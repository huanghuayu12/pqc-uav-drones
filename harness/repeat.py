"""Repeat a small set of configurations to report run-to-run variance.

The sweep tables are single-run, and a 9.6 kbps handshake takes long enough
that repeating everything is expensive.  This script repeats only the three
configurations that carry the argument -- the classical baseline, the
recommended post-quantum certificate suite, and the pre-provisioned-trust
case -- so that the paper can report a mean and a standard deviation instead
of one number per cell.
"""
import csv, statistics, sys, tempfile, os
import link_measure as lm

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "results", "repeatability.csv")

PSK = "00112233445566778899aabbccddeeff00112233445566778899aabbccddeeff"
N = 5
RATE, DELAY = 9600, 250

def main():
    with tempfile.TemporaryDirectory() as td:
        certs = {a: (c, k) for a, c, k in lm.make_certs(td)}
        port = 16000
        cases = []
        crt, key = certs["ecdsa-p256"]
        cases.append(("X25519 + ECDSA-P256 (classical)",
                      dict(group="X25519", cert=crt, key=key, alg="ecdsa-p256")))
        crt, key = certs["ml-dsa-65"]
        cases.append(("ML-KEM-768 + ML-DSA-65 (mutual)",
                      dict(group="MLKEM768", cert=crt, key=key, alg="ml-dsa-65")))
        cases.append(("ML-KEM-768 PSK (pre-provisioned)",
                      dict(group="MLKEM768", psk=PSK)))

        print(f"{'configuration':38s}{'n':>3s}{'bytes':>8s}{'mean T(s)':>11s}"
              f"{'sd':>7s}{'min':>8s}{'max':>8s}")
        rows = []
        for label, cfg in cases:
            bs, ts = [], []
            for i in range(N):
                port += 2
                if cfg.get("psk"):
                    r = lm.measure(cfg["group"], "", "", "psk", RATE, DELAY,
                                   port, psk_hex=cfg["psk"])
                else:
                    r = lm.measure(cfg["group"], cfg["cert"], cfg["key"],
                                   cfg["alg"], RATE, DELAY, port,
                                   client_cert=cfg["cert"], client_key=cfg["key"])
                if r.ok:
                    bs.append(r.total_bytes); ts.append(r.wall_ms / 1000.0)
            if not ts:
                print(f"{label:38s}  all runs failed"); continue
            mean = statistics.mean(ts)
            sd = statistics.stdev(ts) if len(ts) > 1 else 0.0
            print(f"{label:38s}{len(ts):3d}{int(statistics.mean(bs)):8d}"
                  f"{mean:11.3f}{sd:7.3f}{min(ts):8.3f}{max(ts):8.3f}")
            rows.append(dict(configuration=label, n=len(ts),
                             bytes=int(statistics.mean(bs)),
                             mean_s=round(mean, 4), sd_s=round(sd, 4),
                             min_s=round(min(ts), 4), max_s=round(max(ts), 4)))
        with open(OUT, "w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)
        print(f"wrote {OUT}", file=sys.stderr)

if __name__ == "__main__":
    main()
