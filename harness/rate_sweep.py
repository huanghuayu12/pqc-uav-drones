"""Measure how handshake time scales with link rate, at fixed propagation delay.

Why this exists
---------------
The paper's clean-link sweep in link_measure.py fixes one rate (9.6 kbps,
DO-362 beyond-line-of-sight) and varies the certificate algorithm; a second
run at 64 kbps used a 2 ms propagation delay, which makes it a different
link rather than the same link at a higher rate.  A reviewer is entitled to
ask whether the 5.66x certificate penalty is an artefact of picking the
slowest plausible rate.  This script answers that by varying one thing.

Design
------
Rate varies over 2.4 / 4.8 / 9.6 / 19.2 / 38.4 kbps per direction.
One-way propagation delay is held at 250 ms throughout, so every point
describes a geostationary beyond-line-of-sight link that differs only in
transponder bandwidth -- a real procurement decision, since satellite C2
bandwidth is sold in exactly these steps.

Three configurations, because they are the three the paper argues about:

    classical          X25519 + ECDSA-P256
    recommended        ML-KEM-768 + ML-DSA-65
    pre-provisioned    ML-KEM-768 + external PSK

Two runs per cell.  The 9.6 kbps cell is already covered by eight runs in
loss_sweep.py and five in repeat.py; the two runs here exist to keep this
table internally consistent (same session, same certificate set) rather
than to re-establish repeatability, which Section 4.7 does.

What the model predicts, and why the measurement is still worth doing
--------------------------------------------------------------------
If serialisation dominates, completion time should be affine in 1/rate:

    T(rate) = bytes * 8 / rate + T_fixed

so a plot of T against 1/rate should be a straight line whose slope is the
byte count and whose intercept is the fixed cost (two propagation legs plus
handshake round trips).  That gives two checks the paper cannot currently
make: whether the slope actually equals the measured byte count, and
whether the certificate and PSK lines are parallel (same slope, different
intercept would mean the difference is protocol overhead; same intercept,
different slope means it is bytes).  The paper's claim is the latter.

Output: results/rate_sweep.csv, one row per run.
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

RATES = (2400, 4800, 9600, 19200, 38400)
DELAY_MS = 250          # held constant: this is the controlled variable
N = 2
SEED0 = 7300


def main() -> None:
    out = os.path.join(HERE, "..", "results", "rate_sweep.csv")
    with tempfile.TemporaryDirectory() as td:
        certs = {a: (c, k) for a, c, k in lm.make_certs(td)}
        rows = []
        port = 24000
        for rate in RATES:
            for label, group, alg in CASES:
                ts, bs = [], []
                for run in range(N):
                    port += 2
                    try:
                        if alg == "psk":
                            r = lm.measure(group, "", "", "psk", rate, DELAY_MS,
                                           port, psk_hex=PSK,
                                           seed=SEED0 + run)
                        else:
                            c, k = certs[alg]
                            r = lm.measure(group, c, k, alg, rate, DELAY_MS,
                                           port, client_cert=c, client_key=k,
                                           seed=SEED0 + run)
                    except Exception as exc:                # noqa: BLE001
                        print(f"  ! {label} rate={rate} run={run}: {exc}",
                              file=sys.stderr)
                        continue
                    if not r.ok:
                        print(f"  ! {label} rate={rate} run={run}: not ok",
                              file=sys.stderr)
                        continue
                    ts.append(r.wall_ms / 1000.0)
                    bs.append(r.total_bytes)
                    rows.append(dict(rate_bps=rate, delay_ms=DELAY_MS,
                                     config=label, group=group, cert_alg=alg,
                                     run=run, bytes=r.total_bytes,
                                     t_s=round(r.wall_ms / 1000.0, 3),
                                     ok=r.ok))
                if ts:
                    print(f"rate={rate:6d}  {label:24s} n={len(ts)}  "
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
