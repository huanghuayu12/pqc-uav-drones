# Response to the re-review (Accept, minor revision)

The eight minor points are all in the text now. Three of them changed a number
or a claim rather than only a phrasing, and one exposed an asymmetry in Table 6
that I would not have found without the prompt.

One housekeeping note first, for the editor rather than the reviewer: the
report is headed *"Post-Quantum Migration of UAV Command-and-Control Links:
Identity, Not Computation, Is the Binding Constraint"*, while the manuscript is
titled *"Where the Bytes Go: Certificate Chains, Not Key Encapsulation,
Dominate Post-Quantum Handshake Cost on Unmanned Aircraft Command-and-Control
Links"*. The former never appeared in any version of this file, so it is likely
a working title or a paraphrase. Flagging it so the record is unambiguous; no
change made.

---

## m1 — the Gilbert–Elliott assumptions are now named

**Accepted.** The count of episodes depends on two assumptions that were
implicit. The text now says so, at the formula rather than in a footnote:

> Two assumptions sit in that count and are worth naming: $L$ is a length in
> segments, and it is the *total* loss in the bad state that makes the count
> exactly $np/L$ — a bad state dropping only a fraction $p_{\mathrm{bad}}$ of
> its segments would multiply the count by $1/p_{\mathrm{bad}}$, so $1/L$ is
> the optimistic end of the family rather than a general scaling law.

The reviewer's correction is right and worth stating plainly: with a partial
bad state the episode count is $np/(L\,p_{\mathrm{bad}})$, so correlation still
reduces the mean penalty relative to the independent model, but by less than
$1/L$. The bound survives; its label is now accurate.

## m2 — the "4×" compared two different statistics, and now gives both

**Accepted, and this was the weakest sentence in the revision.** The old text
put a 20 % difference between two *configurations* beside a 4.6 % coefficient
of variation belonging to a *third* configuration (the classical baseline).
Both are relative quantities, which is what makes the comparison possible at
all, but they are not the same statistic and the pairing was convenient rather
than principled.

Now stated with the basis explicit:

- the 20 % is **125 times** the pooled coefficient of the two configurations
  being compared — ML-DSA-65 and ML-DSA-44, pooled CV 0.16 %;
- and **4.3 times** the worst coefficient in the batch, 4.6 %, which belongs to
  the classical baseline rather than to either of them;
- with one sentence saying both are relative and that they are different
  statistics, which is why both are given.

The same correction is applied in the threats section, so the two places no
longer disagree.

## m3 — Table 8 says the range is used *instead of* an SD

**Accepted.** The note now ends: "a standard deviation from two runs would
carry no information, so the range is quoted in its place." No inference left
for the reader.

## m4 — the conclusion names the stack

**Accepted.** The conclusion now reads "OpenSSL 3.5.7 — a property of this
stack, not of the protocol — issues no ticket", matching the "One stack, one
version" paragraph in §5.6.

## m5 — table consistency, and one real asymmetry in Table 6

Two things here, one of which was a genuine fault rather than a missing note.

**(a) Table 10's baseline.** The note now names the batch: the classical
baseline is the 1,915-byte, 1.99 s measurement from the same batch as
Table 5. A clause at the point of citation in the body says the same thing, so
a reader who arrives at the table through the prose does not have to reach the
figure's caption to learn why 5.66× and 5.70× differ.

**(b) Table 6 did have an asymmetry.** The client direction carried a separate
`framing` row (53 B) while the server direction folded its framing into a
combined `Finished and framing` row (262 B). That is exactly the shape a reader
could mistake for a mis-merged cell, and it was inconsistent besides. The
server direction is now split the same way as the client one:

| Direction | Row | Bytes |
|---|---|---|
| server→client | `Finished` | 74 |
| server→client | *framing* | 188 (CCS 6 + tickets 158 + close 24) |

`\multirow` was 6 and is now 7. Both directions sum to their measured totals,
10,372 and 10,468, which add to the 20,840 of Table 5. The framing rows are set
in italics and the caption says in as many words that italic rows are not
messages but collections of records carrying no handshake content.

**Caveat on verification.** I checked this structurally and numerically — row
count against `\multirow`, both column sums, no overfull box, no float
rejection — but I could **not** rasterise the page on this machine: there is no
PDF renderer installed, and the Windows WinRT route needs a runtime-compiled
assembly that the sandbox blocks. So the layout has not been looked at by eye.
Table 6 is on page 13; please confirm it in the proof, as the reviewer asked.

## m6 — 12–13 % everywhere

**Accepted.** The design rule said 12.6 %, the abstract 12–13 %, and §4.8 gave
the range 11–13 % with the point value inside it. The design rule now reads
12–13 %.

## m7 — the figure's baseline is named in the body too

**Accepted.** Added at the Table 10 citation, above.

## m8 — the Internet-Draft is labelled where it is used

**Accepted.** First use in §2.3 now reads "The IETF Merkle Tree Certificate
draft — an Internet-Draft, not yet a standard — counts…". The vendor-announcement
entry already carried its marking from the previous revision.

---

## Also done

The reviewer suggested the repository record the DTLS gap. `README.md` now opens
with it:

> Known gap: every measurement is TLS over TCP. A DTLS 1.3 measurement is
> future work — this stack has no post-quantum DTLS to measure, so the paper
> carries an RFC 9147 bound instead (`harness/dtls_bound.py`).

## State

33 pages (Table 6 gained a row), 14 tables, 7 figures, 200-word abstract,
33 references, 41/41 cross-references, 0 overfull, 0 errors, 0 undefined.
Pushed to `main`; the PDF and all CSVs are in the repository.

Still outstanding, and only the authors can supply it: the author block.
28 `<<...>>` placeholders — names, affiliation, e-mails, CRediT roles, funding.
