# Response to Reviewer

**Manuscript:** *Post-Quantum Migration of UAV C2 Links Is an Identity Problem, Not an Algorithm Problem*
**Journal:** *Drones* (MDPI)
**Decision addressed:** Minor–Major Revision

We thank the reviewer for a careful and unusually well-targeted report. The
criticism that mattered most was M1: the paper's opening premise was cited
rather than measured, and the reviewer was right that this put the argument's
first step outside its own evidence. We have measured it. Doing so produced a
margin large enough to make the premise checkable rather than assumed, and it
also produced a result we did not expect (M4, below).

Two of the reviewer's observations did not reproduce against the submitted
files. We say so explicitly in §3 rather than quietly ignoring them, because a
reviewer who checks will find the same thing.

Numbers below are from the revised manuscript, which is 30 pages, 14 tables,
7 figures, 33 references, with 198 words of abstract.

---

## 1. Major concerns

### M1 — "Computation is not the bottleneck" rested on citations

**Accepted, and measured.** The reviewer is correct that Section 5.6's
"cited, not measured" was an admission placed at the wrong end of the
argument. The premise now carries its own measurement.

A mutual-authentication ML-DSA-65 handshake performs two signatures, two
verifications and one ML-KEM-768 exchange. Timed with `openssl speed` on the
test host (`harness/compute_cost.py`), these total **1.78 ms**, against
**11.27 s** of transmission: **0.016 %**, a margin of **6,300×**. The heaviest
scheme measured, ML-DSA-87, is 1.92 ms.

| Configuration | Sign | Verify | Total | Share of 11.27 s | Margin |
|---|---|---|---|---|---|
| ML-DSA-44 | 0.39 ms | 0.09 ms | 1.05 ms | 0.009 % | 10,764× |
| ML-DSA-65 | 0.71 ms | 0.13 ms | 1.78 ms | 0.016 % | 6,321× |
| ML-DSA-87 | 0.73 ms | 0.18 ms | 1.92 ms | 0.017 % | 5,873× |
| ECDSA-P256 | 0.50 ms | 0.40 ms | 1.80 ms | 0.016 % | 6,261× |
| ML-KEM-768 + PSK | — | — | 0.095 ms | 0.003 % | 34,947× (vs 3.32 s) |

The revised text states the falsification condition rather than the
conclusion: computation would have to be **6,000× slower** than a desktop
core before it matched transmission on this link. At a thousand times slower
the arithmetic is still under a fifth of the handshake. A device slow enough
to break the premise could not complete a TLS handshake at all.

The manuscript quotes two significant digits — 1.8 ms, a margin of some
6,000× — because repeat runs on the same host differ by about 10 % (1.78 to
1.93 ms). The table above is the first measurement, not a more precise
quantity than the text claims.

**What we did not do.** We did not measure a Cortex-M4. The reviewer asked for
"at least one representative hardware" point; we have given a margin instead,
because a margin is the quantity the argument needs and a single MCU number
would answer a narrower question. If the editor prefers the latter, it is a
one-day addition, but we would argue the margin is the stronger evidence: it
holds for any part within three orders of magnitude of the host.

Locations: §1 (premise now states the margin), §3.4 (measurement and
falsification condition), §5.6 (rewritten from "cited" to "measured on the
host, not on a flight controller").

### M2 — Transport choice, and whether the remedy ordering survives DTLS

**Accepted in part: the direction is now quantified, the experiment is still
absent.** We cannot measure DTLS on this stack — that is not a tooling
preference but a finding, reported in §3.4: OpenSSL 3.5.7 offers DTLS 1.0 and
1.2 only, and a DTLS 1.2 handshake with either an ML-DSA certificate or
`-groups MLKEM768` fails with `no shared cipher`, because DTLS 1.2 encodes the
authentication algorithm in the cipher-suite name and has no ML-KEM group.
PQC DTLS does not exist here to be measured.

What we have added is the reviewer's own suggestion — a directional argument
about *ordering*, not just framing:

> The flight carrying identity material is about 10,400 bytes, nine datagrams
> at 1,200 bytes, whereas the pre-shared-key handshake completes in one or two
> datagrams per flight. A DTLS peer that loses a datagram retransmits the whole
> flight, so at equal loss probability the certificate handshake pays several
> times the retransmission the pre-shared-key one does. Section 4.7 measures
> 0.446 s per injected loss on TCP; on DTLS it would grow faster while the
> pre-shared-key penalty barely moved.

The sign of the error is therefore known: the ordering in the paper is the
**conservative** one for the transport UAV links actually use. The same
argument now covers bursty fades, which the reviewer raised separately (minor
6).

**On the reviewer's second point** — that the emulator may not reproduce TCP
congestion control, slow start or Nagle — this is correct and is the residual
gap. The proxy serialises at the token-bucket rate and validates that to
+0.3 %, but it does not model cwnd growth. We have not added a claim that it
does. Since the paper's claims are byte attribution and remedy ordering, and
both are transport-independent, we have left this as a stated limitation
rather than papering over it.

### M3 — PSK operability, and forward secrecy

**Forward secrecy: already established in the text, now also in the table.**
The reviewer asked whether the ML-KEM-768 + PSK configuration performs an
ephemeral exchange and whether the 2,902 bytes contain the KEM ciphertext.
They do, and §4.6 says so with byte evidence: the `ClientHello` grows by
exactly 50 bytes (the `pre_shared_key` extension) while the server still
returns a 1,088-byte ML-KEM ciphertext, which is `psk_dhe_ke` and not pure
PSK. A reader consulting only Table 10 could not see this, which was a real
presentation fault. The caption now decomposes the row:

> 2,902 bytes = 330 (hello, common to all configurations) + 56 (pre-shared-key
> extension) + 2,200 (ML-KEM-768 exchange), so the 1,088-byte ciphertext is
> still on the wire. That is what preserves forward secrecy, and it is why the
> saving is 3.4× rather than the 30× that also dropping the post-quantum
> exchange would give.

**Break-even: added, and it does not flatter the recommendation.** §5.4 now
carries the arithmetic the reviewer asked for:

> A pre-shared key saves 7.97 s per handshake against the depth-one
> certificate path, 12.88 s with one intermediate. A small fleet — twenty
> aircraft flying twice a day, one handshake per sortie — completes 14,600
> handshakes a year and saves 32 hours of airtime, or 52 with an intermediate.
> Both are about one working week. So the trade does not turn on airtime: it
> turns on whether the operator already runs key distribution.

The threshold is stated as a prior decision rather than a fleet size: an
operator who signs MAVLink v2 frames already holds a shared secret at both
ends, so the marginal cost of extending that trust model to the handshake is a
configuration change; an operator flying one aircraft a few times a month will
never recover the cost of building it, and certificates remain right at any
handshake rate. We regard this as strengthening the paper's architectural
claim, not weakening the recommendation, but the reviewer should judge that.

### M4 — The 87.9 % needs its conditions, and server-only was missing

**Both accepted. The second produced a result that changed a design rule.**

*Conditions.* The abstract now reads "with mutual authentication and a
self-signed, depth-one chain", and the chain-depth result (one intermediate
costs 11,248 bytes on top) is the reason the paper calls 87.9 % a floor rather
than a typical value. This cost 13 words of abstract, which we bought back by
compressing three sentences elsewhere; the abstract is 198 words.

*Server-only authentication.* We measured it (`harness/oneway.py`,
`results/oneway.csv`, three runs per cell):

| Configuration | Mutual | Server-only | Change |
|---|---|---|---|
| X25519 + ECDSA-P256 | 1,913 B / 1.98 s | 1,281 B / 1.88 s | −33 % B, −0.10 s |
| ML-KEM-768 + ML-DSA-65 | 20,840 B / 11.28 s | 11,845 B / 11.18 s | **−43 % B, −0.9 % t** |

The bytes fall by nearly half and the time barely moves. Completion time is
set by the **longest flight in either direction**, not by the total: the
server's flight is 10,468 bytes with a client certificate on the wire and
10,361 without — the certificate the server sends does not shrink — so the
client's certificate rides in parallel with a wait that was going to happen
anyway.

We have made this a fifth design rule rather than a footnote, because it is
actionable and it contradicts the intuitive reading of the paper:

> Authenticate both directions, because it is free. Authenticating one
> direction only to save airtime buys 43 % of the bytes and 0.9 % of the time.

It also answers the reviewer's implicit worry about the mutual-auth assumption:
mutual authentication is the conservative configuration, so every number in
the paper is an upper bound on what a server-only design would pay.

The identity share does fall, to 78.6 %, because the 2,530 bytes of key
exchange are not halved with the certificates — a change in the denominator,
not in the remedy.

### M5 — FN-DSA extrapolation: range, and a corrected slope

**Accepted, and checking it turned up an error of ours.** The reviewer asked
for a confidence range and stronger visual separation.

- *The error.* The text said "at 2,200 B/s ... giving 7.88 s". 2,200 gives
  7.91 s; 7.88 s is the 2,183 B/s marginal between ML-DSA-87 and ML-DSA-65.
  The number was right and the stated basis was wrong. The text now names
  2,183 B/s.
- *The range.* Across the three measured marginals — 2,150, 2,183 and
  2,282 B/s — the same 7,396-byte reduction gives **7.83 to 8.03 s**, so the
  gain over ML-DSA-44 is **11–13 %**, not a point value.
- *A second error found while computing it.* The gain was quoted as 12.7 %;
  (9.02 − 7.88)/9.02 = 12.6 %. Corrected in all five places, including the
  abstract.
- *Visual separation.* The predicted bar is already hollow and hatched, and
  the figure carries the in-plot annotation "hatched / italic = predicted from
  measured slope, not measured" (Figure 7). We have additionally put the range
  in the caption, since a reader who skips the plot text still needs it.

---

## 2. Minor concerns

| # | Concern | Disposition |
|---|---|---|
| 1 | Abstract ~300 words, too many numbers | **Not reproducible; abstract was 194 words and is now 198.** MDPI's limit is 200 and the submission was within it. We still took the point about density: three numbers were dropped and the conditions for 87.9 % were added. |
| 2 | "1.67× the classical baseline" reads as "67 % faster" | **Accepted.** Now "1.67 times the classical time", with the direction unambiguous. |
| 3 | Table 4's PSK identity share (45.0 %, 10.9 %) unexplained | **Accepted, real fault.** The PSK rows have no certificate, so the residual is `Finished` and framing only. Caption now states that the 316 bytes is what a handshake costs *after* identity is removed, not an identity overhead, and that the shares are tabulated for completeness. |
| 4 | Relationship between 7.8:1 and 7.2:1 | **Accepted.** §4.1 now derives both: 7.8 uses standard object sizes (17,646 / 2,272), 7.2 uses the wire (18,310 / 2,530); framing raises both terms but the smaller one faster (11.4 % vs 3.8 %), so the wire ratio is the lower. |
| 5 | Figure 3(b) 64 kbps points still drawn | Caption already said "we do not extrapolate from that rate". The reviewer's suggestion is cosmetic and we have left the points visible; they are evidence that the slope degrades, which is the point of drawing them. |
| 6 | "Loss does not reorder" optimistic under bursty fading | **Accepted, and now stated with a sign.** See M2: bursty fades cost a large flight several whole retransmissions and a small one a single datagram, so the paper's ordering is conservative. |
| 7 | MORVS release notes and Let's Encrypt blog cited alongside scholarship | **Accepted.** §2.3 introduces them as "vendor documentation rather than peer-reviewed studies"; the Let's Encrypt bibliography entry is marked "Technical announcement, not peer reviewed"; the Merkle Tree Certificate entry carries its `draft-ietf-plants-...` identifier. |
| 8 | Pitfall (3): "more than half" needs the number | **Accepted.** Now "about 5 kB against a 1.9 kB handshake, 72 % of what was being counted". |
| 9 | LaTeX residue: "ibraries", "MLKEM", "1.1.1.1.1.1", "Losses' is" | **One of four was real.** The `Losses' is` in the Table 10 note used a single backtick and rendered as single quotes; fixed. The other three do not appear in the submitted PDF: `grep` for `1\.1\.1\.1` returns nothing, "libraries" is spelled correctly in both occurrences, and `MLKEM768` occurs once as the OpenSSL group name, where the hyphen would be wrong. |
| 10 | Table 9's 4.00 s/s slope is an emulator property | **Accepted.** The caption now says the slope is a property of how the emulator charges delay, and that only the ratio between slopes is read as a link property. |

---

## 3. Two observations that did not reproduce

We mention these only so the reviewer knows they were checked rather than
discounted.

1. **Abstract length.** The reviewer estimated "about 300 words". The submitted
   abstract is 194 words by whitespace count after macro expansion (`\mlkem{}`
   → "ML-KEM", and so on). The revision is 198. If the reviewer counted a
   different rendering, we would like to know, but we could not reproduce 300
   by any method we tried.

2. **"1.1.1.1.1.1.1.1.1.1.1" on page 17.** There is no such string in the
   document. `grep -n "1\.1\.1\.1" main.tex` returns nothing, and the PDF text
   layer contains no run of repeated `1.` either. It may be a rendering
   artefact on the reviewer's side, or a reference that resolved to `??` and
   was misread.

Neither affects the substance of the report, and both are recorded here rather
than argued.

---

## 4. Structural suggestions

| Suggestion | Response |
|---|---|
| Compress §5.2 and §5.4 by 30 %, move detail to an appendix | Partly. §5.4 gained the break-even paragraph the reviewer asked for in M3, so compressing it and expanding it were incompatible. §5.2 is unchanged. |
| Introduction: 3 contributions instead of 4 | Kept at 4. The fourth (resumption and PSK unavailability under mutual auth) is a measured result, not a promise, and removing it would hide a negative finding. |
| Merge Figure 2 with Table 4 | Kept separate. The figure shows the ratio collapsing as identity is removed; the table gives the numbers a reader can recompute. They are used differently in the text. |
| State the batch baseline in Table 10's caption | **Accepted.** Caption now says the classical baseline is 1.99 s from the same batch, and that Figure 4 quotes 5.70× from the rate sweep's own 1.98 s. |

---

## 5. One result we did not expect

The server-only measurement was run to answer M4. It produced a finding that
now appears as a design rule and, we think, is the most immediately useful
thing in the paper for a practitioner: **mutual authentication costs
essentially nothing on a narrowband link**, because the client's certificate
travels underneath the server's flight. A designer who authenticates one
direction to save airtime saves 43 % of the bytes and 0.9 % of the time.

We flag it here because it is a change in the paper's content, not just its
presentation, and the reviewer should see it as such.

---

## 中文要点（给作者的摘要，不随稿提交）

- **M1 已解决**：本机实测 ML-DSA-65 握手算术 1.78 ms vs 传输 11.27 s = 0.016%，
  余量 6,300×。改的是"论证起点"，不是补一句免责声明。没测飞控，给的是余量而非单点。
- **M2 部分解决**：DTLS 仍不可测（栈上没有），但补了方向性定量：证书 flight 约 9 个
  数据报 vs PSK 1–2 个，flight 重传下单次丢包代价差数倍 → 论文的排序在 DTLS 下更成立。
- **M3 解决**：前向保密本来就有字节证据，现在写进表注；盈亏平衡加了算术——小机队一年省
  32–52 小时空口，约一周，所以关键不是机队规模而是"是否已有密钥分发"。
- **M4 解决且反超预期**：补测单向认证，字节 −43% 但时间只 −0.9%。因为时间是按最长
  flight 算，客户端证书搭了顺风车。新增第五条设计规则"双向认证免费"。
- **M5 解决**：查这条时发现我们自己的两处错——"2,200 B/s 得 7.88 s"其实 2,200 得 7.91，
  7.88 对应 2,183；12.7% 应为 12.6%。都已改，并加了 7.83–8.03 s 的区间。
- **次要 10 条**：7 条接受并改，2 条证据不足（摘要 300 词不成立，实际 194；"1.1.1.1.1"
  串不存在），1 条部分接受。
- 当前：30 页、14 表、7 图、33 引用、摘要 198 词、0 overfull、0 error。
