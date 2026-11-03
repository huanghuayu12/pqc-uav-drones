# Post-Quantum C2 for UAVs — measurement package

Target: **MDPI *Drones*** (research article, measurement-based).
32 pages, 14 tables, 7 figures, 200-word abstract, 33 references.
Compiles clean on TeX Live 2026 with the official MDPI class v6.5d.

Reproduce with `python run_all.py` (see `REPRODUCE.md`). The author block is
still to be filled; `AUTHOR-INFO.md` lists what remains.

All quantitative results come from **real TLS 1.3 handshakes** measured on
OpenSSL 3.5.7 over an emulated constrained link. One exception remains and
it is labelled where it occurs: the FN-DSA-512 point, which OpenSSL cannot
run and which is extrapolated along a measured slope. Resumption (5.2) and
the depth-two chain (5.3) *were* extrapolations in an earlier draft and are
now measured; both measurements moved the number, and both corrections are
in the paper.

---

## The finding

On a 9.6 kbps / 250 ms beyond-line-of-sight C2 link, with mutual
authentication:

| Configuration | Bytes | Time | vs classical |
|---|---|---|---|
| X25519 + ECDSA-P256 (classical) | 1,915 | 1.99 s | 1.00× |
| ML-KEM-768 + ML-DSA-65 | 20,840 | 11.27 s | **5.66×** |
| ML-KEM-768 + pre-shared key | 2,902 | 3.32 s | **1.67×** |

Of the 20,840 bytes, **18,310 are certificate and signature material** and
only 2,530 are key exchange. The identity term is 7.2× the key-exchange
term. Replacing certificates with a TLS 1.3 external PSK removes 87.9 % of
the handshake, and that is worth more than every signature-algorithm choice
combined — including FN-DSA-512, which would gain only 12.6 % over the
already-standardised ML-DSA-44.

**The penalty is not rate-invariant.** Holding the 250 ms delay fixed and
moving the rate from 2.4 to 38.4 kbps, the certificate penalty runs from
**8.64× to 3.07×**. The 5.66× above is the value *at the DO-362 operating
point*, not a property of the handshake. The byte gap does not move at all;
what moves is the fraction of completion time that is serialisation.

**Adding a certificate costs more than improving one.** A second
certificate in the chain — a leaf plus an intermediate, root trusted out of
band — adds **11,248 bytes and 4.94 s**, a factor of 1.44. That is 2.2×
what shrinking ML-DSA-65 to ML-DSA-44 saves, so an operator who improves the
algorithm and then adds an intermediate has made the handshake 2.7 s
*slower*. The 160 bytes that a naive "intermediate = copy of leaf" estimate
misses are accounted for to the byte in the paper.

**Resumption is not the escape.** Measured at 3,335 bytes and 3.51 s against
12,252 and 11.26 for the cold server-authenticated handshake — a third, and
a real saving, but **433 bytes and 0.20 s more than a raw pre-shared key**.
And it is unavailable in the mutual-authentication configuration, because
OpenSSL 3.5.7's `s_server` issues no ticket when it must authenticate the
client (`-verify 0`, `-Verify 0` and `-Verify 1` all tried; only the
no-client-auth case yields a ticket). A resumed TLS 1.3 handshake
authenticates by PSK and re-runs no certificate authentication, so a server
that demands a client certificate has nothing to resume from.

Link loss does not reorder any of this. Each injected retransmission costs
**0.446 s whatever the handshake design** — the penalty is a property of the
link, and what varies between designs is only how many losses they incur.
Comparing like with like, the certificate case costs 5.23× the classical
baseline at a 20 % per-segment loss rate against 5.75× on a clean link, and
the gap between certificates and pre-shared keys is unchanged at 3.4×.

---

## Layout

```
manuscript/
  main.tex              MDPI Drones manuscript
  references.bib        33 entries, all verified against DOI or primary source
  check_tex.py          static checker (citations, refs, envs, figure paths)
  Definitions/          official MDPI class v6.5d (do not edit)
  m1..m7 .pdf/.png      figures, vector + 600 dpi raster
harness/
  link_measure.py       rate-limited proxy + handshake driver (the testbed)
  record_breakdown.py   TLS record-layer parser and byte attribution
  msg_anatomy.py        resolves the Certificate record to the byte: DER
                        anatomy, every record size, and the length check that
                        shows 5,549 = 35 framing + 5,514 DER with nothing over
  repeat.py             run-to-run variance on the three key configurations
  loss_sweep.py         loss injection sweep, 8 runs per cell
  rate_sweep.py         5 rates x 3 configurations at fixed 250 ms delay
  delay_sweep.py        4 delays (0/40/250/600 ms) x 3 configurations at
                        fixed 9.6 kbps; the LEO-vs-GEO check
  sweep_repeat.py       5 runs per row of the certificate sweep, for the sd
  loss_low.py           0.1/0.5/1 % loss: the regime real links live in
  dtls_bound.py         RFC 9147 framing bound -- PQC DTLS cannot be measured
                        on this stack, so the overhead is computed instead
  burst_bound.py        Gilbert-Elliott bound on what bursty fading changes:
                        the mean penalty falls as 1/L, the ratio does not
  repeatability_raw.py  one row per handshake behind Table 13; --runs/--out
                        so further batches can be appended
  chain_depth.py        depth-one vs depth-two hierarchy, 3 runs each
  resumption_live.py    TLS 1.3 resumption, 5 runs, with the negative
                        control that shows why the first attempt failed
  resumption_sweep.py   UNUSED — superseded by resumption_live.py; kept as a
                        record of the diagnosis that turned out to be wrong
  compute_cost.py       openssl speed on the test host, and the margin it
                        leaves: arithmetic is 0.017 % of the handshake, so
                        computation would have to be ~5,900x slower to bind
  oneway.py             mutual vs server-only authentication; shows that the
                        client certificate costs 0.10 s because it travels
                        under the server's flight
sim/
  plot_measured.py      regenerates all seven figures from results/
results/
  real_9600_sweep.csv   4 KEM x 4 certificate algorithms at 9.6 kbps
  real_64k_sweep.csv    same at 64 kbps
  real_psk_9600.csv     pre-shared-key handshakes at 9.6 kbps
  real_psk_64k.csv      same at 64 kbps
  record_breakdown.json per-message byte attribution, 6 configurations
  repeatability.csv     5 runs each for the three headline configurations
  ticket_artefact.csv   the section 3.3 artefact, with and without the flag
  loss_sweep.csv        96 runs: 4 configurations x 3 loss rates x 8 repeats
  rate_sweep.csv        30 runs: 5 rates x 3 configurations x 2 repeats
  chain_depth.csv       6 runs: depth one and depth two, 3 each
  resumption.csv        10 runs: 5 cold handshakes and 5 resumptions
  delay_sweep.csv       36 runs: 4 delays x 3 configurations x 3 repeats
  sweep_repeat.csv      20 runs: 4 certificate algorithms x 5 repeats
  loss_low.csv          60 runs: 4 loss rates x 3 configurations x 5 repeats
  repeatability_raw.csv 15 runs: 3 configurations x 5, one row per handshake
  repeatability_raw2.csv / _3.csv  two further batches of the same kind
  oneway.csv            12 runs: mutual vs server-only, 2 configurations x 3
  compute_cost.json     per-operation timings from openssl speed, and the
                        compute share of each measured handshake
archive/                the earlier model-based draft and the raw MDPI
                        template; superseded, nothing in the paper uses them
PLAN.md                 working notes, including every corrected error
```

---

## Reproducing

Everything runs on Windows or Linux with **OpenSSL 3.5+** on `PATH`, plus
**TeX Live** for the manuscript.

```bash
cd harness

# full matrix at the two link rates used in the paper (~10 min)
python3 link_measure.py --rate 9600  --delay-ms 250 --out ../results/real_9600_sweep.csv
python3 link_measure.py --rate 64000 --delay-ms 2   --out ../results/real_64k_sweep.csv

# pre-shared-key configurations
python3 link_measure.py --psk --rate 9600  --delay-ms 250 --out ../results/real_psk_9600.csv
python3 link_measure.py --psk --rate 64000 --delay-ms 2   --out ../results/real_psk_64k.csv

# byte attribution, plus the section 3.3 artefact
python3 record_breakdown.py

# variance on the three configurations that carry the argument
python3 repeat.py

# loss injection: 96 runs, ~19 min (~8 min at 64 kbps)
python3 loss_sweep.py

# rate sweep at fixed delay: 30 runs, ~9 min
python3 rate_sweep.py

# chain depth: depth one vs a real root->intermediate->leaf hierarchy
python3 chain_depth.py

# TLS 1.3 resumption (server-authenticated only; see the module docstring)
python3 resumption_live.py

# figures
cd ../sim && python3 plot_measured.py

# structural sanity check on the LaTeX
cd ../manuscript && python3 check_tex.py
```

To build the manuscript:

```bash
cd manuscript
pdflatex main && bibtex main && pdflatex main && pdflatex main
```

Expected: 32 pages, 0 undefined references, 0 overfull boxes, 33 bibitems.

To see the ticket artefact yourself:

```bash
python3 link_measure.py --rate 9600 --delay-ms 250 --allow-ticket --out /tmp/x.csv
# adds ~11.4 kB at the record layer; record_breakdown.py shows why
```

To see the loss model's calibration (why per-chunk delay is not
store-and-forward):

```bash
python3 link_measure.py --rate 9600 --delay-ms 0   --out /tmp/d0.csv
python3 link_measure.py --rate 9600 --delay-ms 250 --out /tmp/d250.csv
# the ML-KEM-768 + ML-DSA-65 row moves 10.26 s -> 11.28 s, i.e. 9 % of the
# total is repeated propagation delay and 91 % is serialisation
```

---

## What the paper claims, and what it does not

**Claims** (all measured): byte counts per direction and per TLS record;
handshake completion time at five link rates and two delays; the marginal
byte→time slope at 9.6 kbps (2,150–2,282 B/s, i.e. 90–95 % of the ideal
serial rate); how the certificate penalty varies with rate at fixed delay;
the effect of replacing certificates with a pre-shared key; the cost of a
retransmission (0.446 s) and how it scales with handshake size.

**Does not claim**: microcontroller cycle counts, RAM or energy — those are
cited from the literature (pqm4, Pornin). Resumption under mutual
authentication — it was attempted and found unavailable in this stack, which
is reported as a finding rather than as a gap (Section 5.2). Bursty loss —
the injected loss is independent and memoryless, so the tails are optimistic;
a Gilbert–Elliott channel is named as future work. DTLS — Section 3.4 argues
at length that TCP is the more forgiving transport for this workload, so the
numbers are a loss-equal lower bound along the transport dimension, but
nothing DTLS-specific was measured. Chain depth above two — depth two is now
measured; depths above it are a linear extension of that measurement,
justified by the per-entry structure of the TLS certificate list but not
independently verified.

---

## Before submitting

1. **Replace the 17 `<<...>>` placeholders** — author block (9) and the
   repository URL in the data-availability statement (8). Nothing else is
   outstanding on the manuscript itself.
2. **Deposit the data and paste the DOI.** `results/`, `harness/` and
   `sim/` are self-contained; MDPI enforces the data-availability statement.
3. **Optional but cheap:** the loss sweep uses independent per-segment loss.
   A Gilbert–Elliott run would close the last modelling gap and is already
   named as future work, so it is not required for submission.

---

## The seven measurement errors found, and where each is reported

Section 3.3 documents the first five because each one produced plausible
numbers:

1. Token bucket double-credited a wait → link ran 53 % fast (14.73 vs
   9.6 kbps). Every timing in the first pass was compressed.
2. Token bucket handed out a free 1,400-byte burst → 1.17 s of uncharged
   transfer.
3. `s_server -www` status page (~5 kB) counted as handshake.
4. Session ticket counted or not depending on link speed → 12 % swing.
5. **`-CAfile` embedded the CA certificate in every session ticket**,
   inflating the mutual-auth handshake from 20,840 to 32,236 bytes
   (+54.7 %). This one pushed in the direction of the paper's hypothesis,
   which is exactly why it is reported rather than quietly fixed.

Errors 1–4 were caught by validating the emulator against a known
transfer. Error 5 was caught by parsing the record layer: a 5,775-byte
post-handshake record cannot be explained by any field in the handshake,
and an unattributable record has to be investigated rather than averaged.

Two more surfaced while adding the loss experiment:

6. The token bucket refilled during an injected retransmission timeout,
   so a loss cost nothing: 2 drops moved the handshake by 0.012 s. Fixed
   by freezing the credit clock across the RTO.
7. Loss was counted per proxy chunk rather than per TCP segment, so a
   20,840-byte handshake and a 1,912-byte one suffered the same loss
   count and the experiment concluded, wrongly, that loss does not
   interact with handshake size.

Both are reported in the paper because both changed a published conclusion.

---

## Corrections made on 2026-11-02, second pass

- **"Resumption cannot be measured" was wrong.** The draft claimed
  OpenSSL 3.5.7 writes a TLS 1.2-style object through `-sess_out`. It does
  not: `-sess_out` works, but every measurement in the paper runs with
  `-no_ticket`, so the client was never sent a ticket to save. With tickets
  enabled, resumption measures at 3,335 B / 3.51 s. The paragraph now
  reports the measurement *and* the correction, because a wrong diagnosis
  that got published as a "bound" is worth more to a reader than a clean
  result would be.
- **The depth-two chain was arithmetic; it is now a measurement.** Building
  a real root → intermediate → leaf hierarchy gives 32,088 B / 16.22 s
  against 20,840 / 11.28 at depth one, i.e. +11,248 B and +4.94 s rather
  than the +11,088 and +5.0 s predicted. The 160-byte gap is fully
  accounted for: the intermediate encodes to 5,541 B (not 5,544), and a leaf
  verified against a parent carries `extendedKeyUsage` and `subjectAltName`
  that a self-signed leaf does not, +78 B each way.

## Corrections made on 2026-11-02, after the first full compile

These were not measurement errors but writing and citation errors, and are
recorded here because they are the kind that survive review silently:

- **An invented quotation.** The draft attributed to the MORVS Swarm SDK
  the words "alone would take 19 MAVLink frames" and the figure 4,627.
  The page says neither; it says post-quantum signatures are not
  implemented at all. Replaced with the real claim, and the frame count
  recomputed here (4,627 / 243 = 20 frames).
- **A citation that did not support its sentence.** 13.8 kB for a
  two-level ML-DSA-65 chain was attributed to RFC 6928 and the MTC draft,
  neither of which contains it. Replaced with arithmetic on the measured
  certificate (1,952 + 3,309 + 238 = 5,499 bytes).
- **Two ratios, 5.66× and 5.75×, from different batches** in the same
  paper. Now governed by an explicit batch rule in Section 4.1.
- **A claim that the penalty is rate-invariant**, which the rate sweep
  shows to be false. Corrected in Sections 4.5 and 6, the abstract and
  the conclusions.
