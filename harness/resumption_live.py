"""Measure TLS 1.3 session resumption, and record where it is unavailable.

Section 5.2 of the paper bounded resumption at 2.9--3.1 kB and 3.4--3.5 s
because it could not be measured directly.  It can, but not in the case
the paper cares about, and the reason is a property of the stack rather
than of the link.

What was established, in order:

  1. `-sess_out` does work for TLS 1.3, but only if the client is sent a
     NewSessionTicket, which requires that `-no_ticket` is *not* in
     effect.  Every other measurement in this paper uses `-no_ticket`, so
     the earlier attempt had nothing to resume.
  2. With mutual authentication enabled (`s_server -Verify` in any form,
     including `-verify` which merely requests), OpenSSL 3.5.7's
     `s_server` sends no NewSessionTicket at all.  Four configurations
     were tried -- no client auth, `-verify 0`, `-Verify 0`, `-Verify 1`
     -- and a ticket appears only in the first.
  3. Resumption is therefore measurable only for server-authenticated
     handshakes, which is the configuration this script measures.

The reason (2) is not an accident of the tool: a resumed TLS 1.3
handshake authenticates with the PSK and does not re-run certificate
authentication in either direction.  A stack that has been told to
demand a client certificate has no way to satisfy that demand from a
ticket, so it declines to issue one.  This is the paper's thesis
appearing as a tool behaviour: once trust is pre-provisioned, the
certificates stop going on the wire.

Output: results/resumption.csv
"""

import csv
import os
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import link_measure as lm  # noqa: E402

ALG = "ml-dsa-65"
REPS = 5
RATE = 9600
DELAY = 250
OUT = os.path.join(HERE, "..", "results", "resumption.csv")


def issue_pki(tmp):
    """A CA and a leaf it signs, so -CAfile never holds the peer's identity."""
    keyopt = list(lm._NEWKEY[ALG])
    p = lambda n: os.path.join(tmp, n)
    ca_key, ca_crt = p("ca.key"), p("ca.crt")
    lf_key, lf_csr, lf_crt = p("leaf.key"), p("leaf.csr"), p("leaf.crt")

    subprocess.run(["openssl", "req", "-new", "-x509", "-days", "1", "-nodes",
                    "-subj", "/CN=uav-ca", "-keyout", ca_key, "-out", ca_crt,
                    "-addext", "basicConstraints=critical,CA:TRUE",
                    "-addext", "keyUsage=critical,keyCertSign,cRLSign"] + keyopt,
                   check=True, capture_output=True)
    subprocess.run(["openssl", "req", "-new", "-nodes",
                    "-subj", "/CN=uav-c2-test", "-keyout", lf_key, "-out", lf_csr]
                   + keyopt, check=True, capture_output=True)
    ext = p("leaf.ext")
    with open(ext, "w") as f:
        f.write("basicConstraints=critical,CA:FALSE\n"
                "keyUsage=critical,digitalSignature\n"
                "extendedKeyUsage=serverAuth\n"
                "subjectAltName=DNS:uav-c2-test\n"
                "subjectKeyIdentifier=hash\n"
                "authorityKeyIdentifier=keyid:always\n")
    subprocess.run(["openssl", "x509", "-req", "-in", lf_csr, "-CA", ca_crt,
                    "-CAkey", ca_key, "-CAcreateserial", "-days", "1",
                    "-out", lf_crt, "-extfile", ext],
                   check=True, capture_output=True)
    return ca_crt, lf_crt, lf_key


def main():
    rows = []
    with tempfile.TemporaryDirectory() as td:
        ca, leaf, key = issue_pki(td)

        for rep in range(REPS):
            port = 28900 + rep * 10
            srv = subprocess.Popen(
                ["openssl", "s_server", "-accept", str(port), "-cert", leaf,
                 "-key", key, "-tls1_3", "-groups", "MLKEM768", "-quiet"],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            try:
                if not lm._wait_port(port):
                    print("s_server did not start", file=sys.stderr)
                    continue

                # Baseline: a full server-authenticated handshake, unfettered
                # by a ticket.  This is the number resumption has to beat.
                base = lm.measure("MLKEM768", leaf, key, ALG, RATE, DELAY,
                                  25100 + rep * 10, server_ca=ca, seed=rep,
                                  external_srv_port=port)

                # Pass 1: same handshake but with a ticket allowed.  Direct
                # rather than throttled: at 9.6 kbps the ticket is still on
                # the wire when the client hits EOF, and `-sess_out` is
                # written at close, so a throttled pass 1 loses it.
                sess = os.path.join(td, f"s{rep}.pem")
                p1 = subprocess.run(
                    ["openssl", "s_client", "-connect", f"127.0.0.1:{port}",
                     "-tls1_3", "-groups", "MLKEM768", "-CAfile", ca,
                     "-sess_out", sess],
                    capture_output=True, text=True, timeout=120, input="x\n")
                if not os.path.exists(sess):
                    print(f"  rep{rep}: no session file", file=sys.stderr)
                    continue

                # Pass 2: the resumption, measured on the emulated link.
                r = lm.measure("MLKEM768", leaf, key, ALG, RATE, DELAY,
                               25100 + rep * 10, server_ca=ca,
                               allow_ticket=True, sess_in=sess, seed=200 + rep,
                               external_srv_port=port)
                if not r.ok:
                    print(f"  rep{rep}: resumption failed", file=sys.stderr)
                    continue

                reused = "Reused" in r.stdout
                rows.append(dict(rep=rep, reused=int(reused),
                                 full_bytes=base.total_bytes,
                                 full_t_s=round(base.wall_ms / 1000, 3),
                                 res_bytes=r.total_bytes,
                                 res_t_s=round(r.wall_ms / 1000, 3),
                                 sess_file_bytes=os.path.getsize(sess)))
                print(f"  rep {rep}: full {base.total_bytes} B / "
                      f"{base.wall_ms/1000:.2f} s  ->  resumed {r.total_bytes} B / "
                      f"{r.wall_ms/1000:.2f} s  reused={reused}")
            finally:
                srv.terminate()
                try:
                    srv.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    srv.kill()

    if not rows:
        print("no successful resumptions", file=sys.stderr)
        return 1

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)

    n = len(rows)
    fb = sum(r["full_bytes"] for r in rows) / n
    ft = sum(r["full_t_s"] for r in rows) / n
    rb = sum(r["res_bytes"] for r in rows) / n
    rt = sum(r["res_t_s"] for r in rows) / n
    print(f"\nfull    {fb:.0f} B  {ft:.3f} s")
    print(f"resumed {rb:.0f} B  {rt:.3f} s")
    print(f"ratio   {rb/fb:.2f}$\\times$ bytes, {rt/ft:.2f}$\\times$ time")
    print(f"written to {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
