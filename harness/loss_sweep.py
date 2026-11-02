"""Measure how handshake completion time responds to link loss.

The clean-link sweep in link_measure.py answers "how many bytes and how
long".  It cannot answer the question a link budget actually poses, which
is what happens when segments are lost: a certificate is 5,500 bytes, so
losing one segment of it forces a retransmission that the key exchange
never pays, and the penalty should therefore grow with the identity
material rather than with the KEM.

Design notes
------------
Loss is injected as a retransmission timeout, not as a dropped byte (see
the module docstring of link_measure.py for why a TCP proxy cannot drop
bytes).  Each configuration is repeated, because the cost of a loss is
not deterministic: a loss that lands while the peer is still transmitting
in the other direction is absorbed, and one that lands at the end of a
flight is not.  Measured at p=0.30 on ML-KEM-768 + ML-DSA-65, six runs
gave 11.28 s to 13.65 s from the same configuration, so a single run
would be meaningless.

Output is one row per run, so that the distribution rather than the mean
can be reported.
"""
from __future__ import annotations

import csv
import os
import statistics
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import link_measure as lm                                   # noqa: E402

PSK = "00112233445566778899aabbccddeeff00112233445566778899aabbccddeeff"

# The three configurations that carry the paper's argument: the classical
# baseline, the recommended post-quantum suite, and the pre-provisioned case.
CASES = [
    ("X25519 + ECDSA-P256",    "X25519",   "ecdsa-p256"),
    ("ML-KEM-768 + ML-DSA-44", "MLKEM768", "ml-dsa-44"),
    ("ML-KEM-768 + ML-DSA-65", "MLKEM768", "ml-dsa-65"),
    ("ML-KEM-768 + PSK",       "MLKEM768", "psk"),
]
LOSSES = (0.0, 0.10, 0.20)
RATE, DELAY = 9600, 250
N = 8


def main() -> None:
    out = os.path.join(HERE, "..", "results", "loss_sweep.csv")
    with tempfile.TemporaryDirectory() as td:
        certs = {a: (c, k) for a, c, k in lm.make_certs(td)}
        rows = []
        port = 22000
        for lp in LOSSES:
            for label, group, alg in CASES:
                ts, ds, bs = [], [], []
                for run in range(N):
                    port += 2
                    try:
                        if alg == "psk":
                            r = lm.measure(group, "", "", "psk", RATE, DELAY,
                                           port, psk_hex=PSK, loss_prob=lp,
                                           seed=9100 + run)
                        else:
                            c, k = certs[alg]
                            r = lm.measure(group, c, k, alg, RATE, DELAY, port,
                                           client_cert=c, client_key=k,
                                           loss_prob=lp, seed=9100 + run)
                    except Exception as exc:                # noqa: BLE001
                        print(f"  ! {label} p={lp} run={run}: {exc}",
                              file=sys.stderr)
                        continue
                    if not r.ok:
                        continue
                    ts.append(r.wall_ms / 1000.0)
                    ds.append(r.drops)
                    bs.append(r.total_bytes)
                    rows.append(dict(config=label, loss_prob=lp, run=run,
                                     group=group, cert_alg=alg,
                                     bytes=r.total_bytes, drops=r.drops,
                                     t_s=round(r.wall_ms / 1000.0, 3),
                                     ok=r.ok))
                if ts:
                    print(f"p={lp:4.2f}  {label:24s} n={len(ts)}  "
                          f"b={int(statistics.mean(bs)):6d}  "
                          f"drops={statistics.mean(ds):4.1f}  "
                          f"med={statistics.median(ts):6.3f}  "
                          f"mean={statistics.mean(ts):6.3f}  "
                          f"max={max(ts):6.3f}", file=sys.stderr)

    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {out} ({len(rows)} rows)", file=sys.stderr)


if __name__ == "__main__":
    main()
