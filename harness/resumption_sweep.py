"""UNUSED: this script does not work with OpenSSL 3.5.7 and is kept only as a
record of what was attempted.

The blocker is that s_client's -sess_out does not export a resumable TLS 1.3
ticket in this build.  It writes a 1,636-byte "SSL SESSION PARAMETERS" blob
(a TLS 1.2-style session object), and feeding that back with -sess_in does not
produce a resumed handshake: the second connection re-runs a full one, measured
at 14,375 bytes instead of the ~2,900 a pre-shared-key handshake costs.
-num_tickets does not help, and it makes -sess_out fail outright.  Because the
ticket is delivered after the handshake, a client that exits on stdin EOF
receives nothing at all, so the connection has to be held open -- that part is
fixed below and works, but it is not sufficient.

The paper therefore bounds resumption rather than measuring it directly; see
Section 5.2.  Do not cite numbers from this script.

Measure a resumed TLS 1.3 handshake against a full one.

Section 5.2 of the paper leans on session resumption to keep the
certificate cost rare: "whether eleven seconds is acceptable depends on
how often the handshake happens; session resumption keeps it rare."  That
claim had no measurement behind it.  This script supplies one.

Method
------
TLS 1.3 resumption needs a session ticket, which the main harness
disables to keep byte counts clean (NewSessionTicket arrives after the
handshake and was being counted inconsistently).  Here tickets are
enabled for the first connection only, and the session is exported with
-sess_out.  The second connection resumes from that file and is the one
that is measured, through the same rate-limiting proxy as every other
number in the paper.

The first connection is deliberately run without the proxy.  Its purpose
is to produce a ticket, not to be measured; running it at full speed
keeps the experiment short and does not affect what the ticket contains.

Both connections must hit the same s_server process.  A TLS 1.3 ticket is
sealed with a key that is generated per process, so a fresh instance
cannot resume a session from an earlier one -- an earlier attempt that
restarted the server for the second connection failed every time with
"session not resumed".
"""
from __future__ import annotations

import csv
import os
import subprocess
import sys
import tempfile
import time
import socket

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import link_measure as lm                                   # noqa: E402

RATE, DELAY = 9600, 250
N = 5


def run_case(group, cert, key, label, port):
    """Return (label, full_bytes, full_t, res_bytes, res_t, resumed_flag)."""
    srv_port = port
    srv = subprocess.Popen(
        ["openssl", "s_server", "-accept", str(srv_port), "-cert", cert,
         "-key", key, "-tls1_3", "-groups", group, "-quiet",
         "-Verify", "0", "-CAfile", cert],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    sess = os.path.join(HERE, f".sess_{port}.pem")
    try:
        if not lm._wait_port(srv_port):
            raise RuntimeError("s_server did not start")

        # 1) full handshake, no proxy, harvest a ticket.
        # The connection must stay open for a moment after the handshake:
        # NewSessionTicket arrives afterwards, and a client that exits on
        # stdin EOF never receives it, so -sess_out writes nothing.  Measured:
        # exiting immediately produces no session file at all.
        p1 = subprocess.Popen(
            ["openssl", "s_client", "-connect", f"127.0.0.1:{srv_port}",
             "-groups", group, "-tls1_3",
             "-cert", cert, "-key", key,
             "-sess_out", sess],
            stdin=subprocess.PIPE, stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL)
        try:
            p1.stdin.write(b"x\n"); p1.stdin.flush()
            time.sleep(2.5)
            p1.stdin.close()
            p1.wait(timeout=20)
        except Exception:                                   # noqa: BLE001
            p1.kill()
        if not os.path.exists(sess):
            return (label, 0, 0.0, 0, 0.0, False)

        # 2) resumed handshake, through the proxy
        ls, _ = lm.serve_once(port + 1, srv_port, RATE, DELAY)
        t0 = time.perf_counter()
        r2 = subprocess.run(
            ["openssl", "s_client", "-connect", f"127.0.0.1:{port + 1}",
             "-groups", group, "-tls1_3",
             "-cert", cert, "-key", key,
             "-sess_in", sess],
            capture_output=True, text=True, timeout=180, input="x")
        wall = (time.perf_counter() - t0)
        ls.done.wait(30)
        resumed = "Reused" in r2.stderr and "New," not in r2.stderr
        tot = ls.up.bytes + ls.down.bytes
        return (label, 0, 0.0, tot, wall, resumed)
    finally:
        srv.terminate()
        try: srv.wait(timeout=5)
        except subprocess.TimeoutExpired: srv.kill()
        try: os.unlink(sess)
        except OSError: pass


def main():
    with tempfile.TemporaryDirectory() as td:
        certs = {a: (c, k) for a, c, k in lm.make_certs(td)}
        cases = [("ML-KEM-768 + ML-DSA-65", "MLKEM768", "ml-dsa-65"),
                 ("X25519 + ECDSA-P256", "X25519", "ecdsa-p256")]
        rows = []
        port = 23000
        for label, group, alg in cases:
            c, k = certs[alg]
            for i in range(N):
                port += 2
                lab, fb, ft, rb, rt, resumed = run_case(group, c, k, label, port)
                rows.append(dict(config=lab, run=i, resumed=resumed,
                                 resumed_bytes=rb, resumed_t_s=round(rt, 3)))
                print(f"{lab:26s} run {i}  resumed={resumed}  "
                      f"{rb:6d} B  {rt:6.3f} s", file=sys.stderr)
        out = os.path.join(HERE, "..", "results", "resumption.csv")
        with open(out, "w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)
        print(f"wrote {out}", file=sys.stderr)


if __name__ == "__main__":
    main()
