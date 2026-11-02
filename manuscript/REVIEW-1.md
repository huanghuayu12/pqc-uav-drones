# Referee Report — "Where the Bytes Go: Certificate Chains, Not Key Encapsulation, Dominate Post-Quantum Handshake Cost on Unmanned Aircraft Command-and-Control Links"

**Target:** MDPI *Drones*
**Manuscript:** main.tex, 29 pp., 14 tables, 7 figures, 33 references
**Recommendation:** **Major revision** (the measurement work is sound and the artefact
narrative is unusually honest; the paper is currently framed as a discovery when it is a
quantification, and three scope restrictions are asserted away rather than measured)

---

## 提出给作者的摘要（中文）

1. **核心问题不是数据，是定位。** 7.2:1 这个比例用 FIPS 204 的尺寸表加一分钟算术就能得到，
   审稿人一定会问"为什么要实测"。论文必须把主张从"我们发现了比例"改成"我们证明线上的字节
   与标准算术逐字节相符，并把它换算成时间、换算成补救方案的排序"。
2. **TCP 而非 DTLS 是最大的软肋。** 现在用"我们的 OpenSSL 编不出 DTLS"来解释，等于承认这是
   工具缺口而非设计选择。至少要给一个 DTLS 的实测字节数，或按 RFC 9147 给出分片开销的定量上界。
3. **只测了 GEO（250 ms）。** 9.6 kbps/250 ms 是 DO-362 的一个剖面，但 LEO 的 20–60 ms 完全没测，
   而结论"迁移在带宽最紧的链路上代价最大"恰恰在 LEO 上要重新检验。
4. **建议方案（PSK）的代价只算了一半。** 论文给证书定了价，却没给证书的吊销通道（CRL/OCSP）
   定价；而 PSK 的轮换与撤销是全网运营问题，只在结论里提了一句。
5. 细节层面已发现并指出若干可验算的不一致（单次运行、丢包段数、恢复会话的泛化），
   这些不致命，但都是审稿人会当场按计算器核对的地方。

---

## Summary of the submission

The authors measure a mutual-authentication TLS 1.3 handshake carrying ML-KEM-768 and
ML-DSA-65 certificates over an emulated 9.6 kbps / 250 ms link, attribute every byte with a
record-layer parser, and convert bytes to completion time using a measured slope. They then
price three remedies — a smaller signature scheme, a shorter chain, and no certificates at
all — and find the third dominates. A section catalogues five measurement pitfalls, one of
which inflated a headline number by 54.7 %.

The empirical core is credible and, in places, better than the norm for this literature: the
byte attribution reconciles to the byte against FIPS 203/204 and X.509 framing, the chain-depth
figure of 11,248 bytes resolves exactly, and the report of a self-caught artefact that pushed
in the authors' own hypothesised direction is the kind of disclosure that raises rather than
lowers confidence. The weaknesses are not in the execution but in the framing and in three
scope restrictions that are argued rather than measured.

---

## Major concerns

### M1. The headline result is arithmetic, and the paper does not confront that

The abstract's first claim is that identity material dominates "not the ratio size tables
suggest". But the size tables *do* suggest it: two ML-DSA-65 certificates at 5,514 B plus two
3,309 B signatures is 17,646 B against 2,272 B of ML-KEM public key and ciphertext, i.e. 7.8:1
before any measurement is done. A referee will do this division in thirty seconds and conclude
that the paper's central finding required no testbed.

This is unfair to the paper, because what it actually contributes is different and more
valuable — (i) the on-the-wire byte counts match the arithmetic exactly, including the 35 bytes
of TLS framing around the DER and the 253-byte X.509 frame, which is a non-trivial check that
most published PQC byte counts fail; (ii) the conversion of bytes into *time* on a constrained
link, with a measured slope rather than an assumed rate; (iii) the ranking of remedies, which
is not derivable from size tables at all; and (iv) the rate-dependence result, which overturns
the natural assumption that the penalty is a constant. But the manuscript does not say this
plainly enough, and the abstract's phrasing invites the criticism.

**Required:** rewrite the abstract's opening claim and the Introduction paragraph beginning
"It is tempting to conclude that the key exchange dominates" so that the paper concedes the
arithmetic up front and claims the measurement, the time conversion and the ranking. State the
naive ratio the paper is arguing against, with its value.

**Also required:** engage with the TLS-level measurement literature, which is cited nowhere.
At minimum Sikeridis et al. (NDSS 2020, post-quantum authentication in TLS 1.3), Paquin,
Stebila and Tamvada (PQCrypto 2020, benchmarking PQC in TLS), and Schwabe, Stebila and Wiggers
(USENIX Security 2021, post-quantum TLS without handshake signatures — which is precisely the
pre-shared-key argument the paper makes for UAVs). The last is the most important: it makes
the "remove the signature rather than shrink it" case for the web, so the paper's PSK
recommendation is not a new idea but a new *price* for a known idea on a specific link. That
distinction should be stated, not left for the reader.

### M2. TCP instead of DTLS is argued away, not measured

Section 3.4 concedes that all measurements are TLS over TCP while UAV C2 links carry DTLS over
UDP, and gives two reasons: the local OpenSSL build could not complete a DTLS handshake against
the proxy, and TCP is "the more forgiving transport". The second is an assertion; the first
reads as an engineering gap, because a UDP relay is a small amount of code.

This is the first question any referee in this area will ask, and the current answer concedes
the point and then reasons past it. Two remedies, in order of preference:

1. Capture one DTLS 1.3 handshake's byte counts (no link emulation needed — a loopback capture
   suffices) and report the fragmentation overhead of a 5,549-byte `Certificate` across
   1,200-byte datagrams. Even a single number, e.g. "the same handshake costs N bytes over
   DTLS against 20,840 over TCP", converts an assertion into a measurement.
2. If that is impossible, compute the bound explicitly from RFC 9147: per-datagram record
   headers plus epoch/sequence fields for a handshake of this size, and state the resulting
   percentage. The paper already contains all the inputs.

The claim that the *attribution* survives the transport change is correct and should be kept;
it is the claim that the *cost* is bounded below by the TCP numbers that needs support.

### M3. Only one propagation-delay regime is measured

Section 2.2 correctly identifies two UAV link profiles, LOS (milliseconds) and BLOS GEO
(250 ms one-way, DO-362). Only the second is measured. The rate sweep varies bandwidth from
2.4 to 38.4 kbps at fixed 250 ms, so the paper can say how the penalty behaves with rate but
not with delay — and its own conclusion, that migration "costs most on exactly the links that
have the least bandwidth to spare", is a joint statement about rate and delay that the data
only half supports. A LEO BLOS profile (20–60 ms one-way, 100–500 kbps) is the third regime
that matters operationally, and it is one configuration × three handshakes.

**Required:** add a delay sweep at fixed rate, or at minimum one LEO point. If neither is
possible, the conclusions must be restricted to the GEO regime explicitly, in the abstract as
well as in Section 5.

### M4. The recommended remedy is priced but its operational cost is not

The paper's recommendation is to pre-provision a PSK and drop certificates. It prices the
certificate exchange thoroughly and the PSK rotation not at all. Two asymmetries deserve a
paragraph each, because a referee will raise them:

- **Revocation.** A certificate can be revoked through a channel the peer checks; a PSK can
  only be replaced. The paper costs the certificate but not its revocation channel, even
  though CRL/OCSP responses on a 9.6 kbps link are themselves hundreds to thousands of bytes.
  If revocation is out of scope, say so and say why the comparison is still fair.
- **Forward secrecy.** Section 4.6 states the handshake uses `psk_dhe_ke` and I have verified
  the byte evidence supports it (ClientHello +50 B for the extension, server still returns a
  1,088-byte ciphertext). That should be stated with the evidence, because the paper's own
  motivation is harvest-now-decrypt-later and a reader will otherwise assume the recommendation
  removes the ephemeral exchange that defends against it.

### M5. Single-run measurements in the table that carries the central time claim

Table 7 (certificate parameter sweep) is single-run; the repeatability evidence comes from
five runs at three configurations elsewhere. The quoted coefficients of variation (0.10 %,
0.41 %, 0.67 %) do bound the risk, and the argument that the smallest effect resolved is thirty
times the largest CV is sound. But the remedy is cheap — four rows × five runs — and the
difference between "bounded by an argument" and "reported with an interval" is exactly the
difference between a major and a minor revision on this point.

**Required:** n = 5 on Table 7 with mean ± sd, or a clear statement in the caption that the
column is single-run and why the CV bound suffices.

### M6. The loss model is tested only where real links do not operate

Loss is swept at 10 % and 20 % per segment, which is one to two orders of magnitude above a
well-engineered BLOS link. At those rates the interesting regime is not the mean shift but the
tail: at 20 % over sixteen segments, the probability of a handshake that exhausts its
retransmission budget is not negligible, and the paper reports means only. A sweep at 0.1 %,
0.5 % and 1 % would (a) sit where real links are, (b) show whether the 0.446 s-per-loss slope
holds when losses are rare, and (c) let the tail be reported.

Related: the 1,200 ms RTO is shorter than what RFC 6298 would compute for a 500 ms RTT link.
State the basis for the value and the sensitivity of the result to it.

### M7. Resumption: a stack behaviour generalised into a protocol property

Section 3.4's body text is properly scoped to OpenSSL 3.5.7's `s_server`, and the conclusions
repeat the scoping. But the Introduction's contribution bullet and the phrase "a stack that
must authenticate both directions by certificate cannot get there by resuming" read as a
statement about TLS 1.3 rather than about one server implementation. RFC 8446 does not forbid
issuing tickets after client authentication, and a server may bind the authenticated client
identity to the ticket; other stacks do so. (I have softened the two offending sentences in the
enclosed revision, but the referee's point stands for the submitted version.)

**Required:** in every place where the unavailability of resumption under mutual authentication
is stated, attribute it to the stack, and add one sentence saying that whether other stacks
behave differently is untested here.

### M8. Reproducibility artefacts are incomplete, and one byte count is not pinned

The data-availability statement points to a repository URL that is still a placeholder, and
there is no DOI. MDPI will not send this to production in that state.

Separately, the test certificates are regenerated per run with `openssl req -x509`, which
assigns a random serial number. A serial whose leading byte is zero encodes one byte shorter,
which would move the DER length from 5,514 and break the paper's "resolves to the byte" claim
for anyone reproducing it. I confirmed the DER is 5,514 over repeated generation on this
machine, but pinning the serial (`-set_serial`) would remove the residual risk and cost one
line of harness code. The same applies to the reported total: I reproduced 20,840 exactly over
four runs, so the number is right; it should simply be made unconditionally right.

---

## Minor concerns

1. **Identity is defined by subtraction.** Table 4's identity column is the total minus the two
   hello payloads, so it silently includes the 10 bytes of hello record headers and the 23-byte
   application-probe record. The caption says "everything else … and record and message
   framing", which is honest, but a reader recomputing 2 × (5,514 + 3,309) = 17,646 will get
   96.4 % of 18,310 and wonder about the missing 664. One clause giving that decomposition
   would close it. (I have added the probe-record disclosure to Section 3.2 and to the
   Table 6 caption in the enclosed revision.)

2. **Cipher suite is never stated.** The byte accounting depends on a 16-byte AEAD tag and a
   48-byte Finished, i.e. TLS_AES_256_GCM_SHA384. It should be named once, in the testbed
   description, because a reader who assumes AES-128-GCM-SHA256 will get a 32-byte Finished and
   fail to reconcile the table. (Named in the testbed description of the enclosed
   revision.)

3. **"1,915" versus "1,914".** The classical baseline appears as both. Section 4.1 explains the
   batch-to-batch variation (1,912/1,914/1,915/1,916), which is good practice, but the abstract-
   adjacent tables should carry one value with a footnote rather than two values in two tables.

4. **The abstract's "not the ratio size tables suggest" is unsupported** unless the naive ratio
   is stated. See M1.

5. **Hybrid groups.** Real deployments negotiate X25519MLKEM768, not pure ML-KEM-768. The
   difference is 32 bytes and does not move any conclusion, but one sentence saying so prevents
   a referee from suspecting the configuration was chosen to flatter the key-exchange term.

6. **MAVLink appears in the keywords and in Section 2.2 but is never analysed.** The paper does
   not say how TLS or DTLS would be carried over a MAVLink link, nor how MAVLink 2 signing
   interacts with certificate identity. Either develop this in two paragraphs — the 255-byte
   payload limit and the framing overhead are already discussed, so the material is there — or
   drop the keyword. (Resolved the other way in the enclosed revision: the 255-byte payload
   limit was already there, and two paragraphs now add the MAVLink~2 signing argument.)

7. **Section 3.3 (five pitfalls) would be stronger as a table** with columns for what was wrong,
   what it inflated the number to, and what the corrected value is. As prose it reads as
   confession; as a table it reads as method. Also add one sentence stating that no number
   reported in Sections 4–5 predates these fixes. (Table 2 of the enclosed revision.)

8. **Figure legibility.** The line plots distinguish series by marker as well as colour and are
   greyscale-safe; the stacked bars of Figure 1 are not, and should carry hatching on the
   identity segment. Check also that the figure fonts match the body text at final size.

9. **Figure 7(b) annotates 5.70× at 9.6 kbps while Table 10 gives 5.66× and the abstract quotes
   5.66×.** Both are correct within their own batch — the rate sweep's 9.6 kbps cell is
   11.267 / 1.977 = 5.70 and the pre-shared-key table is 11.29 / 1.99 = 5.66 — but a reader
   comparing the two will not know that, and the batch rule currently lives in the body text.
   One clause in the Figure 7 caption would prevent a needless objection. (Added in the
   enclosed revision.)

10. **Internet-Drafts are cited alongside standards** (Merkle Tree Certificates, Let's Encrypt's
    announcement). This is fine and even valuable for currency, but the bibliography should mark
    draft status in the entry itself so a reader does not mistake it for a published standard.
    (Both marked in the enclosed revision: the Merkle Tree Certificate entry carries its
    `draft-ietf-plants-...` identifier, the Let's Encrypt entry is marked as a technical
    announcement rather than a peer-reviewed source.)

11. **The claim "optimising the smaller term cannot fix the larger one"** would be stronger with
    the number: shrinking the key exchange from 2,530 to its floor changes the total by at most
    1.2 %, against 87.9 % sitting in identity. (Adopted, but with the arithmetic corrected:/n   the key exchange is 12.1 % of the total, not 1.2 %; 2,530 / 20,840 = 0.121. The revision
   states the corrected figure.)

---

## What would make this acceptable

The empirical contribution is already sufficient for *Drones*. What is needed is a
repositioning and three additions:

1. Reframe the contribution from discovery to quantification, and cite the TLS-level
   measurement literature (M1).
2. One measured DTLS data point, or a computed RFC 9147 bound (M2).
3. One additional delay regime, or an explicit restriction of the conclusions to GEO (M3).
4. A paragraph on revocation and forward secrecy in the PSK recommendation (M4).
5. Resolve the repository and DOI placeholders; pin the certificate serial (M8).

Items M5–M7 are desirable rather than essential; the minor points are editorial.

I would be glad to review a revision. The measurement discipline in this manuscript is better
than most, and the pitfalls section is the part I would most like to see kept and strengthened.

---

## 附：补丁记录（本轮已直接改入 main.tex 的项）

| 位置 | 原问题 | 处理 |
|---|---|---|
| Table 6 `Certificate` 行 | "DER 5,500 … frame 239"，与线上 5,549 差 49 B 无法对账 | 改为 DER 5,514 + 35 B TLS 帧；脚注给出 5,514 = 1,952 + 3,309 + 253 |
| Table 6 `CertificateVerify` 行 | "signature 3,314"，实际 3,309 + 30 B 帧 | 改为 3,309 + 30 |
| Table 6 framing 行 | 53 B 未说明含 23 B 应用探针记录 | 标注 CCS 6 + probe 23 + close 24 |
| §3.2 | "the byte counts are the handshake plus two bytes"（错：是 1 B 载荷占 23 B 记录，且服务器不回显） | 重写为准确描述 |
| §4.7 | "spans fourteen [segments] … suffers 3.4"，14×0.2=2.8 与 3.4 不符 | 实测代理计费 16 段（每向 8），改为 "sixteen … against the 3.2 that 16×0.2 predicts" |
| §5.2 | "structural rather than a defect"，把 OpenSSL 行为说成协议性质 | 改为 stack-scoped，补 RFC 8446 允许绑定身份的说明 |
| Intro 贡献第 4 条 | "is unavailable at all when mutual authentication is required" 泛化 | 限定到 OpenSSL 3.5.7 |
| §4.6 | psk_dhe_ke 只有断言 | 补字节证据（ClientHello +50 B，服务器仍回 1,088 B 密文） |
| §3.1 testbed | 未说明密码套件 | 补 TLS_AES_256_GCM_SHA384，并说明它决定 16 B tag 与 48 B Finished |
| §3.1 testbed | 未提混合组 | 补一句：X25519MLKEM768 只多 32 B，不改结论 |
| Table 4 说明 | identity 是残差，未说明含 33 B 帧与探针 | 补 17,646 / 18,310 的分解 |
| Fig. 7 说明 | 图上 5.70× 与 Table 10 的 5.66× 看似矛盾 | 注明两个批次，差 0.7 % 与 1.8 % |
| harness 文档串 | 同 §3.2 的错误描述 | 同步修正 |

---

## 附二：第二轮修订（针对本报告 M1–M3、M8 的回应）

| 意见 | 处理 | 证据 |
|---|---|---|
| M1 定位（"发现"→"量化"） | 摘要与引言重写：明说身份材料占优"从 FIPS 203/204 的尺寸就能预测"，论文主张改为线上与算术逐字节相符、换算成秒、补救排序。新增 Sikeridis NDSS'20 / CoNEXT'20、Paquin PQCrypto'20、Schwabe–Stebila–Wiggers CCS'20 四条 TLS 层测量文献，PSK 论证回到原始出处 | `references.bib` 33 条；§1、§2.3 |
| M2 DTLS 只能界不能测 | 先测清楚"这个栈上不存在后量子 DTLS"：`-dtls1_2` 持 ML-DSA-65 证书一律 `no shared cipher`（1.2 的套件名编码认证算法），`-groups MLKEM768 -dtls1_2` 同样失败（ML-KEM 不是 1.2 的组），DTLS 1.3 在 OpenSSL 3.5.7 未实现。既不可测，就按 RFC 9147 算上界：13 B 记录头 + 12 B 握手头 + 16 B tag = 42 B/数据报，1,200 B 分片下 20,817 → 21,659（+842 B，+4.0 %）；证书与签名记录 +3.2 %，份额 85.4 % → 84.7 %，只缩放不重排 | `harness/dtls_bound.py`；§3.4 |
| M3 只测 GEO | 新增延迟扫描：0 / 40（LEO）/ 250（GEO）/ 600 ms（GEO 双跳），3 次/格。结果双向：时间对延迟严格线性（残差 ≤14 ms），证书配置斜率 4.00 s/s 是经典的 2.03 的两倍，**绝对差从 8.80 增至 9.99 s**；但比值从 7.00× 降到 4.72×，因为延迟是加性项，分母小的被稀释得更快。结论：GEO 的 5.66× 是中间值，LEO 应为 6.71×——论文一直报的是偏保守的一端 | `results/delay_sweep.csv`；Table 9、§4.5 |
| M8 序列号未固定 | `make_certs` 现在用固定 20 字节序列号（首字节 0x7f，保证 DER INTEGER 不补零），ML-DSA 证书 DER 恒为 5,514，四个批次字节数完全一致 | `harness/link_measure.py` `FIXED_SERIAL` |
| 次要：Table 7 只有单次运行 | 补五次重复（`sweep_repeat.py`）：sd = 0.024 / 0.018 / 0.012 / 0.013 s，CV 0.62 / 0.20 / 0.10 / 0.09 %，经典行最不稳（ECDSA 签名变长），已在表内与正文如实说明 | `results/sweep_repeat.csv`；Table 7 |
| 次要：10 %/20 % 丢包不现实 | 补 0.1 / 0.5 / 1 % 低丢包批（`loss_low.py`，5 次/格）：证书配置位移 −0.009 / −0.002 / −0.005 s（方向都不确定），九个格子的位移跨 −0.009 至 +0.013 s，而同格 sd 为 0.008–0.019 s，即在噪声内；论文自身的斜率预测 1 % 时 0.07 s，未被 0.005 s 推翻。明确写成"表里那几行是上界工况"，并说明该批只能否证自己的模型，不能证明真实链路无损 | `results/loss_low.csv`；§4.7 |
| 次要：灰度可读性 | 堆叠柱与分组柱的第二段加斜纹（hatch），不只靠颜色区分；重新生成 m1、m5 | `sim/plot_measured.py` |

仍未解决、且只能由作者提供：正文 17 处 `<<...>>` 占位（作者块 9、仓库 URL 8）与 Zenodo DOI。
