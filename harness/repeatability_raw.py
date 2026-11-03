#!/usr/bin/env python3
"""repeatability_raw.py -- the raw runs behind Table 13.

Table 13 reported a mean and a standard deviation per configuration, but only
the aggregate was kept (results/repeatability.csv).  For a paper whose claim is
reproducibility that is backwards: a reader can check an aggregate only by
re-running it, whereas per-run rows can be checked by inspection.  This script
regenerates the batch as one row per handshake, in a single batch so that the
three configurations share a link state.
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

CASES = (("X25519 + ECDSA-P256",                  "X25519",   "ecdsa-p256"),
         ("ML-KEM-768 + ML-DSA-65 (mutual)",      "MLKEM768", "ml-dsa-65"),
         ("ML-KEM-768 PSK (pre-provisioned)",     "MLKEM768", "psk"))
RATE, DELAY = 9600, 250


def main() -> None:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", type=int, default=5)
    ap.add_argument("--out", default="repeatability_raw.csv")
    ap.add_argument("--port0", type=int, default=32000)
    args = ap.parse_args()
    N = args.runs
    out = os.path.join(HERE, "..", "results", args.out)
    rows = []
    with tempfile.TemporaryDirectory() as td:
        certs = {a: (c, k) for a, c, k in lm.make_certs(td)}
        port = args.port0
        for run in range(N):
            for label, group, alg in CASES:
                port += 2
                if alg == "psk":
                    r = lm.measure(group, "", "", "psk", RATE, DELAY, port,
                                   psk_hex=PSK, seed=7100 + run)
                else:
                    c, k = certs[alg]
                    r = lm.measure(group, c, k, alg, RATE, DELAY, port,
                                   client_cert=c, client_key=k, seed=7100 + run)
                if not r.ok:
                    print(f"  ! {label} run={run}: not ok", file=sys.stderr)
                    continue
                rows.append(dict(config=label, run=run, bytes=r.total_bytes,
                                 t_s=round(r.wall_ms / 1000.0, 4), ok=r.ok))

    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["config", "run", "bytes", "t_s", "ok"])
        w.writeheader()
        w.writerows(rows)

    for label, _, _ in CASES:
        v = [r["t_s"] for r in rows if r["config"] == label]
        if not v:
            continue
        sd = statistics.stdev(v)
        b = [r["bytes"] for r in rows if r["config"] == label][0]
        print(f"{label:36s} n={len(v)} b={b:6d} "
              f"mean={statistics.mean(v):7.4f} sd={sd:6.4f} "
              f"cv={100*sd/statistics.mean(v):5.2f}% "
              f"min={min(v):7.4f} max={max(v):7.4f}", file=sys.stderr)
    print(f"wrote {out} ({len(rows)} rows)", file=sys.stderr)


if __name__ == "__main__":
    main()
