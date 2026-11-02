"""Capture the TLS record-layer decomposition of a handshake.

The aggregate byte counter in link_measure.py answers "how big" but not
"what".  For the argument in the paper the attribution matters: the claim is
that certificates and CertificateVerify signatures dominate, not the key
exchange.  This script parses records as they cross the proxy so each byte is
attributed to a TLS record, and plaintext handshake messages are further
attributed to a message type.

Records after ServerHello are encrypted, so message-level attribution is only
possible for ClientHello / ServerHello / HelloRetryRequest.  That is enough:
those are exactly the messages that carry the key exchange.
"""
import csv, json, os, socket, struct, subprocess, sys, tempfile, threading, time
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

REC = {20: "CCS", 21: "ALERT", 22: "HANDSHAKE", 23: "APPDATA"}
HS_NAMES = {1: "ClientHello", 2: "ServerHello", 4: "NewSessionTicket",
            8: "EncryptedExtensions", 11: "Certificate", 13: "CertificateRequest",
            15: "CertificateVerify", 20: "Finished", 24: "KeyUpdate"}
HRR = bytes.fromhex("cf21ad74e59a6111be1d8c021e65b891c2a211167abb8c5e079e09e2c8a8339c")
PSK = "00112233445566778899aabbccddeeff00112233445566778899aabbccddeeff"


class Stream:
    def __init__(self):
        self.total = 0
        self.records = []      # (type, payload_len)
        self.msgs = []         # (hs_type, len) plaintext only
        self._buf = b""
        self._enc = False

    def feed(self, data):
        self.total += len(data)
        self._buf += data
        while len(self._buf) >= 5:
            t, _, ln = struct.unpack("!BHH", self._buf[:5])
            if len(self._buf) < 5 + ln:
                break
            p = self._buf[5:5 + ln]
            self._buf = self._buf[5 + ln:]
            self.records.append((t, ln))
            if t == 22 and not self._enc:
                i = 0
                while i + 4 <= len(p):
                    mt = p[i]; ml = int.from_bytes(p[i + 1:i + 4], "big")
                    self.msgs.append((mt, ml))
                    if mt == 2:
                        rnd = p[i + 4 + 2:i + 4 + 34]
                        if rnd != HRR:
                            self._enc = True
                    i += 4 + ml
            elif t == 20:
                self._enc = True


def run(group, cert=None, key=None, psk=None, port=18000,
        allow_ticket=False):
    srv_port, proxy_port = port, port + 1
    if psk:
        srv = ["openssl","s_server","-accept",str(srv_port),"-tls1_3","-groups",group,
               "-quiet","-nocert","-psk",psk,"-psk_identity","uav","-no_ticket"]
        cli = ["openssl","s_client","-connect",f"127.0.0.1:{proxy_port}","-groups",group,
               "-tls1_3","-no_ticket","-psk",psk,"-psk_identity","uav"]
    else:
        tk = [] if allow_ticket else ["-no_ticket"]
        srv = ["openssl","s_server","-accept",str(srv_port),"-cert",cert,"-key",key,
               "-tls1_3","-groups",group,"-quiet"] + tk + \
              ["-Verify","0","-CAfile",cert]
        cli = ["openssl","s_client","-connect",f"127.0.0.1:{proxy_port}","-groups",group,
               "-tls1_3"] + tk + ["-cert",cert,"-key",key]

    p = subprocess.Popen(srv, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(150):
        try:
            s = socket.create_connection(("127.0.0.1", srv_port), timeout=0.2); s.close(); break
        except OSError:
            time.sleep(0.04)

    listen = socket.socket(); listen.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    listen.bind(("127.0.0.1", proxy_port)); listen.listen(1); listen.settimeout(30)
    st = {"c2s": Stream(), "s2c": Stream()}

    def pump(a, b, s):
        try:
            while True:
                d = a.recv(65536)
                if not d: break
                s.feed(d); b.sendall(d)
        except OSError:
            pass
        finally:
            try: b.shutdown(socket.SHUT_WR)
            except OSError: pass

    def serve():
        c, _ = listen.accept()
        sv = socket.create_connection(("127.0.0.1", srv_port))
        t1 = threading.Thread(target=pump, args=(c, sv, st["c2s"]), daemon=True)
        t2 = threading.Thread(target=pump, args=(sv, c, st["s2c"]), daemon=True)
        t1.start(); t2.start(); t1.join(60); t2.join(60)
    threading.Thread(target=serve, daemon=True).start()

    r = subprocess.run(cli, capture_output=True, text=True, timeout=120, input="x")
    p.terminate()
    try: p.wait(timeout=5)
    except subprocess.TimeoutExpired: p.kill()
    listen.close()
    return st, r.returncode


def summarize(st):
    """Attribute bytes by record class, and pull out the plaintext KX bytes."""
    out = {"c2s_total": st["c2s"].total, "s2c_total": st["s2c"].total}
    for k in ("c2s", "s2c"):
        by = {}
        for t, ln in st[k].records:
            by[REC.get(t, str(t))] = by.get(REC.get(t, str(t)), 0) + ln + 5
        out[f"{k}_by_record"] = by
        kx = [l for mt, l in st[k].msgs if mt in (1, 2)]
        out[f"{k}_kx_bytes"] = sum(kx) + 4 * len(kx)
    out["total"] = out["c2s_total"] + out["s2c_total"]
    return out


def main():
    with tempfile.TemporaryDirectory() as td:
        import link_measure as lm
        certs = {a: (c, k) for a, c, k in lm.make_certs(td)}
        cases = [
            ("X25519 + ECDSA-P256", "X25519", "ecdsa-p256", None),
            ("X25519 + ML-DSA-65", "X25519", "ml-dsa-65", None),
            ("ML-KEM-768 + ECDSA-P256", "MLKEM768", "ecdsa-p256", None),
            ("ML-KEM-768 + ML-DSA-65", "MLKEM768", "ml-dsa-65", None),
            ("ML-KEM-768 + PSK", "MLKEM768", None, PSK),
            ("X25519 + PSK", "X25519", None, PSK),
        ]
        rows = []
        port = 18100
        for label, g, alg, psk in cases:
            port += 2
            if psk:
                st, rc = run(g, psk=psk, port=port)
            else:
                c, k = certs[alg]
                st, rc = run(g, cert=c, key=k, port=port)
            s = summarize(st)
            s.update(label=label, group=g, cert_alg=alg or "psk", rc=rc)
            rows.append(s)
            print(f"{label:26s} rc={rc} total={s['total']:6d} "
                  f"kx c2s={s['c2s_kx_bytes']:5d} s2c={s['s2c_kx_bytes']:5d}", file=sys.stderr)

        out = os.path.join(HERE, "..", "results", "record_breakdown.json")
        with open(out, "w") as fh:
            json.dump(rows, fh, indent=1)
        print(f"wrote {out}", file=sys.stderr)

        # Reproduce the session-ticket artefact of the paper (Section 3.3,
        # item 5) so that the figure and table are backed by a stored file.
        c, k = certs["ml-dsa-65"]
        arte = []
        for allow, tag in ((False, "server -no_ticket"), (True, "tickets enabled")):
            st, rc = run("MLKEM768", cert=c, key=k, port=18700 + 20 * allow,
                         allow_ticket=allow)
            recs = [ln + 5 for t, ln in st["s2c"].records]
            arte.append(dict(mode=tag, rc=rc,
                             c2s_bytes=st["c2s"].total,
                             s2c_bytes=st["s2c"].total,
                             total_bytes=st["c2s"].total + st["s2c"].total,
                             s2c_records=" ".join(str(x) for x in recs)))
            print(f"  artefact {tag:20s} total={arte[-1]['total_bytes']}", file=sys.stderr)
        aout = os.path.join(HERE, "..", "results", "ticket_artefact.csv")
        import csv as _csv
        with open(aout, "w", newline="") as fh:
            w = _csv.DictWriter(fh, fieldnames=list(arte[0].keys()))
            w.writeheader(); w.writerows(arte)
        print(f"wrote {aout}", file=sys.stderr)


if __name__ == "__main__":
    main()
