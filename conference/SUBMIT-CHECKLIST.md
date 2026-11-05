# AHPCAI 2026 投稿清单（短文版）

论文（投稿用）：**`conference/AHPCAI2026_Huang.docx`** 与 **`conference/AHPCAI2026_Huang.pdf`**
（6 页，直接用会议下发的官方 SPIE A4 Word 模板排版，Word 导出 PDF）。

- 纸型 A4，页边距左右 1.93 cm / 上 2.54 / 下 4.95 cm，正文 10pt Times 单栏 —— 全部继承自官方模板样式。
- 正文源仍是 `conference/main.tex`（内容唯一来源）；`build_docx.py` 把它自动排进 Word 模板。
  改文字请改 main.tex 后重跑 `python build_docx.py`，再用 Word 另存 PDF。
- LaTeX 版（`main.pdf`，spie.cls Letter 版）保留作备份，投稿以 Word 版为准。

## 论文信息

- **标题**：Five ways to mismeasure a post-quantum TLS 1.3 handshake on a narrowband link
- **参考文献 28 条**（含 SLH-DSA/FIPS 205、DO-362、MAVLink、DTLS 1.3/1.2、
  RFC 6928、liboqs、CoNEXT/KEMTLS 等扩展），正文全部有引用点。
- **定位**：测量方法论短文（五个测量陷阱 + 检测协议）。**与 MDPI Drones 期刊版是两篇不同贡献**：
  期刊版讲迁移成本结论，本短文只讲"测量本身怎么被做错、怎么查出来"，重叠内容
  约为期刊版 §3.2–3.3 的一部分。期刊版投稿时须引用本会议版（若录用）。
- **作者与单位**（均署 1,2）：
  1. Xiaoyu Huang（黄晓宇）— 19591587786@163.com（通讯，带 `*`）
  2. Yiliang Han（韩益亮）
  3. Shuaishuai Zhu（朱率率）
  4. Hui Wu（吴悔）
  5. Zhongqiang Liu（刘忠强）
  - 1 Engineering University of PAP, Xi'an, 710086, Shaanxi, China
  - 2 Key Lab of the Armed Police Force for Network and Information Security, Xi'an, 710086, Shaanxi, China

## 会议关键信息

- 截稿：**2026-11-06 23:59**
- 会议：2026-11-20～22，河南大学（郑州龙子湖校区）
- 出版：SPIE 论文集（ISSN 0277-786X），主办方称 EI Compendex + Scopus
- 费用：常规 3,800 元/篇（单栏 4–6 页；本稿 6 页，无超页费）
- 投稿入口：艾思科蓝（ais.cn/attendees/index/7VRZVM）
- 会议秘书：翟老师 17512806705（微信同步），备注 "AHPCAI 咨询"

## 你还需要做的（机器做不了的部分）

1. 在艾思科蓝注册并提交 `AHPCAI2026_Huang.docx`（或其 PDF）；备好 `main.tex` 等源文件以防组委会要源码。
2. **投稿后须主动加会议秘书微信**，跟进审稿状态（会议明文要求）。
3. 查重：会议建议 iThenticate 自费查重；可在校内图书馆或审稿前自测。
4. 录用后缴费、注册（注册费含一位作者参会名额；线上/线下双会场）。
5. 学生价（3,600）需向秘书处提供学生证明，且优惠不可叠加，投稿前先问。
6. 口头报告 10 分钟（可选）；不参会则论文一般不予出版（SPIE 政策），务必确认出席形式。

## 数据与复现

- 所有数字来自仓库 `results/*.csv`，由 `harness/link_measure.py`、
  `harness/record_breakdown.py`、`harness/session_ticket_probe.py` 产出；
  Figure 1 复用 `manuscript/m5_artefact.pdf`。
- Word 版构建：`cd conference && python build_docx.py`，再用 Word 打开
  `AHPCAI2026_Huang.docx` 导出 PDF（本机已验证 6 页）。
- LaTeX 备份版：`pdflatex main && bibtex main && pdflatex main && pdflatex main`
  → 6 页、0 overfull、0 未定义引用。
- SPIE AI 政策：致谢中已声明测量程序开发使用了 AI 编码工具、结果由作者复核。

## 与期刊稿的关系（重要，勿删）

- 本短文**先投先发**。MDPI Drones 版在 cover letter 中应说明本会议版的存在，
  并在文中引用；重叠仅限测量环境描述与五个陷阱的事实，期刊版新增了全部
  sweep、PSK、链深、resumption 与 remedy 排序。
