#!/usr/bin/env python3
"""burst_bound.py -- what a bursty channel does to the loss numbers, analytically.

The paper's loss experiments drop TCP segments independently.  Real narrowband
links fade in bursts, and a reviewer is right to ask what that changes.  It
changes two things in opposite directions, and both can be bounded without a
new testbed.

Model.  A two-state Gilbert-Elliott channel: state G loses nothing, state B
loses every segment.  With stationary bad-state probability p and mean burst
length L segments, a handshake of n segments meets

    episodes ~ n * p / L        contiguous runs of loss
    drops    ~ n * p            individual lost segments

The emulator charges one retransmission timeout per *dropped segment*, which is
what a stack without selective acknowledgement does.  A stack with SACK, which
is what a real link runs, charges one recovery episode per *run*: it
retransmits the whole hole in one timeout.  So for a fixed loss rate the real
mean penalty scales as 1/L, and the measured numbers --- taken at L = 1 --- are
an upper bound on it.

The tail goes the other way.  A run of L segments is L * segment_time seconds
of dead air, and the emulator cannot produce a stall longer than one RTO.  So
the worst case is understated, without bound in the model.

Usage:  python harness/burst_bound.py [--rate 9600] [--mss 1460] [--rto 1200]
"""
from __future__ import annotations

import argparse


def segment_time(rate_bps: float, mss: int) -> float:
    """Seconds of airtime one full segment occupies at the given rate."""
    return mss * 8.0 / rate_bps


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rate", type=float, default=9600, help="bit/s, one direction")
    ap.add_argument("--mss", type=int, default=1460, help="bytes per segment")
    ap.add_argument("--rto", type=float, default=1200, help="ms per timeout")
    ap.add_argument("--segments", type=int, default=16,
                    help="segments charged per 20,840-byte handshake")
    ap.add_argument("--slope", type=float, default=0.446,
                    help="measured seconds per injected drop (Section 4.6)")
    args = ap.parse_args()

    seg = segment_time(args.rate, args.mss)
    rto = args.rto / 1000.0
    n = args.segments

    print(f"link: {args.rate:.0f} bit/s, MSS {args.mss} B, "
          f"segment airtime {seg:.3f} s, RTO {rto:.1f} s")
    print(f"handshake: {n} charged segments; measured slope {args.slope:.3f} s/drop")
    print()

    losses = (0.001, 0.01, 0.05, 0.10, 0.20)
    bursts = (1, 3, 10)

    print("Mean penalty under correlated loss, relative to the independent model")
    print(f"{'p':>7s} {'drops':>6s} " +
          "".join(f"{'L=' + str(b):>10s}" for b in bursts) +
          f"{'indep (s)':>11s}")
    for p in losses:
        drops = n * p
        row = f"{p:7.3f} {drops:6.2f} "
        for b in bursts:
            episodes = drops / b
            row += f"{args.slope * episodes:10.3f}"
        row += f"{args.slope * drops:11.3f}"
        print(row)

    print()
    print("Worst-case single stall, which the independent model cannot express")
    print(f"{'L':>7s} {'dead air (s)':>13s} {'+ RTO (s)':>11s}")
    for b in bursts:
        print(f"{b:7d} {b * seg:13.2f} {b * seg + rto:11.2f}")

    print()
    print("Reading: for a fixed loss rate, burstiness lowers the mean penalty by")
    print(f"roughly the burst length (column L=10 is ~10x below the independent")
    print("column), while raising the worst case to a level the independent model")
    print(f"cannot reach at all ({bursts[-1] * seg:.1f} s against {rto:.1f} s). The mean")
    print("numbers in the paper are therefore pessimistic and the tails optimistic,")
    print("which is the direction a migration study should err in for the mean but")
    print("not for the tail.")


if __name__ == "__main__":
    main()
