#!/usr/bin/env python3
"""oneway.py -- the configuration the paper did not measure.

Every number in the paper is mutual authentication, because a C2 link
authenticates both ends.  A referee can reasonably ask what the split looks
like when only the aircraft is authenticated -- a ground station that dials
out to a known server is the common shape of an uplink, and MAVLink signing
is sometimes offered as the aircraft-side check instead.

This measures it: the same link, the same certificate algorithms, with the
client certificate omitted.  Three runs per cell.

Output: results/oneway.csv
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

CASES = (("X25519 + ECDSA-P256", "X25519", "ecdsa-p256"),
         ("ML-KEM-768 + ML-DSA-65", "MLKEM768", "ml-dsa-65"))
RATE, DELAY = 9600, 250
N = 3
SEED0 = 9900


def main() -> None:
    out = os.path.join(HERE, "..", "results", "oneway.csv")
    rows = []
    port = 31000
    with tempfile.TemporaryDirectory() as td:
        certs = {a: (c, k) for a, c, k in lm.make_certs(td)}
        for label, group, alg in CASES:
            c, k = certs[alg]
            for mode in ("mutual", "server-only"):
                for run in range(N):
                    port += 2
                    kwargs = dict(client_cert=c, client_key=k) if mode == "mutual" else {}
                    r = lm.measure(group, c, k, alg, RATE, DELAY, port,
                                   seed=SEED0 + run, **kwargs)
                    if not r.ok:
                        print(f"  ! {label} {mode} run={run}: not ok",
                              file=sys.stderr)
                        continue
                    rows.append(dict(config=label, mode=mode, run=run,
                                     bytes=r.total_bytes,
                                     up=r.up_bytes, down=r.down_bytes,
                                     t_s=round(r.wall_ms / 1000.0, 3)))
                got = [x for x in rows if x["config"] == label and x["mode"] == mode]
                if got:
                    b = statistics.mean(x["bytes"] for x in got)
                    t = statistics.mean(x["t_s"] for x in got)
                    print(f"{label:24s} {mode:12s} n={len(got)} "
                          f"bytes={b:8.0f} t={t:6.2f}s", file=sys.stderr)

    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    with open(out, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {out} ({len(rows)} rows)", file=sys.stderr)


if __name__ == "__main__":
    main()
