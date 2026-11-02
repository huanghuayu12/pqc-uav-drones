#!/usr/bin/env python3
"""run_all.py -- regenerate every measurement behind the paper.

The paper's tables and figures are produced by the scripts below, in the
order listed.  Nothing is typed in by hand: each table is either read from a
CSV in results/ or derived from one by arithmetic stated in the text.

Running everything takes roughly an hour and overwrites results/.  Use
`--quick` for the steps that only re-derive numbers from data already on
disk, and `--list` to see what there is.

    python run_all.py --list
    python run_all.py --quick        # ~1 minute, no link emulation
    python run_all.py                # everything, ~1 hour
    python run_all.py --only rate_sweep delay_sweep

Requirements: Python 3.10+, matplotlib, numpy, and an `openssl` CLI that
knows ML-KEM and ML-DSA (3.5 or later).  See REPRODUCE.md.
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.abspath(__file__))

# (name, script, kind, what it produces)
#   kind "fast"    -- seconds, reads what is already in results/
#   kind "measure" -- minutes, drives the emulated link
STEPS = (
    ("msg_anatomy",   "harness/msg_anatomy.py",   "fast",
     "DER and record anatomy; the 5,549 = 35 + 5,514 closure"),
    ("dtls_bound",    "harness/dtls_bound.py",    "fast",
     "RFC 9147 framing bound; the DTLS numbers in Section 3.4"),
    ("compute_cost",  "harness/compute_cost.py",  "fast",
     "results/compute_cost.json; the compute margin in Section 3.4"),
    ("record_breakdown", "harness/record_breakdown.py", "measure",
     "results/record_breakdown.json; Tables 3 and 4"),
    ("repeat",        "harness/repeat.py",        "measure",
     "results/repeatability.csv; Table 13"),
    ("sweep_repeat",  "harness/sweep_repeat.py",  "measure",
     "results/sweep_repeat.csv; the sd column of Table 7"),
    ("rate_sweep",    "harness/rate_sweep.py",    "measure",
     "results/rate_sweep.csv; Table 8 and Figure 4"),
    ("delay_sweep",   "harness/delay_sweep.py",   "measure",
     "results/delay_sweep.csv; Table 9"),
    ("loss_sweep",    "harness/loss_sweep.py",    "measure",
     "results/loss_sweep.csv; Table 11"),
    ("loss_low",      "harness/loss_low.py",      "measure",
     "results/loss_low.csv; the 0.1-1 % paragraph in Section 4.7"),
    ("chain_depth",   "harness/chain_depth.py",   "measure",
     "results/chain_depth.csv; Table 14"),
    ("oneway",        "harness/oneway.py",        "measure",
     "results/oneway.csv; the mutual-vs-server-only paragraph"),
    ("resumption_live", "harness/resumption_live.py", "measure",
     "results/resumption.csv; the resumption numbers in Section 5.2"),
    ("plot",          "sim/plot_measured.py",     "fast",
     "all seven figures, from results/"),
)

# Link measurements are slow on purpose: 9.6 kbps is 9.6 kbps.  None of these
# scripts has a "faster" mode, because speeding them up would change the
# quantity being measured.


def check_prereqs() -> list[str]:
    problems = []
    exe = shutil.which("openssl")
    if not exe:
        problems.append("openssl not on PATH")
    else:
        out = subprocess.run([exe, "version"], capture_output=True, text=True)
        ver = out.stdout.strip()
        # ML-KEM and ML-DSA landed in 3.5.  Anything older cannot run the testbed.
        try:
            major, minor = (int(x) for x in ver.split()[1].split(".")[:2])
            if (major, minor) < (3, 5):
                problems.append(f"{ver}: need OpenSSL 3.5 or later")
        except (IndexError, ValueError):
            problems.append(f"could not parse openssl version: {ver!r}")
    try:
        import matplotlib  # noqa: F401
    except ImportError:
        problems.append("matplotlib not installed (pip install -r requirements.txt)")
    return problems


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true",
                    help="only the steps that re-derive from existing data")
    ap.add_argument("--list", action="store_true", help="show the steps and exit")
    ap.add_argument("--only", nargs="+", metavar="NAME", help="run just these")
    ap.add_argument("--keep-going", action="store_true",
                    help="continue after a failing step (default: stop)")
    args = ap.parse_args()

    if args.list:
        for name, script, kind, what in STEPS:
            print(f"{name:18s} {kind:8s} {what}")
        return 0

    if args.only:
        unknown = set(args.only) - {s[0] for s in STEPS}
        if unknown:
            print(f"unknown step(s): {', '.join(sorted(unknown))}", file=sys.stderr)
            return 2
    steps = [s for s in STEPS if (not args.only or s[0] in args.only)
             and (not args.quick or s[2] == "fast")]

    problems = check_prereqs()
    if problems:
        print("prerequisites missing:", file=sys.stderr)
        for p in problems:
            print(f"  - {p}", file=sys.stderr)
        return 1

    if not args.quick and not args.only:
        print("This overwrites results/ and takes about an hour.", file=sys.stderr)
        print("Press Ctrl-C within 5 s to abort.", file=sys.stderr)
        try:
            time.sleep(5)
        except KeyboardInterrupt:
            return 130

    failed = []
    t0 = time.time()
    for name, script, kind, what in steps:
        print(f"\n=== {name} [{kind}] {what}", flush=True)
        t = time.time()
        rc = subprocess.call([sys.executable, os.path.join(ROOT, script)],
                             cwd=ROOT)
        dt = time.time() - t
        status = "ok" if rc == 0 else f"FAILED rc={rc}"
        print(f"--- {name}: {status} in {dt:.1f}s", flush=True)
        if rc != 0:
            failed.append(name)
            if not args.keep_going:
                break

    print(f"\ntotal {time.time() - t0:.0f}s, {len(steps) - len(failed)} ok, "
          f"{len(failed)} failed")
    if failed:
        print("failed: " + ", ".join(failed), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
