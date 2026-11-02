#!/usr/bin/env python3
"""delay_sweep.py -- hold the rate fixed and vary the propagation delay.

Why this exists
---------------
The rate sweep in rate_sweep.py varies bandwidth at a fixed 250 ms one-way
delay, which is the geostationary beyond-line-of-sight profile of DO-362.
That answers "does the penalty depend on rate" but not "does it depend on
delay", and the paper's conclusion -- migration costs most on the links with
the least bandwidth -- is a joint statement about the two.  A referee is
entitled to ask whether the result survives a low-earth-orbit profile, which
is 20-60 ms rather than 250 ms.

Design
------
Rate is held at 9.6 kbps per direction and the one-way delay takes four
values:

    0 ms     the same-host floor, which isolates serialisation
    40 ms    low earth orbit, the third regime a UAV operator meets
    250 ms   geostationary, the DO-362 point used elsewhere in the paper
    600 ms   geostationary plus a bent-pipe transponder and processing

Three configurations, three runs per cell.  The 250 ms cell overlaps the
eight runs of loss_sweep.py and the five of repeat.py; it is repeated here so
that every point in this table comes from one batch and the comparison
across delay is not confounded by batch drift.

Output: results/delay_sweep.csv, one row per run.
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

RATE = 9600
DELAYS = (0, 40, 250, 600)
N = 3
SEED0 = 9100


def main() -> None:
    out = os.path.join(HERE, "..", "results", "delay_sweep.csv")
    with tempfile.TemporaryDirectory() as td:
        certs = {a: (c, k) for a, c, k in lm.make_certs(td)}
        rows = []
        port = 26000
        for delay in DELAYS:
            for label, group, alg in CASES:
                ts, bs = [], []
                for run in range(N):
                    port += 2
                    try:
                        if alg == "psk":
                            r = lm.measure(group, "", "", "psk", RATE, delay,
                                           port, psk_hex=PSK, seed=SEED0 + run)
                        else:
                            c, k = certs[alg]
                            r = lm.measure(group, c, k, alg, RATE, delay,
                                           port, client_cert=c, client_key=k,
                                           seed=SEED0 + run)
                    except Exception as exc:                # noqa: BLE001
                        print(f"  ! {label} delay={delay} run={run}: {exc}",
                              file=sys.stderr)
                        continue
                    if not r.ok:
                        print(f"  ! {label} delay={delay} run={run}: not ok",
                              file=sys.stderr)
                        continue
                    ts.append(r.wall_ms / 1000.0)
                    bs.append(r.total_bytes)
                    rows.append(dict(rate_bps=RATE, delay_ms=delay, config=label,
                                     group=group, cert_alg=alg, run=run,
                                     bytes=r.total_bytes,
                                     t_s=round(r.wall_ms / 1000.0, 3), ok=r.ok))
                if ts:
                    print(f"delay={delay:4d}  {label:24s} n={len(ts)}  "
                          f"b={int(statistics.mean(bs)):6d}  "
                          f"mean={statistics.mean(ts):7.3f}  "
                          f"min={min(ts):7.3f}  max={max(ts):7.3f}",
                          file=sys.stderr)

    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {out} ({len(rows)} rows)", file=sys.stderr)


if __name__ == "__main__":
    main()
