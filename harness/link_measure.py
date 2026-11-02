#!/usr/bin/env python3
"""
link_measure.py -- measure real TLS 1.3 post-quantum handshakes over an
emulated constrained C2 link.

This replaces the purely analytical treatment with a measurement on a real
protocol stack (OpenSSL 3.5, TLS 1.3, ML-KEM / ML-DSA).  A userspace TCP
proxy rate-limits and delays the connection so that a 9.6 kbps / 250 ms
geostationary C2 link can be emulated on an ordinary machine without `tc`,
root privileges or special hardware.

What is measured, and what is not
---------------------------------
MEASURED
  * bytes actually exchanged in each direction during the connection
  * wall-clock time to complete the handshake
  The application payload is a single byte that the client sends after the
  handshake, as a liveness probe; the server returns nothing.  That byte
  occupies a 23-byte record (5 header + 16 AEAD tag + 1 content type + 1
  payload), so every byte count here is 23 bytes larger than the handshake
  proper.  Session tickets are disabled
  with -no_ticket: NewSessionTicket arrives after the handshake and was being
  counted or not counted depending on link speed, which made byte counts vary
  by ~12% between runs of the same configuration.  An earlier version used
  `s_server -www`, whose ~5 kB HTML status page dominated the count and
  corrupted the comparison between cipher suites.
  * negotiated TLS version, group and cipher suite
NOT MEASURED
  * microcontroller cycle counts, RAM or energy.  Those are taken from the
    literature (pqm4 for ML-DSA, Pornin 2019 for Falcon) and cited, not
    measured here.  Do not claim otherwise in the paper.

The emulated link model is: token-bucket serialisation at the configured rate,
plus a fixed one-way propagation delay applied once per forwarded chunk.  This
is *not* the same as a store-and-forward link, where the delay is paid once per
hop rather than once per chunk, and the paper says so rather than pretending
otherwise (Section 3.2).  What saves the model is that on a narrow link TCP
coalesces a whole flight of segments into one chunk, so the chunk boundaries
tend to coincide with direction changes, and a direction change is exactly
where an additional one-way delay is physically owed.  The number should still
be read as a slightly pessimistic estimate: calibration at 9.6 kbps on the
20,840-byte handshake gives 10.26 s at zero delay and 11.28 s at 250 ms, so
repeated delay contributes 1.0 s, about 9% of the total.  The sensitivity
analysis in Section 4.6 uses that linearity directly.

Loss is handled by RTO injection, not by dropping bytes: a TCP proxy cannot
drop a byte without corrupting the stream.  With `--loss p` a chunk is delayed
by one retransmission timeout with probability p, which reproduces the
time-axis effect of a lost segment while leaving the byte stream intact.  The
mapping "one loss = one RTO" is an assumption and is labelled as such wherever
those numbers appear.

Usage
-----
    python3 link_measure.py --rate 9600 --delay-ms 250
    python3 link_measure.py --matrix > ../results/real_handshake.csv
"""

from __future__ import annotations

import argparse
import csv
import os
import random
import socket
import subprocess
import sys
import tempfile
import threading
import time
from dataclasses import dataclass, field

HERE = os.path.dirname(os.path.abspath(__file__))

# Nominal TCP segment payload, used to convert a byte count into a
# segment count for loss accounting.
MSS_BYTES = 1460


# ---------------------------------------------------------------------------
# Rate-limiting, delaying TCP proxy
# ---------------------------------------------------------------------------
class Throttle:
    """Token bucket: serialise bytes at `bps`, then hold each chunk `delay` s.

    With `loss_prob > 0` the chunk is additionally held for one retransmission
    timeout, which emulates a lost segment.  See the module docstring for why
    this is injection rather than actual dropping.
    """

    def __init__(self, bps: float, delay_s: float, burst: int = 0,
                 loss_prob: float = 0.0, rto_s: float = 1.2, seed: int = 0):
        self.rate = bps / 8.0            # bytes per second
        self.delay = delay_s
        self.burst = burst
        self.tokens = float(burst)
        self.last = time.monotonic()
        self.bytes = 0
        self.chunks = 0
        self.loss_prob = loss_prob
        self.rto = rto_s
        self.drops = 0
        self._rng = random.Random(seed)

    def consume(self, n: int) -> float:
        """Return how long the caller must wait before this chunk may leave.

        Debt model: `tokens` is allowed to go negative, so the bucket owes
        capacity.  `burst` defaults to 0 on purpose: a token bucket with a
        non-zero burst hands out that many bytes for free, which is wrong for a
        serial link and cost ~13% on a 12 kB transfer (a 1400-byte burst is
        1.17 s at 9.6 kbps).  With burst 0 the serialisation is exact.  A previous version clamped tokens to zero on the deficit
        branch *and* refilled from elapsed time on the next call, which
        credited the same wait twice and let the link run ~50% fast (measured
        14.7 kbps against a 9.6 kbps target).  Letting the balance go negative
        makes the long-run serialisation exactly n/rate per byte regardless of
        how the stream happens to be chunked.
        """
        now = time.monotonic()
        self.tokens = min(self.burst, self.tokens + (now - self.last) * self.rate)
        self.last = now
        self.tokens -= n
        wait = 0.0 if self.tokens >= 0 else -self.tokens / self.rate
        self.bytes += n
        self.chunks += 1
        if self.loss_prob > 0.0 and n > 0:
            # Loss must be counted per transmitted segment, not per proxy chunk.
            # TCP coalesces a whole flight of segments into one recv(), so
            # counting per chunk makes a 20,840-byte handshake suffer the same
            # loss rate as a 1,912-byte one: measured 2.0 drops for both at
            # p=0.30, when 14 segments against 2 should differ by 7x.  Charging
            # one RTO per lost segment is an upper bound, because a real TCP
            # would retransmit several losses within one timeout using SACK.
            segs = max(1, round(n / MSS_BYTES))
            lost = sum(1 for _ in range(segs) if self._rng.random() < self.loss_prob)
            if lost:
                self.drops += lost
                wait += lost * self.rto
                # Freeze the credit clock across the retransmission timeouts.
                # Without this the bucket refills by rto*rate on the next call
                # and the loss costs nothing: measured 2 drops at p=0.15 moving
                # the handshake by 0.015 s instead of 2.4 s.
                self.last += lost * self.rto
        return wait + self.delay


@dataclass
class LinkStats:
    up: Throttle = None      # client -> server
    down: Throttle = None    # server -> client
    done: threading.Event = field(default_factory=threading.Event)

    @property
    def drops(self) -> int:
        return (self.up.drops if self.up else 0) + (self.down.drops if self.down else 0)


def _pump(src: socket.socket, dst: socket.socket, thr: Throttle, stop: threading.Event):
    try:
        while not stop.is_set():
            data = src.recv(4096)
            if not data:
                break
            wait = thr.consume(len(data))
            if wait > 0:
                time.sleep(wait)
            dst.sendall(data)
    except OSError:
        pass
    finally:
        try:
            dst.shutdown(socket.SHUT_WR)
        except OSError:
            pass


def serve_once(listen_port: int, target_port: int, bps: float, delay_ms: float,
               loss_prob: float = 0.0, rto_ms: float = 1200.0, seed: int = 0):
    """Accept exactly one connection, proxy it, return LinkStats."""
    ls = LinkStats(up=Throttle(bps, delay_ms / 1000.0, loss_prob=loss_prob,
                               rto_s=rto_ms / 1000.0, seed=seed),
                   down=Throttle(bps, delay_ms / 1000.0, loss_prob=loss_prob,
                                 rto_s=rto_ms / 1000.0, seed=seed + 977))
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("127.0.0.1", listen_port))
    srv.listen(1)
    srv.settimeout(30)

    def run():
        try:
            conn, _ = srv.accept()
        except OSError:
            ls.done.set()
            return
        try:
            up_sock = socket.create_connection(("127.0.0.1", target_port), timeout=30)
        except OSError:
            conn.close(); ls.done.set(); return
        stop = threading.Event()
        t1 = threading.Thread(target=_pump, args=(conn, up_sock, ls.up, stop), daemon=True)
        t2 = threading.Thread(target=_pump, args=(up_sock, conn, ls.down, stop), daemon=True)
        t1.start(); t2.start()
        t1.join(120); t2.join(120)
        stop.set()
        for s in (conn, up_sock):
            try: s.close()
            except OSError: pass
        ls.done.set()

    threading.Thread(target=run, daemon=True).start()
    return ls, srv


# ---------------------------------------------------------------------------
# Handshake driver
# ---------------------------------------------------------------------------
@dataclass
class Result:
    group: str
    cert_alg: str
    rate_bps: int
    delay_ms: int
    ok: bool
    wall_ms: float
    up_bytes: int
    down_bytes: int
    total_bytes: int
    protocol: str
    cipher: str
    drops: int = 0
    stdout: str = ""


def _wait_port(port: int, timeout_s: float = 20.0) -> bool:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        try:
            s = socket.create_connection(("127.0.0.1", port), timeout=0.2)
            s.close()
            return True
        except OSError:
            time.sleep(0.02)
    return False


def measure(group: str, cert: str, key: str, cert_alg: str,
            rate_bps: int, delay_ms: int, port_base: int,
            timeout_s: float = 180.0,
            client_cert: str | None = None, client_key: str | None = None,
            server_chain: str | None = None, client_chain: str | None = None,
            server_ca: str | None = None, sess_in: str | None = None,
            sess_out: str | None = None, external_srv_port: int | None = None,
            psk_hex: str | None = None, allow_ticket: bool = False,
            loss_prob: float = 0.0, rto_ms: float = 1200.0,
            seed: int = 0) -> Result:
    """Run one handshake.

    `sess_in` resumes a TLS 1.3 session from a file written by a previous
    connection's `-sess_out`, and requires `allow_ticket` on the server: a
    client that is never sent a ticket has nothing to resume.

    If `psk_hex` is given the handshake uses TLS 1.3 external PSK instead of
    certificates: no Certificate, no CertificateVerify, no trust anchor on the
    link.  This is the pre-provisioned-trust case, and it is measured rather
    than modelled because the whole point of the analysis is that this case has
    a different byte cost, not a different cryptographic security level.
    """
    srv_port = port_base
    proxy_port = port_base + 1

    if psk_hex:
        server_cmd = ["openssl", "s_server", "-accept", str(srv_port),
                      "-tls1_3", "-groups", group, "-quiet", "-nocert",
                      "-psk", psk_hex, "-psk_identity", "uav", "-no_ticket"]
        client_cmd = ["openssl", "s_client", "-connect", f"127.0.0.1:{proxy_port}",
                      "-groups", group, "-tls1_3", "-no_ticket",
                      "-psk", psk_hex, "-psk_identity", "uav"]
        cert_alg = "psk"
    else:
        # -no_ticket is required on the SERVER too, not only on the client.
        # With client authentication enabled, s_server uses -CAfile both to
        # validate the client and to build the chain it sends; the CA
        # certificate then reappears inside each NewSessionTicket.  Measured on
        # ML-KEM-768 + ML-DSA-65 that inflated the server->client direction
        # from 10,447 B to 21,807 B -- two 5,759 B tickets where a ticket
        # should be 255 B.  Client-side -no_ticket alone does not suppress it,
        # because the ticket is emitted by the server after the handshake.
        srv_ticket = [] if allow_ticket else ["-no_ticket"]
        # `server_chain` makes the server send an intermediate alongside its
        # leaf; `server_ca` is a trust anchor only and is deliberately not
        # sent.  Both are needed to measure a two-level hierarchy, and the
        # byte delta is checked in chain_depth.py rather than assumed.
        srv_chain = [] if server_chain is None else ["-cert_chain", server_chain]
        trust_anchor = server_ca if server_ca is not None else client_cert
        server_cmd = (["openssl", "s_server", "-accept", str(srv_port), "-cert", cert,
                       "-key", key, "-tls1_3", "-groups", group, "-quiet"] + srv_ticket
                      + srv_chain
                      + (["-Verify", "0", "-CAfile", trust_anchor] if client_cert else []))
        client_cmd = (["openssl", "s_client", "-connect", f"127.0.0.1:{proxy_port}",
                       "-groups", group, "-tls1_3"]
                      + ([] if allow_ticket else ["-no_ticket"])
                      + (["-cert", client_cert, "-key", client_key] if client_cert else [])
                      + (["-cert_chain", client_chain] if client_chain else [])
                      + (["-CAfile", server_ca] if server_ca else [])
                      + (["-sess_in", sess_in] if sess_in else [])
                      + (["-sess_out", sess_out] if sess_out else []))

    if external_srv_port is not None:
        # Resuming a TLS 1.3 session requires the ticket encryption key,
        # which lives in the process that issued the ticket.  Starting a
        # fresh s_server here would silently reject the ticket and fall
        # back to a full handshake, which is exactly the failure this
        # parameter exists to prevent.
        srv_port = external_srv_port
        server = None
    else:
        server = subprocess.Popen(server_cmd,
                                  stdout=subprocess.DEVNULL,
                                  stderr=subprocess.DEVNULL)
    try:
        if server is not None and not _wait_port(srv_port):
            raise RuntimeError("s_server did not start")
        ls, proxy = serve_once(proxy_port, srv_port, rate_bps, delay_ms,
                               loss_prob=loss_prob, rto_ms=rto_ms, seed=seed)
        # NB: do not probe proxy_port for readiness.  serve_once() has already
        # bound and listened synchronously, and it accepts exactly one
        # connection -- a liveness probe would consume that connection and the
        # real client would queue forever.

        t0 = time.perf_counter()
        try:
            r = subprocess.run(client_cmd, capture_output=True, text=True,
                               timeout=timeout_s, input="x")
            wall = (time.perf_counter() - t0) * 1000.0
            ok = r.returncode == 0
            err = r.stderr
        except subprocess.TimeoutExpired:
            wall, ok, err = timeout_s * 1000.0, False, ""

        ls.done.wait(30)
        proto = next((l.split(":", 1)[1].strip() for l in err.splitlines()
                      if l.startswith("New, TLSv")), "")
        cipher = next((l.split(":", 1)[1].strip() for l in err.splitlines()
                       if l.startswith("Cipher is")), "")
        if not cipher:
            for l in err.splitlines():
                if "Ciphersuite is" in l:
                    cipher = l.split(":", 1)[-1].strip(); break
        return Result(group, cert_alg, rate_bps, delay_ms, ok, wall,
                      ls.up.bytes, ls.down.bytes, ls.up.bytes + ls.down.bytes,
                      proto or ("TLS1.3" if ok else ""), cipher, ls.drops,
                      stdout=r.stdout if ok else "")
    finally:
        if server is not None:
            server.terminate()
            try: server.wait(timeout=5)
            except subprocess.TimeoutExpired: server.kill()


# ---------------------------------------------------------------------------
# Certificate algorithms to sweep.  ML-DSA is included at all three parameter
# sets, not just the recommended one, because the certificate and
# CertificateVerify sizes are what the measurement is about: 44/65/87 give a
# controlled sweep over object size within one scheme family, which is what
# lets the byte->time relation be fitted to measured points rather than
# assumed.  That fit is then what any extrapolation (e.g. to FN-DSA, which
# OpenSSL 3.5 cannot load) has to stand on.
CERT_ALGS = ("ecdsa-p256", "ml-dsa-44", "ml-dsa-65", "ml-dsa-87",
             "slh-dsa-sha2-128s")
# 20 bytes, top bit clear: encodes as a 20-byte DER INTEGER with no leading
# zero, which is the width OpenSSL uses for a random serial.  See make_certs.
FIXED_SERIAL = "7f" + "0123456789abcdef" * 2 + "012345"
_NEWKEY = {"ecdsa-p256": ["-newkey", "ec"], "ml-dsa-44": ["-newkey", "ml-dsa-44"],
           "ml-dsa-65": ["-newkey", "ml-dsa-65"], "ml-dsa-87": ["-newkey", "ml-dsa-87"],
           "slh-dsa-sha2-128s": ["-newkey", "slh-dsa-sha2-128s"]}


def make_certs(tmpdir: str) -> list[tuple[str, str, str]]:
    """Generate one self-signed certificate per signature algorithm.

    The serial number is fixed at 20 bytes with the top bit clear, which is
    the width `openssl req -x509` picks by default.  Without this the serial
    is random, and a serial whose leading byte is zero encodes one byte
    shorter, which would move every DER length in the paper by one and break
    the claim that the byte counts are reproducible to the byte.  Fixing the
    value rather than the width would do the same thing, so the value is
    chosen to encode at exactly 20 bytes.
    """
    out = []
    for alg in CERT_ALGS:
        crt = os.path.join(tmpdir, f"{alg}.crt")
        key = os.path.join(tmpdir, f"{alg}.key")
        cmd = (["openssl", "req", "-new", "-x509", "-days", "1", "-nodes",
                "-subj", "/CN=uav-c2-test", "-set_serial", "0x" + FIXED_SERIAL,
                "-keyout", key, "-out", crt]
               + _NEWKEY[alg])
        if alg == "ecdsa-p256":
            cmd += ["-pkeyopt", "ec_paramgen_curve:P-256"]
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode != 0:
            print(f"  ! cert {alg} failed: {r.stderr.strip()[:120]}", file=sys.stderr)
            continue
        out.append((alg, crt, key))
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rate", type=int, default=9600)
    ap.add_argument("--delay-ms", type=int, default=250)
    ap.add_argument("--one-way", action="store_true",
                    help="server-only authentication (default is mutual)")
    ap.add_argument("--allow-ticket", action="store_true",
                    help="reproduce the session-ticket artefact of "
                         "Section 3.3 item (5); do not use for real measurements")
    ap.add_argument("--psk", action="store_true",
                    help="measure TLS 1.3 external-PSK handshakes (no "
                         "certificates) instead of certificate handshakes")
    ap.add_argument("--loss", type=float, default=0.0,
                    help="per-chunk loss probability; a loss costs one RTO "
                         "(RTO injection, see module docstring)")
    ap.add_argument("--rto-ms", type=float, default=1200.0,
                    help="retransmission timeout used for loss injection")
    ap.add_argument("--matrix", action="store_true",
                    help="sweep rates x groups x cert algorithms to CSV")
    ap.add_argument("--out", default=os.path.join(HERE, "..", "results",
                                                  "real_handshake.csv"))
    args = ap.parse_args()

    # Fixed test PSK.  It is a measurement parameter, not a secret: the point is
    # to measure the byte cost of the pre-provisioned-trust case, and the PSK is
    # the same on both sides by construction.
    PSK = ("00112233445566778899aabbccddeeff"
           "00112233445566778899aabbccddeeff")

    with tempfile.TemporaryDirectory() as td:
        certs = make_certs(td)
        if not certs:
            sys.exit("no certificates generated")
        print("certificates:", ", ".join(a for a, _, _ in certs), file=sys.stderr)

        groups = ["X25519", "X25519MLKEM768", "MLKEM768", "MLKEM1024"]
        if args.matrix:
            rates = [(9600, 250), (64000, 2), (2000000, 2)]
        else:
            rates = [(args.rate, args.delay_ms)]

        rows: list[Result] = []
        port = 15300
        if args.psk:
            # For PSK there is no certificate, so the only sweep dimension that
            # matters is the key-exchange group.
            for rate, delay in rates:
                for g in groups:
                    port += 2
                    try:
                        res = measure(g, "", "", "psk", rate, delay, port,
                                      psk_hex=PSK, loss_prob=args.loss,
                                      rto_ms=args.rto_ms, seed=port)
                    except Exception as exc:            # noqa: BLE001
                        print(f"  ! psk/{g}/{rate}: {exc}", file=sys.stderr)
                        continue
                    rows.append(res)
                    print(f"{rate:>9} bps {delay:>4} ms  {g:16s} {'PSK':16s} "
                          f"{'OK ' if res.ok else 'FAIL'} {res.wall_ms:9.0f} ms "
                          f"{res.total_bytes:7d} B "
                          f"{'drops=' + str(res.drops) if res.drops else ''}",
                          file=sys.stderr)
            if rows:
                os.makedirs(os.path.dirname(args.out), exist_ok=True)
                with open(args.out, "w", newline="") as fh:
                    w = csv.DictWriter(fh, fieldnames=list(rows[0].__dict__.keys()))
                    w.writeheader()
                    for r in rows:
                        w.writerow(r.__dict__)
                print(f"wrote {args.out} ({len(rows)} rows)", file=sys.stderr)
            return

        for rate, delay in rates:
            for g in groups:
                for alg, crt, key in certs:
                    port += 2
                    try:
                        res = measure(g, crt, key, alg, rate, delay, port,
                                      client_cert=crt, client_key=key,
                                      allow_ticket=args.allow_ticket,
                                      loss_prob=args.loss, rto_ms=args.rto_ms,
                                      seed=port)
                    except Exception as exc:            # noqa: BLE001
                        print(f"  ! {g}/{alg}/{rate}: {exc}", file=sys.stderr)
                        continue
                    rows.append(res)
                    print(f"{rate:>9} bps {delay:>4} ms  {g:16s} {alg:16s} "
                          f"{'OK ' if res.ok else 'FAIL'} {res.wall_ms:9.0f} ms "
                          f"{res.total_bytes:7d} B", file=sys.stderr)

        if rows:
            os.makedirs(os.path.dirname(args.out), exist_ok=True)
            with open(args.out, "w", newline="") as fh:
                w = csv.DictWriter(fh, fieldnames=list(rows[0].__dict__.keys()))
                w.writeheader()
                for r in rows:
                    w.writerow(r.__dict__)
            print(f"wrote {args.out} ({len(rows)} rows)", file=sys.stderr)


if __name__ == "__main__":
    main()
