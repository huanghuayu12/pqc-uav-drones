# Reproducing the measurements

Every number in the paper comes from one of the scripts in `harness/`, either
directly or by arithmetic stated in the text. Nothing is transcribed by hand
from a terminal session.

## What you need

- Python 3.10 or later, with `matplotlib` and `numpy` (`pip install -r requirements.txt`)
- An `openssl` binary that knows **ML-KEM and ML-DSA** — 3.5 or later.
  Developed and tested against OpenSSL 3.5.7.
- No root, no `tc`, no network namespaces. The link is emulated by a userspace
  token-bucket proxy on loopback, so the testbed runs anywhere Python does.

## Quick check (about 1 minute)

```bash
python run_all.py --quick
```

Re-derives the anatomy, the DTLS bound, the compute margin and all seven
figures from what is already in `results/`. Does not touch the link.

Note that `compute_cost.json` is re-measured rather than re-read, so its
timings will differ from the published ones by about 10 % depending on host
load; the paper quotes two significant digits for exactly this reason.

## Full reproduction (about 1 hour)

```bash
python run_all.py
```

Runs the link measurements in dependency order. **This overwrites `results/`.**
Copy the directory first if you want to keep the published numbers:

```bash
cp -r results results.published
```

Individual steps:

```bash
python run_all.py --list
python run_all.py --only rate_sweep delay_sweep
```

## Which script produces which table

| Table | Content | Script / file |
|---|---|---|
| 1 | Object sizes from FIPS 203/204/205 | standards, not measured |
| 2 | The five measurement pitfalls | no data — a record of what went wrong |
| 3 | TLS records of the handshake | `record_breakdown.py` → `record_breakdown.json` |
| 4 | Byte attribution, six configurations | same |
| 5 | 4 × 4 key-exchange / certificate matrix | `real_9600_sweep.csv` |
| 6 | Per-message reconstruction | `msg_anatomy.py` |
| 7 | Certificate parameter sweep + sd | `real_9600_sweep.csv`, `real_64k_sweep.csv`, `sweep_repeat.csv` |
| 8 | Rate sweep, 2.4–38.4 kbps | `rate_sweep.py` → `rate_sweep.csv` |
| 9 | Delay sweep, 0–600 ms | `delay_sweep.py` → `delay_sweep.csv` |
| 10 | Certificates vs pre-shared key | `real_psk_9600.csv` |
| 11 | Loss sweep | `loss_sweep.py`, `loss_low.py` |
| 12 | The remedy ladder | derived: `real_9600_sweep.csv` + FIPS object sizes |
| 13 | Repeatability, one batch of five | `repeatability_raw.py` → `repeatability_raw.csv` (batches 2 and 3: `repeatability_raw2.csv`, `repeatability_raw3.csv`) |
| 14 | Chain depth, one vs two intermediates | `chain_depth.py` → `chain_depth.csv` |

| Figure | Script |
|---|---|
| 1 ticket artefact | `sim/plot_measured.py` (see caveat below) |
| 2 byte breakdown | `sim/plot_measured.py` from `record_breakdown.json` |
| 3 certificate sweep | from `real_9600_sweep.csv`, `real_64k_sweep.csv` |
| 4 rate sweep | from `rate_sweep.csv` |
| 5 testbed schematic | drawn in `sim/plot_measured.py` |
| 6 loss | from `loss_sweep.csv` |
| 7 remedy ladder | from `real_9600_sweep.csv` + the FN-DSA prediction |

## What does not reproduce here

Three numbers in the paper are not measurements and are labelled as such in
the text. Do not expect `run_all.py` to produce them.

- **DTLS overhead** (`dtls_bound.py`) is computed from RFC 9147, not measured.
  There is no post-quantum DTLS to measure on this stack: OpenSSL 3.5.7 offers
  DTLS 1.0 and 1.2 only, and both reject an ML-DSA certificate or an ML-KEM
  group.
- **FN-DSA-512** is extrapolated along the measured marginal throughput.
  OpenSSL has no Falcon implementation, so its byte count follows from the
  object sizes and its time from the slope.
- **Cortex-M4 cycle counts** are cited from the literature, not measured.
- **The burst bound** (`burst_bound.py`) is closed-form, not a simulation: it
  takes the measured 0.446 s per injected drop and re-charges it per burst
  episode instead of per lost segment. Its inputs are the segment airtime and
  the burst length, both arguments of the script.
- **Table 8's two runs per cell** are what was measured; the table note quotes
  the resulting spread (largest 1.9 %, median 0.3 %) rather than a standard
  deviation, which two runs cannot support.

## Figure 1 is the one exception to "no hand-entered numbers"

The two bars of Figure 1 come from `record_breakdown.py` run twice, once with
server-side ticket suppression and once without. The values are entered as
constants in `fig5()` of `sim/plot_measured.py` because `record_breakdown.py`
disables tickets by default and has no flag to re-enable them. The underlying
claim is checkable — the two post-handshake records are 79 bytes with the flag
and 5,775 without — but reproducing the figure requires editing
`link_measure.py` to drop `-no_ticket` from the server command line, re-running
`record_breakdown.py`, and comparing. This is a gap in the artifact, not in the
measurement.

## Determinism and variance

- **Packet loss** is drawn from a seeded RNG per run; the same seed gives the
  same drops. Different seeds give different drops, which is why the loss
  tables report means over repeats.
- **Post-quantum byte counts are exact.** ML-DSA signatures are fixed-length,
  and `make_certs()` pins the certificate serial number to a fixed 20-byte
  value, so a 20,840-byte handshake is 20,840 bytes in every run.
- **The classical baseline moves by ±2 bytes** between runs, because an ECDSA
  signature is variable-length DER and occasionally gains a leading zero.
  Ratios in the paper are therefore always formed **within one batch**; the
  paper says so in Section 4.1.
- **Timing** varies with host load. Repeats of the same cell differ by about
  0.01–0.02 s; the compute benchmark by under 10 %.

## Ports

Scripts bind loopback ports in the range 27000–31901, two per measurement. Run
them sequentially — `run_all.py` does — or two concurrent runs will collide.
