#!/usr/bin/env python3
"""compute_cost.py -- how much of the handshake is arithmetic, and how much
could ever be.

The paper's premise is that bandwidth, not computation, is the binding
constraint on a 9.6 kbps C2 link.  That premise was cited rather than
measured, which is the one place a referee can reasonably press: if the
target is a small MCU, is the premise still true?

This script does not answer that with an MCU measurement.  It answers it
with a margin: it measures the arithmetic on the machine that runs the
testbed, then asks how much slower a processor would have to be before
computation matched transmission.  The margin is the answer, because it
is far larger than the gap between any desktop core and any flight
controller.

Measured operations for a mutual-authentication TLS 1.3 handshake:

    two ML-DSA signatures      (one CertificateVerify per side)
    two verifications          (one per side)
    one ML-KEM keygen + one encapsulation + one decapsulation

X.509 parsing, hashing of the transcript and AEAD are omitted; they are
microseconds against the numbers below and can only raise the compute
share, never lower it.

Usage:
    python harness/compute_cost.py [--wall 11.27] [--out results/compute_cost.json]
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

# (openssl speed name, label).  Names are the ones `openssl speed` accepts;
# "mldsa65" is rejected by OpenSSL 3.5.7, "ML-DSA-65" is accepted.
# `openssl speed` prints its column names on the header line and only numbers
# on the data line, and the header is not machine-readable when the algorithm
# label contains spaces ("256 bits ecdsa (nistp256)").  So the column names are
# declared here rather than parsed, and the count is checked against the row.
SIGS = (("ML-DSA-44", "ml-dsa-44", ("keygen", "signs", "verify")),
        ("ML-DSA-65", "ml-dsa-65", ("keygen", "signs", "verify")),
        ("ML-DSA-87", "ml-dsa-87", ("keygen", "signs", "verify")),
        ("ecdsap256", "ecdsa-p256", ("sign", "verify")))
KEMS = (("ML-KEM-768", "mlkem768", ("keygen", "encaps", "decaps")),)

TIME = re.compile(r"(\d+\.\d+)s")


def speed(name: str, fields: tuple[str, ...]) -> dict[str, float]:
    """Run `openssl speed` for one algorithm and return seconds per op."""
    proc = subprocess.run(["openssl", "speed", "-seconds", "1", name],
                          capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"openssl speed {name} failed: {proc.stderr.strip()}")
    line = [l for l in proc.stdout.splitlines() if TIME.search(l)][-1].strip()
    times = [float(x) for x in TIME.findall(line)]
    if len(times) != len(fields):
        raise RuntimeError(f"{name}: expected {len(fields)} timings, "
                           f"parsed {len(times)} from {line!r}")
    return dict(zip(fields, times))


def handshake_cost(sig: dict[str, float], kem: dict[str, float] | None) -> dict:
    """Seconds of arithmetic for a mutual-auth handshake."""
    s = sig.get("signs", sig.get("sign"))
    v = sig.get("verify")
    out = {"sig_seconds": s, "verify_seconds": v,
           "signatures": 2 * s, "verifications": 2 * v, "kem": 0.0}
    if kem:
        out["kem"] = (kem.get("keygen", 0.0) + kem.get("encaps", 0.0)
                      + kem.get("decaps", 0.0))
        out["kem_seconds"] = kem
    out["total"] = out["signatures"] + out["verifications"] + out["kem"]
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--wall", type=float, default=11.27,
                    help="measured handshake completion time, seconds "
                         "(default: ML-KEM-768 + ML-DSA-65 at 9.6 kbps)")
    ap.add_argument("--out", default=os.path.join(HERE, "..", "results",
                                                  "compute_cost.json"))
    args = ap.parse_args()

    print(f"host: {subprocess.run(['openssl', 'version'], capture_output=True, text=True).stdout.strip()}")
    kem = {k: speed(n, f) for n, k, f in KEMS}
    sigs = {k: speed(n, f) for n, k, f in SIGS}

    rows = []
    print(f"\n{'configuration':26s} {'sign':>8s} {'verify':>8s} {'total':>10s} "
          f"{'share of':>9s} {'margin':>8s}")
    print(f"{'':26s} {'ms':>8s} {'ms':>8s} {'ms':>10s} {'11.27 s':>9s} {'x':>8s}")
    for label, key in (("ML-DSA-44", "ml-dsa-44"), ("ML-DSA-65", "ml-dsa-65"),
                       ("ML-DSA-87", "ml-dsa-87"), ("ECDSA-P256", "ecdsa-p256")):
        c = handshake_cost(sigs[key], kem["mlkem768"] if key != "ecdsa-p256" else None)
        share = c["total"] / args.wall
        margin = args.wall / c["total"]
        rows.append(dict(config=label, **{k: c[k] for k in
                                          ("sig_seconds", "verify_seconds", "total")},
                         share=share, margin=margin))
        print(f"{label:26s} {1e3*c['sig_seconds']:8.3f} {1e3*c['verify_seconds']:8.3f} "
              f"{1e3*c['total']:10.3f} {100*share:8.3f}% {margin:8.0f}")

    # Same figure for the pre-shared-key configuration: no signatures at all,
    # so the arithmetic is one KEM exchange.
    psk = handshake_cost({"signs": 0.0, "verify": 0.0}, kem["mlkem768"])
    psk_row = dict(config="ML-KEM-768 + PSK", sig_seconds=0.0,
                   verify_seconds=0.0, total=psk["total"],
                   share=psk["total"] / 3.32, margin=3.32 / psk["total"])
    print(f"{psk_row['config']:26s} {0.0:8.3f} {0.0:8.3f} {1e3*psk_row['total']:10.3f} "
          f"{100*psk_row['share']:8.3f}% {psk_row['margin']:8.0f}   (against 3.32 s)")

    worst = max(rows, key=lambda r: r["total"])
    print(f"\narithmetic is {100*worst['share']:.3f} % of the handshake for the "
          f"heaviest signature scheme ({worst['config']}).")
    print(f"for computation to match transmission on this link, the processor "
          f"would have to be {worst['margin']:.0f}x slower than the host.")
    for factor in (100, 1000):
        print(f"  at {factor:>5}x slower: {1e3*worst['total']*factor:8.1f} ms "
              f"= {100*worst['share']*factor:5.1f} % of the handshake")

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w") as fh:
        json.dump({"wall_s": args.wall, "handshakes": rows + [psk_row],
                   "kem_seconds": kem["mlkem768"]}, fh, indent=1)
    print(f"\nwrote {args.out}", file=sys.stderr)


if __name__ == "__main__":
    main()
