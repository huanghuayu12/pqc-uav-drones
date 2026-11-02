#!/usr/bin/env python3
"""msg_anatomy.py -- resolve on-the-wire handshake bytes to the byte.

Answers the question a reviewer asks of the per-message table: does every
record size follow from the standards?  Three dumps, in order:

  1. the DER anatomy of the ML-DSA-65 test certificate
  2. every TLS record of a mutual-authentication handshake, both directions
  3. a length check that explains the Certificate record exactly

TLS 1.3 encrypts the Certificate, so a naive scan of plaintext records finds
nothing: the handshake stream has to be reassembled from the application_data
records first, which is what `scan` below does.

Result for ML-KEM-768 + ML-DSA-65 (stable across runs):

  DER            5,514 = 1,952 key + 3,309 signature + 253 X.509 frame
  Certificate    5,549 = 35 TLS framing + 5,514 DER
  CertVerify     3,339 = 30 TLS framing + 3,309 signature
  c2s           10,372 = 1,357 6 5,549 3,339 74 23 24
  s2c           10,468 = 1,183 6 28 107 5,549 3,339 74 79 79 24

The 23-byte record in c2s is the one-byte application probe, not handshake
data; see the module docstring of link_measure.py.
"""
import socket
import subprocess
import sys
import tempfile
import threading
import time

sys.path.insert(0, "harness")
import link_measure as lm  # noqa: E402


def grab(cert, key, srv_port, proxy_port, inp="x"):
    """One handshake through a recording proxy; returns raw bytes each way."""
    srv = ["openssl", "s_server", "-accept", str(srv_port), "-cert", cert,
           "-key", key, "-tls1_3", "-groups", "MLKEM768", "-quiet",
           "-no_ticket", "-Verify", "0", "-CAfile", cert]
    cli = ["openssl", "s_client", "-connect", f"127.0.0.1:{proxy_port}",
           "-groups", "MLKEM768", "-tls1_3", "-no_ticket",
           "-cert", cert, "-key", key]
    p = subprocess.Popen(srv, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(150):
        try:
            socket.create_connection(("127.0.0.1", srv_port), timeout=0.2).close()
            break
        except OSError:
            time.sleep(0.05)

    ln = socket.socket()
    ln.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    ln.bind(("127.0.0.1", proxy_port))
    ln.listen(1)
    ln.settimeout(60)
    buf = {"c2s": bytearray(), "s2c": bytearray()}

    def pump(a, b, k):
        try:
            while True:
                d = a.recv(65536)
                if not d:
                    break
                buf[k] += d
                b.sendall(d)
        except OSError:
            pass
        finally:
            try:
                b.shutdown(socket.SHUT_WR)
            except OSError:
                pass

    def serve():
        c, _ = ln.accept()
        sv = socket.create_connection(("127.0.0.1", srv_port))
        t1 = threading.Thread(target=pump, args=(c, sv, "c2s"), daemon=True)
        t2 = threading.Thread(target=pump, args=(sv, c, "s2c"), daemon=True)
        t1.start(); t2.start(); t1.join(60); t2.join(60)

    threading.Thread(target=serve, daemon=True).start()
    r = subprocess.run(cli, capture_output=True, text=True, timeout=120, input=inp)
    p.terminate()
    ln.close()
    return buf, r


def records(data):
    out, i = [], 0
    while i + 5 <= len(data):
        ct = data[i]
        ln = int.from_bytes(data[i + 3:i + 5], "big")
        if i + 5 + ln > len(data):
            break
        out.append((ct, bytes(data[i + 5:i + 5 + ln])))
        i += 5 + ln
    return out


def tlv(b, o=0):
    t = b[o]; o += 1
    l = b[o]; o += 1
    if l & 0x80:
        n = l & 0x7F
        l = int.from_bytes(b[o:o + n], "big")
        o += n
    return t, l, o, o + l


def der_anatomy(der):
    _, _, cs, ce = tlv(der)
    t, l2, cs2, ce2 = tlv(der, cs)
    print(f"DER total {len(der)}; TBS {l2} + header 4 = {ce2 - cs}")
    o = cs2
    while o < ce2:
        t3, l3, _, e3 = tlv(der, o)
        print(f"  field {t3:#04x} len={l3}")
        o = e3
    t4, l4, c4, e4 = tlv(der, ce2)
    print(f"sigalg block {e4 - ce2}")
    t5, l5, c5, e5 = tlv(der, e4)
    print(f"signature BIT STRING {l5} (value {l5 - 1})")


def decompose(payload_len, der_len, direction):
    """Explain a Certificate record from its length alone.

    TLS 1.3 encrypts the message, so the structure cannot be read off the
    wire without the keys; the lengths can still be checked, because every
    field the message contains has a fixed width:

        record payload = 16 AEAD tag
                       + 4  handshake header
                       + 1  content type (inside the inner plaintext)
                       + 1  certificate_request_context length
                       + 3  certificate_list length
                       + 3  first certificate length
                       + der_len
                       + 2  per-certificate extensions length

    Solving for the last term is the check: if it comes out at zero, the
    record carries one certificate and no per-certificate extensions, which
    is what the test configuration should produce.
    """
    fixed = 16 + 4 + 1 + 1 + 3 + 3 + 2
    rest = payload_len - fixed - der_len
    print(f"{direction}: payload {payload_len} = {fixed} framing + {der_len} DER "
          f"+ {rest} unexplained")
    if rest:
        print(f"  ! {rest} bytes are not accounted for")
    else:
        print("  exact: one certificate, no per-certificate extensions")


def main():
    with tempfile.TemporaryDirectory() as td:
        certs = {a: (c, k) for a, c, k in lm.make_certs(td)}
        cert, key = certs["ml-dsa-65"]
        der = subprocess.run(["openssl", "x509", "-in", cert, "-outform", "DER"],
                             capture_output=True).stdout

        print("== DER anatomy ==")
        der_anatomy(der)

        print("\n== records ==")
        buf, _ = grab(cert, key, 29530, 29531)
        for d in ("c2s", "s2c"):
            rec = records(bytes(buf[d]))
            full = [(ct, len(pl) + 5) for ct, pl in rec]
            print(f"{d}: {sum(n for _, n in full)} B  {full}")

        print("\n== Certificate record ==")
        for d in ("c2s", "s2c"):
            big = max((len(pl) for ct, pl in records(bytes(buf[d])) if ct == 23),
                      default=None)
            if big:
                decompose(big, len(der), d)


if __name__ == "__main__":
    main()
