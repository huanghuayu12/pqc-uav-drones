# Response to Reviewer 2

Manuscript: *Where the Bytes Go: Certificate Chains, Not Key Encapsulation,
Dominate Post-Quantum Handshake Cost on Unmanned Aircraft Command-and-Control
Links*

Recommendation received: Major Revision. Six major and ten minor points.
Seven are addressed by new text, two by new analysis, two by qualification
rather than new measurement, and **three of the reviewer's numbers turned out
to be wrong in the manuscript**, which the review surfaced indirectly. Those
corrections are listed in §4 below, because they changed numbers in the paper.

A note on method: every claim below was checked against the source file or the
measurement CSV before anything was edited. Where the check contradicted the
review, the review is answered rather than followed.

---

## 1. Major points

### M1 — TCP rather than DTLS

**Accepted as a limitation, not fixed by measurement.** A DTLS 1.3 measurement
is not available on this testbed, and the reason is not effort: this stack has
no post-quantum DTLS at all. OpenSSL 3.5.7 offers DTLS 1.0 and 1.2 only, and
both reject the configuration *before* the handshake, because DTLS 1.2 cipher
suite names encode the authentication algorithm and there is no ML-KEM group;
DTLS 1.3 is unimplemented. `harness/dtls_bound.py` reproduces the check.

What changed instead:

- The abstract now reads "On TLS 1.3 over TCP, on an emulated 9.6 kbps/250 ms
  link". It previously said only "over an emulated link", which a reader could
  take as transport-agnostic.
- The conclusion now reads "should budget eleven seconds per post-quantum
  handshake on a narrowband satellite TLS link over TCP, and at least that over
  DTLS". The earlier phrasing read as if it applied to a DTLS deployment.
- §3.4 states explicitly that the RFC 9147 framing figure is a **bound, not a
  measurement**, and that the direction is conservative: DTLS retransmits whole
  flights, so its cost is at or above the TCP figure, never below.

We did not attempt a second stack. Adding wolfSSL or GnuTLS would test a
different implementation, not a different transport, unless the harness were
rebuilt around UDP and datagram semantics; that is a second paper's worth of
work and we say so rather than implying the gap is closed.

### M2 — Bursty fading, and the low-loss sample

**Accepted, and fixed analytically rather than by hand-waving.** The previous
text said the two model errors "act in different directions" and that "we have
not attempted to net them off". That was the weakest paragraph in the paper and
the reviewer is right to name it.

`harness/burst_bound.py` now gives the netting-off. On a two-state
Gilbert-Elliott channel with stationary loss rate $p$ and mean burst length $L$,
an $n$-segment handshake meets about $np$ lost segments but only $np/L$ distinct
recovery episodes, and a SACK stack charges episodes, not segments. Hence:

| Quantity | Independent model | Correlated, burst length $L$ |
|---|---|---|
| Mean penalty at $p=0.20$ | 1.43 s | 0.48 s ($L{=}3$), 0.14 s ($L{=}10$) |
| Ratio between two configurations | — | **invariant to $L$** |
| Worst single stall | 1.2 s (one RTO) | $L \times 1.22$ s, i.e. 12.2 s at $L{=}10$ |

Three consequences, all now in the paper. The mean penalty in Table 11 is an
**upper** bound under correlation. The ordering is preserved **by
construction**, since both losses and episodes scale with $n$, which is a
stronger claim than the paper previously made. And the tail is a **lower** bound,
because a 10-segment fade stalls for 12.2 s and this model cannot produce more
than one RTO. §4.7, §5.6 and the conclusion now say this in those words.

On the low-loss batch: the wording is now "the effect is smaller than the
run-to-run spread **at five runs per cell** --- not that it is zero".

### M3 — "Computation is not the bottleneck" versus "the stack runs on the MCU"

**Accepted, and the distinction is now explicit.** The reviewer is correct that
these are different claims and that the second one is what an operator cares
about. §5.6 now separates them in a dedicated paragraph:

> *Is the arithmetic affordable on a microcontroller?* Yes by three orders of
  magnitude, which is what §3.2 measures.
> *Can a complete TLS stack run on the flight controller at all?* That is a
  question about RAM, flash, an OS abstraction layer and a maintained port, and
  **nothing in this paper bears on it** --- the stack measured here needs a
  desktop operating system and would not be the one an airframe flew.

We did not claim a deployability result before, and now we say in print that we
do not have one.

### M4 — PSK operating cost

**Accepted on both counts.**

- Design rule 1 now opens with the precondition in its own clause: "Pre-provision
  trust if the operational model permits it, **and only if you already distribute
  symmetric keys**", and states that the saving is airtime while the cost is
  machinery the operator must already own.
- Revocation now carries a magnitude: twenty aircraft against three stations is
  sixty pairwise keys; replacing the aircraft side means physical or out-of-band
  contact at about an hour each, so a sixty-hour campaign and an exposure window
  measured in **weeks** at the sortie rate used in the same section, not hours.
  The certificate path is not free either — a revoked chain must still reach
  every station — but that is distribution, and distribution completes in
  seconds on the link being budgeted.

### M5 — Statistical strength of the numbers

**Accepted, and it cost us a claim.** Three changes:

1. Table 5 (the 4×4 matrix) now carries, in the caption, both "cells are single
   runs" and the interval implied by the repeatability measurement: a
   1σ of about ±0.02 s, smaller than the last digit shown.
2. Table 8 (rate sweep) — two runs per cell — now justifies the choice with the
   measured spread instead of omitting it: across the fifteen cells the largest
   within-cell difference is 1.9 %, the median 0.3 %, against a 2.8× range that
   the table exists to show. A standard deviation from two runs would be
   meaningless, so the spread is quoted instead.
3. FN-DSA is quoted as "12–13 %" in the abstract, matching the interval already
   given in §4.8.
4. **Table 13 now points at raw rows.** The old `repeatability.csv` held only an
   aggregate, which for a paper selling reproducibility is backwards: an
   aggregate can only be checked by re-running it. `harness/repeatability_raw.py`
   regenerates one row per handshake.

That last change found something, and it is the one place where this revision
makes a claim **weaker**:

**Means reproduce; spreads do not.** We ran two more batches of the same three
configurations, fifteen runs each configuration in total. The means are 2.004,
11.285 and 3.340 s — within 1 % of Table 13 — but the coefficients of variation
rise to 4.6, 0.16 and 3.4 % because two of the forty-five runs stalled: one
pre-shared-key run at 3.74 s against a 3.31 s median, and one classical run at
2.33 s against 1.96 s, both with no injected loss. Those are 0.4–0.5 s stalls,
the same order as the 0.446 s a single retransmission costs in §4.7.

The consequence is stated in the paper rather than buried. The smallest effect
the tables resolve — the 20 % between ML-DSA-65 and ML-DSA-44 — is **four
times** the largest pooled coefficient, not thirty times the cleanest one as an
earlier draft said. The margin is still adequate; the earlier phrasing was
flattering itself with a lucky batch.

### M6 — What exactly is 87.9 %

**Accepted.** The abstract now reads "are certificate, signature **and the
records carrying them**", so 18,310 is not passed off as payload alone. The
17,646 B figure, the 7.8-versus-7.2 reconciliation and the residual composition
were already in §4.1 and the Table 4 note; what was missing was the qualifier
where most readers stop. The abstract is at exactly 200 words, the MDPI ceiling,
so the three added words were bought by compressing "completes in" to "takes"
and dropping two connectives elsewhere.

---

## 2. Minor points

| # | Point | Action |
|---|---|---|
| 1 | §4.5 slope caveat buried in the caption | Moved to the **first paragraph** of §4.5, before any number: the absolute slope is a property of the emulator, only the ratio between configurations is read from it |
| 2 | §3.2 delay composition is an argument | Now says so: "That composition is an argument rather than a validation: what was checked directly is the serialisation rate, to +0.3 %" |
| 3 | Resumption finding may read as a TLS property | Already stack-scoped in the previous revision ("its server issues no ticket"); no further change |
| 4 | MAVLink reassembly buffer not quantified | Now **22 frames, 5.4 kB, 2.8 % of the 192 kB floor**, with the observation that this is buffered before a byte is authenticated. This also exposed an arithmetic error — see §4 |
| 5 | SLH-DSA numbers unsourced | Now sourced to Table 1 (from FIPS 205) and to the pqm4 measurements, with the size multiple corrected from "thirty times" to 3.2× |
| 6 | Fig 4 batch difference only in the caption | One sentence added at first citation in the body: the figure is its own batch, ratios 0.7 % and 1.8 % above Table 10, baseline differs only in ECDSA |
| 7 | Long sentences; 2026 references | Acknowledged but not systematically rewritten. Two of the three 2026 entries are an Internet-Draft and a vendor announcement rather than peer-reviewed sources, and both are now marked as such in the bibliography; whether the URLs survive to publication is outside our control |
| 8 | PSK forward secrecy and leakage radius | Forward secrecy was already evidenced (psk_dhe_ke retained; 1,088-byte ciphertext still on the wire). Leakage radius now quantified: a captured aircraft key opens **three** links for the re-keying window; a group key opens **all sixty** endpoints for the same window |

---

## 3. What we did not do, and why

- **No DTLS measurement.** Not available on this stack, as above. The paper now
  says the number is a TCP number.
- **No Cortex-M4 measurement.** The margin argument does not need one; the
  deployability question does, and that question is now marked out of scope
  rather than answered by implication.
- **No further batches on the rate and delay sweeps.** Two and three runs per
  cell respectively, justified by measured spread rather than by preference; the
  reviewer offered this as an acceptable alternative to re-running.
- **No systematic sentence-splitting pass.** Cosmetic against a revision of this
  size, and every pass risks moving a number.

---

## 4. Errors in the manuscript that this review exposed

These are ours, not the reviewer's, and they are listed because the paper's
argument depends on the numbers being checkable.

1. **MAVLink frame count was inconsistent.** The manuscript said a 5,549-byte
   certificate "spans twenty frames" while using 255 bytes of payload *and*
   counting 12 bytes of overhead inside it — a contradiction that happened to
   give the right answer for the 4,627-byte signature (20) and the wrong one for
   the certificate. A MAVLink v2 frame carries 255 bytes of payload with 12
   bytes of header and checksum *outside* it, so the correct counts are
   **22** and **19** frames. Both corrected.
2. **A new sentence of ours contained two wrong magnitudes** before it reached
   the build: SLH-DSA signatures called "thirty times" the ML-DSA-44 size
   (7,856 / 2,420 = 3.2), and lattice signing called "tens of microseconds"
   when the measurement in §3.2 is 0.39–0.71 ms. Both corrected to 3.2× and
   "well under a millisecond" before compilation.
3. **The repeatability claim quoted a lucky batch.** See M5: 0.10–0.67 % became
   up to 4.6 % when two more batches were added, and "thirty times" became
   "four times". The conclusion survives; the margin does not.

---

## 5. State of the revision

- 32 pages (was 30), 14 tables, 7 figures, 200-word abstract, 33 references,
  41/41 cross-references, 0 overfull boxes, 0 errors, 0 undefined references.
- New scripts: `harness/burst_bound.py`, `harness/repeatability_raw.py`.
- New data: `results/repeatability_raw{,_2,_3}.csv` (45 handshakes).
- Repository: https://github.com/huanghuayu12/pqc-uav-drones, commit on `main`.
- Outstanding: the author block. 28 `<<...>>` placeholders remain, all of them
  names, affiliations, e-mails, CRediT roles and the funding sentence. These
  cannot be filled by the authors of the software.
