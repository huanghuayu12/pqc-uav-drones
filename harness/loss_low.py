#!/usr/bin/env python3
"""loss_low.py -- the loss regime real links operate in.

loss_sweep.py sweeps 10 % and 20 % per segment, which is one to two orders of
magnitude above a well-engineered beyond-line-of-sight link.  At those rates
the mean shift is large and easy to measure; at realistic rates almost every
handshake is clean and the quantity that matters is the tail, not the mean.
This script measures 0.1 %, 0.5 % and 1 %, with a clean baseline in the same
batch so that every delta is computed within batch, five runs per cell.

Output: results/loss_low.csv, one row per run.
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

CASES = [
    ("X25519 + ECDSA-P256",    "X25519",   "ecdsa-p256"),
    ("ML-KEM-768 + ML-DSA-65", "MLKEM768", "ml-dsa-65"),
    ("ML-KEM-768 + PSK",       "MLKEM768", "psk"),
]
LOSSES = (0.0, 0.001, 0.005, 0.01)
RATE, DELAY = 9600, 250
N = 5
SEED0 = 9700


def main() -> None:
    out = os.path.join(HERE, "..", "results", "loss_low.csv")
    with tempfile.TemporaryDirectory() as td:
        certs = {a: (c, k) for a, c, k in lm.make_certs(td)}
        rows = []
        port = 28000
        for lp in LOSSES:
            for label, group, alg in CASES:
                ts, ds, bs = [], [], []
                for run in range(N):
                    port += 2
                    try:
                        if alg == "psk":
                            r = lm.measure(group, "", "", "psk", RATE, DELAY,
                                           port, psk_hex=PSK, loss_prob=lp,
                                           seed=SEED0 + run)
                        else:
                            c, k = certs[alg]
                            r = lm.measure(group, c, k, alg, RATE, DELAY, port,
                                           client_cert=c, client_key=k,
                                           loss_prob=lp, seed=SEED0 + run)
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
                    print(f"p={lp:5.3f}  {label:24s} n={len(ts)}  "
                          f"b={int(statistics.mean(bs)):6d}  "
                          f"drops={statistics.mean(ds):4.2f}  "
                          f"mean={statistics.mean(ts):7.3f}  "
                          f"max={max(ts):7.3f}", file=sys.stderr)

    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {out} ({len(rows)} rows)", file=sys.stderr)


if __name__ == "__main__":
    main()
