#!/usr/bin/env python3
"""sweep_repeat.py -- five runs per row of the certificate parameter sweep.

Table 6 of the paper reports completion time for four certificate algorithms
as single runs, and defends that with the coefficient of variation measured at
three other configurations.  A referee asked, reasonably, for the interval on
the table that carries the central time claim.  This script supplies it: four
algorithms, five runs each, same link as Table 6 (9.6 kbps per direction,
250 ms one-way), one batch.

Output: results/sweep_repeat.csv, one row per run.
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

ALGS = ("ecdsa-p256", "ml-dsa-44", "ml-dsa-65", "ml-dsa-87")
RATE, DELAY = 9600, 250
N = 5
SEED0 = 9400


def main() -> None:
    out = os.path.join(HERE, "..", "results", "sweep_repeat.csv")
    with tempfile.TemporaryDirectory() as td:
        certs = {a: (c, k) for a, c, k in lm.make_certs(td)}
        rows = []
        port = 27000
        for alg in ALGS:
            c, k = certs[alg]
            ts, bs = [], []
            for run in range(N):
                port += 2
                r = lm.measure("MLKEM768", c, k, alg, RATE, DELAY, port,
                               client_cert=c, client_key=k, seed=SEED0 + run)
                if not r.ok:
                    print(f"  ! {alg} run={run}: not ok", file=sys.stderr)
                    continue
                ts.append(r.wall_ms / 1000.0)
                bs.append(r.total_bytes)
                rows.append(dict(cert_alg=alg, run=run, bytes=r.total_bytes,
                                 t_s=round(r.wall_ms / 1000.0, 3), ok=r.ok))
            if ts:
                sd = statistics.stdev(ts) if len(ts) > 1 else 0.0
                print(f"{alg:14s} n={len(ts)} b={int(statistics.mean(bs)):6d} "
                      f"mean={statistics.mean(ts):7.3f} sd={sd:5.3f} "
                      f"cv={100*sd/statistics.mean(ts):4.2f}%", file=sys.stderr)

    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {out} ({len(rows)} rows)", file=sys.stderr)


if __name__ == "__main__":
    main()
