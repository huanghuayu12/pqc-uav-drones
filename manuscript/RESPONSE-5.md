# RESPONSE-5 — Fourth external review (major revision, leaning light)

The review was checked against the current source (`manuscript/main.tex`, commit
`d37da90` and this revision) before anything was changed. A number of items
describe a PDF that predates the last two revision rounds; those are listed in
Part C with the verification that was run. Everything in Part A was a real
defect in the current text and is fixed. Part B lists judgement calls taken the
way the review suggested.

---

## Part A — Real defects, fixed in this revision

**A1. Table 3 / text / Figure 1: 10,468→21,860 (+11,392) vs "+11,396 (+54.7%)".**
Real, and the four bytes are not a bookkeeping slip. Re-measured
(`harness/record_breakdown.py`, re-run locally on OpenSSL 3.5.7): with tickets
enabled the *client* flight also grows, 10,372 → 10,376, because the client
then offers the empty `session_ticket` extension (type 35, length 0), which
`-no_ticket` suppresses; its ClientHello grows 1,357 → 1,361 bytes. So the two
directions grow by 11,392 and 4 bytes, and the 11,396-byte total is their sum.
Section 3.3 item (5) and the Table 3 caption now state this explicitly, and
`results/ticket_artefact.csv` already carried the client-side column.

**A2. §4.4 "the byte gap is 18,928 bytes in four of the five rows".**
Wrong as written: the gaps are 18,925 (4.8 kbps), 18,927 (9.6), 18,928 (19.2)
and 18,927 (38.4). The paragraph now gives both absolute numbers per row
(20,658 against 1,913 at 2.4 kbps; 20,840 against 1,912–1,915 above it),
states the gaps as 18,925–18,928, and derives the 183-byte shortfall as
182 + 1 from the two window-boundary artefacts.

**A3. §5.3 chain-depth arithmetic.**
The "2×5,544 = 11,088 ... 160 bytes" passage did not resolve: 5,541 + 3 + 2 =
5,546, not 5,544, and 2×5,546 = 11,092 ≠ 11,088. Rewritten around the measured
DER sizes (leaf 5,514, intermediate 5,541, depth-two leaf 5,592 — re-verified
by regenerating the hierarchy): naive estimate 2×5,514 = 11,028, measured
11,248, and the 220 bytes resolve as 2×27 (intermediate encoding) + 2×5 (list
framing) + 2×78 (leaf growth). 2×5,546 + 2×78 = 11,248 retained, now derivable.

**A4. §5.3 "leaving 238 bytes ... once the three-byte TLS header is counted".**
Both numbers were wrong: 5,514 − 1,952 − 3,309 = 253 (the X.509 framing figure
Table 7 already uses), and the TLS framing is 35 bytes, not 3. Fixed; the
sentence now reads 253 + 35 = 5,549, consistent with Table 7.

**A5. Table 13 (ladder) classical row "1,914 / 1.98".**
That value matches no stored batch (matrix batch: 1,915/1.99; repeatability
batch: 1,916/1.989). Changed to 1,915/1.99 and the batch index (A6) records
which batch each baseline comes from.

**A6. Four classical baselines.**
New Table 6 (§4.1) lists the four batches (loss 1,912; attribution 1,913;
matrix 1,915; repeatability 1,916), the tables each backs, and states that
the rate and delay sweeps are further batches that form ratios row by row.

**A7. FN-DSA-512 extrapolation flagged too weakly in abstract and conclusion.**
Abstract now reads "FN-DSA-512, *extrapolated along the measured slope*, gains
only 12–13 %"; the conclusion reads "the *extrapolated* FN-DSA-512 point saves
a further 1.15 s". The labelling in Table 13, Figure 7 and §4.8/§5.6 was
already in place.

**A8. §3.3 "the 5,759-byte records".**
Stale number from an earlier measurement; the records are 5,775 bytes
(5,696 + 79). Fixed.

## Part B — Reviewer suggestions adopted as phrasing/scope changes

- **Abstract ratio.** Now states both: "7.2 times the key exchange on the wire,
  7.8 on the standards objects alone"; the introduction points to §4.2 for why
  they differ.
- **PSK recommendation precondition.** Conclusion now reads "Operators who can
  answer no should pre-provision *if they already run a key-distribution
  mechanism*, and be done", matching §5.1's precondition and §5.4's break-even.
- **DTLS bound in the conclusion.** Now says the 4 % figure of §3.4 is a
  framing-only bound that excludes IP/UDP headers and flight-level
  retransmission, both of which raise it.
- **"only widens as the link gets harder"** → "widens across the measured
  range. Below 2.4 kbps we have no measurement, and the trend is an
  extrapolation there."
- **"conservative for every link an operator is likely to buy"** →
  "for any single-hop link in the measured range — 0 to 600 ms, 2.4 to
  38.4 kbps".
- **§2.3 [xia2024ligkyx].** "is consistent with a pre-provisioned design" →
  "a pre-provisioned design is one explanation ..., though a single total
  cannot distinguish that from a handshake that simply carried a shorter
  chain, and we claim only the first reading"; "evidence for the thesis" →
  "consistent with the thesis".
- **§5.2 ticket behaviour.** The exact `s_server` invocation is now given
  (displayed command line), the three option variants are named, and the claim
  is explicitly scoped: tested on 3.5.7 only, other patch releases not tested.
- **§5.6 desktop-OS sentence.** Replaced with the suggested shape: the stack is
  a production TLS implementation on a desktop OS, and porting it to a given
  avionics platform (RAM/flash/OSAL) is a separate question the paper does not
  address.
- **Chunk-size sensitivity (§3.2/§5.6).** No such experiment exists; the
  emulator forwards whatever `recv` returns, so chunk size is not a parameter
  of ours. §3.2 now says the composition argument "is an argument, not a
  measurement", states which way the error moves, and §5.6 records it as a
  limitation.
- **Table 4 PSK rows.** The caption caveat is now repeated in the body text:
  the 316-byte residual of the PSK rows is Finished and framing, not identity,
  and the 45.0 %/10.9 % shares are tabulated for column completeness.
- **Table 7 decomposition in the body.** The 35-byte framing breakdown and the
  1,952 + 3,309 + 253 DER split moved from the caption into §4.2's text, with
  the caption trimmed to avoid duplication.
- **Data Availability.** Now lists the harness script behind each table and
  figure, states that Table 7's contents column is arithmetic rather than
  measurement, and points at the new README mapping section.

## Part C — Items that describe an earlier PDF (verified present/clean now)

Verified on the rebuilt PDF (34 pp) by rendering the pages and by text
extraction; renders are kept in `.render/`.

| Review item | Status in current build |
|---|---|
| Duplicate "An assessment of what compact signatures..." on p. 3 | Absent. The contributions list has six single items (p. 3 render). |
| "1 Two measurements of remedies..." numbering chaos on p. 3 | Absent; the list is a plain `itemize`, no numbers. |
| Page 22 "1 1 1 1 ..." garbage for about a page | Absent. Page 22 (now p. 23) holds §4.8, Table 13 and Figure 7, all clean. No "1 1 1 1" pattern anywhere in the extracted text. |
| Table 12 cited but missing | Present: the byte-cost ladder is §4.8's own table (Table 13 in the current build), referenced in §4.8, §5.6 and the conclusion. |
| Table 1 FN-DSA row "897-666" | Renders correctly as separate public-key (897) and signature (666) columns with an em-dash in the ciphertext column. |
| "e-mail@1", "\(\mathrm{\Delta A >}\)" residue in Author Contributions | The `<<e-mail@1>>` strings are the unfilled author-block placeholders (28 of them; only the authors can fill these). The reviewer's `\mathrm{\Delta A}` residue does not exist in the source; the only `\Delta` uses are the intentional `$\Delta T$` column headers of the loss table. |
| Figure 1 caption vs Table 3 vs text | See A1: all three now agree, and the 4-byte client-side difference is explained rather than papered over. |
| §4.6 "three links" needs a cross-reference | Already present in the current text: "in the twenty-aircraft, three-station fleet of Section 5.4 ...". |
| Table 5 single-run cells | The matrix caption already states the ±0.02 s interval from the repeatability section, and §5.6 states what single runs can and cannot resolve (20 % effect vs 0.16 %/4.6 % pooled CVs). Adding per-cell repeats is the one suggestion not adopted, because the matrix is single-run *by design* and the interval it carries is stated; the reviewer's alternative (a table note) is exactly what is there. |

## Remaining before submission

- The 28 `<<...>>` placeholders (author block ×12, CRediT ×15, funding ×1) —
  author-supplied only.
- One human pass over the final PDF (the render pipeline used here is
  Ghostscript; a native PDF viewer check of Tables 3, 6, 7 and 13 is advised).
