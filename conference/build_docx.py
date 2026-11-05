"""Build the AHPCAI 2026 Word manuscript from main.tex into the official
SPIE A4 template (Template/文件2：ProcSPIETemplate_A4.docx).

The LaTeX file stays the single source of truth for the text and numbers;
this script only re-flows it into the conference's required template.
"""
import copy
import re
import docx
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

TEMPLATE = "_user_tmpl/template.docx"
OUT = "AHPCAI2026_Huang.docx"
FIG = "../manuscript/m5_artefact.png"

CITE = {"fips203": 1, "fips204": 2, "fips205": 3, "rfc9881": 4, "rfc9909": 5,
        "openssl35": 6, "shor1997": 7, "mosca2018": 8, "nistir8105": 9,
        "bernstein2017": 10, "pqcryptoBook": 11, "pqm4": 12, "botros2019": 13,
        "paquin2020": 14, "sikeridis2020ndss": 15, "xia2024ligkyx": 16,
        "hussien2026pqmavlink": 17, "zeng2016": 18, "do362": 19, "mavlink": 20,
        "measurepackage": 21, "rfc8446": 22, "liboqs": 23, "rfc9147": 24,
        "rfc6347": 25, "rfc6928": 26, "sikeridis2020conext": 27,
        "schwabe2020kemtls": 28}
REF = {"fig:artefact": "1", "tab:pitfalls": "1", "tab:messages": "2",
       "sec:intro": "1", "sec:testbed": "2", "sec:pitfalls": "3",
       "sec:protocol": "4", "sec:case": "5", "sec:related": "6",
       "sec:conclusion": "7"}

REFERENCES = [
 'National Institute of Standards and Technology, “FIPS 203: Module-lattice-based key-encapsulation mechanism standard,” tech. rep., U.S. Department of Commerce, 2024.',
 'National Institute of Standards and Technology, “FIPS 204: Module-lattice-based digital signature standard,” tech. rep., U.S. Department of Commerce, 2024.',
 'National Institute of Standards and Technology, “FIPS 205: Stateless hash-based digital signature standard,” tech. rep., U.S. Department of Commerce, 2024.',
 'J. Massimo, P. Kampanakis, and S. Salter, “Internet X.509 public key infrastructure: Algorithm identifiers for ML-DSA,” RFC 9881, 2025.',
 'J. Massimo, P. Kampanakis, and S. Salter, “Internet X.509 public key infrastructure: Algorithm identifiers for SLH-DSA,” RFC 9909, 2025.',
 'The OpenSSL Project, “OpenSSL 3.5: ML-KEM, ML-DSA and SLH-DSA support,” https://openssl-library.org/, 2025. Version 3.5.7 used for all measurements.',
 'P. W. Shor, “Polynomial-time algorithms for prime factorization and discrete logarithms on a quantum computer,” SIAM Journal on Computing 26(5), pp. 1484–1509, 1997.',
 'M. Mosca, “Cybersecurity in an era with quantum computers: Will we be ready?,” IEEE Security & Privacy 16(5), pp. 38–41, 2018.',
 'L. Chen, S. Jordan, Y.-K. Liu, D. Moody, R. Peralta, R. Perlner, and D. Smith-Tone, “Report on post-quantum cryptography,” Tech. Rep. NISTIR 8105, National Institute of Standards and Technology, 2016.',
 'D. J. Bernstein and T. Lange, “Post-quantum cryptography,” Nature 549(7675), pp. 188–194, 2017.',
 'D. J. Bernstein, J. Buchmann, and E. Dahmen, eds., Post-Quantum Cryptography, Springer, Berlin, Germany, 2009.',
 'M. J. Kannwischer, J. Rijneveld, P. Schwabe, and K. Stoffelen, “pqm4: Testing and benchmarking NIST PQC on ARM Cortex-M4,” in Proc. 2nd NIST PQC Standardization Conference, 2019.',
 'L. Botros, M. J. Kannwischer, and P. Schwabe, “Memory-efficient high-speed implementation of Kyber on ARM Cortex-M4,” in Progress in Cryptology – AFRICACRYPT 2019, LNCS 11627, pp. 111–130, 2019.',
 'C. Paquin, D. Stebila, and G. Tamvada, “Benchmarking post-quantum cryptography in TLS,” in Post-Quantum Cryptography – PQCrypto 2020, LNCS 12100, pp. 72–91, Springer, 2020.',
 'D. Sikeridis, P. Kampanakis, and M. Devetsikiotis, “Post-quantum authentication in TLS 1.3: A performance study,” in Proc. 27th Annual Network and Distributed System Security Symposium (NDSS), The Internet Society, 2020.',
 'T. Xia, M. Wang, J. He, G. Yang, L. Fan, and G. Wei, “A quantum-resistant identity authentication and key agreement scheme for UAV networks based on Kyber algorithm,” Drones 8(8), 359, 2024.',
 'A. Hussien and A. A. Abdullah, “A post-quantum lightweight mutual authentication and encryption scheme for secure UAV communications,” Frontiers in Computer Science 8, 2026.',
 'Y. Zeng, R. Zhang, and T. J. Lim, “Wireless communications with unmanned aerial vehicles: Opportunities and challenges,” IEEE Communications Magazine 54(5), pp. 36–42, 2016.',
 'RTCA, Inc., “DO-362: Command and control (C2) data link minimum operational performance standards (MOPS) (terrestrial),” tech. rep., RTCA, Inc., Washington, DC, USA, 2016.',
 'MAVLink Development Team, “MAVLink developer guide,” https://mavlink.io/en/, 2024.',
 'X. Huang, Y. Han, S. Zhu, H. Wu, and Z. Liu, “Measurement package: post-quantum TLS 1.3 handshakes over an emulated narrowband command-and-control link,” https://github.com/huanghuayu12/pqc-uav-drones, 2026.',
 'E. Rescorla, “The transport layer security (TLS) protocol version 1.3,” RFC 8446, 2018.',
 'Open Quantum Safe Project, “liboqs: An open-source C library for quantum-safe cryptography,” https://openquantumsafe.org/, 2024.',
 'E. Rescorla, H. Tschofenig, and T. Fossati, “The datagram transport layer security (DTLS) protocol version 1.3,” RFC 9147, 2022.',
 'E. Rescorla and N. Modadugu, “Datagram transport layer security version 1.2,” RFC 6347, 2012.',
 'J. Chu, N. Dukkipati, Y. Cheng, and M. Mathis, “Increasing TCP’s initial window,” RFC 6928, 2013.',
 'D. Sikeridis, P. Kampanakis, and M. Devetsikiotis, “Assessing the overhead of post-quantum cryptography in TLS 1.3 and SSH,” in Proc. 16th International Conference on Emerging Networking Experiments and Technologies (CoNEXT), pp. 149–156, ACM, 2020.',
 'P. Schwabe, D. Stebila, and T. Wiggers, “Post-quantum TLS without handshake signatures,” in Proc. 2020 ACM SIGSAC Conference on Computer and Communications Security (CCS), pp. 1461–1480, ACM, 2020.',
]

# ---------------------------------------------------------------- inline

ESC = [(r"\{,\}", ","), (r"\,", " "), (r"~", " "), (r"---", "\u2014"),
       (r"--", "\u2013"), (r"\%", "%"), (r"\{", "{"), (r"\}", "}"),
       (r"\_", "_"), (r"\&", "&"), (r"\#", "#"), (r"\$", "$")]

TOKEN = re.compile(r"\\(cite|texttt|textbf|emph|ref|url|supit)\{([^}]*)\}")


def plain(s):
    s = s.replace(r"\mav{}", "MAVLink")
    s = s.replace("{,}", ",")
    s = s.replace(r"$\to$", "\u2192")
    s = s.replace(r"$\times$", "\u00d7").replace(r"$+$", "+")
    s = s.replace(r"\quad", "\u2003")
    s = s.replace(r"\ ", " ")
    for a, b in ESC:
        s = s.replace(a, b)
    s = s.replace("{,}", ",")
    return s


def runs(s):
    """LaTeX inline -> list of (text, fmt-dict)."""
    s = s.replace("{,}", ",")
    out, pos = [], 0
    for m in TOKEN.finditer(s):
        if m.start() > pos:
            out.append((plain(s[pos:m.start()]), {}))
        kind, arg = m.group(1), m.group(2)
        if kind == "cite":
            nums = ",".join(str(CITE[k.strip()]) for k in arg.split(","))
            out.append((nums, {"sup": True}))
        elif kind == "ref":
            out.append((REF[arg.strip()], {}))
        elif kind == "texttt":
            out.append((plain(arg), {"mono": True}))
        elif kind == "textbf":
            out.append((plain(arg), {"bold": True}))
        elif kind == "emph":
            out.append((plain(arg), {"italic": True}))
        elif kind == "url":
            out.append((arg, {"mono": True}))
        elif kind == "supit":
            out.append((arg, {"sup": True}))
        pos = m.end()
    if pos < len(s):
        out.append((plain(s[pos:]), {}))
    return [(t, f) for t, f in out if t]


def add_runs(p, spec):
    for text, fmt in spec:
        r = p.add_run(text)
        if fmt.get("bold"):
            r.bold = True
        if fmt.get("italic"):
            r.italic = True
        if fmt.get("mono"):
            r.font.name = "Courier New"
            r.font.size = Pt(9)
        if fmt.get("sup"):
            r.font.superscript = True
    return p


# ---------------------------------------------------------------- blocks

def load_tex():
    s = open("main.tex", encoding="utf-8").read()
    s = re.sub(r"(?m)^\s*%.*$", "", s)
    body = s.split(r"\begin{document}", 1)[1].split(r"\end{document}", 1)[0]
    abstract = re.search(r"\\begin\{abstract\}(.*?)\\end\{abstract\}", body, re.S).group(1)
    keywords = re.search(r"\\keywords\{([^}]*)\}", body).group(1)
    ack = re.search(r"\\acknowledgments(.*?)(?:\\bibliography|\\end\{document\})", body, re.S)
    body = re.sub(r"\\begin\{abstract\}.*?\\end\{abstract\}", "", body, flags=re.S)
    body = re.sub(r"\\keywords\{[^}]*\}", "", body)
    body = re.sub(r"\\begin\{table\}.*?\\end\{table\}", "\n@@TABLE@@\n", body, flags=re.S)
    body = re.sub(r"\\begin\{figure\}.*?\\end\{figure\}", "\n@@FIGURE@@\n", body, flags=re.S)
    body = re.sub(r"\\acknowledgments.*?\\bibliographystyle\{[^}]*\}", "", body, flags=re.S)
    body = re.sub(r"\\maketitle|\\label\{[^}]*\}", "", body)
    return body, abstract.strip(), keywords.strip(), (ack.group(1).strip() if ack else "")


def blocks(body):
    """Yield ('h1'|'h2'|'p'|'marker', text)."""
    body = body.replace("@@TABLE@@", "\n\n@@TABLE@@\n\n").replace("@@FIGURE@@", "\n\n@@FIGURE@@\n\n")
    out = []
    for chunk in re.split(r"\n\s*\n", body):
        c = chunk.strip()
        if not c:
            continue
        if c in ("@@TABLE@@", "@@FIGURE@@"):
            out.append(("marker", c.strip("@")))
            continue
        m = re.match(r"\\section\*?\{([^}]*)\}", c, re.S)
        if m:
            out.append(("h1", m.group(1)))
            continue
        m = re.match(r"\\subsection\*?\{([^}]*)\}", c, re.S)
        if m:
            out.append(("h2", m.group(1)))
            continue
        c = re.sub(r"\s*\n\s*", " ", c)
        out.append(("p", c))
    return out


# ---------------------------------------------------------------- docx bits

def clear_body(doc):
    body = doc.element.body
    for child in list(body):
        if child.tag == qn("w:sectPr"):
            continue
        body.remove(child)


def shade(cell, hexcolor="F2F2F2"):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hexcolor)
    tcPr.append(shd)


def borders(table, header_rows=1):
    tbl = table._tbl
    tblPr = tbl.tblPr
    b = OxmlElement("w:tblBorders")
    for edge, sz in (("top", 8), ("bottom", 8), ("left", 0), ("right", 0),
                     ("insideH", 0), ("insideV", 0)):
        e = OxmlElement(f"w:{edge}")
        e.set(qn("w:val"), "single" if sz else "none")
        e.set(qn("w:sz"), str(sz))
        e.set(qn("w:space"), "0")
        e.set(qn("w:color"), "000000")
        b.append(e)
    tblPr.append(b)
    # rule under the header row
    for cell in table.rows[header_rows - 1].cells:
        tcPr = cell._tc.get_or_add_tcPr()
        tb = OxmlElement("w:tcBorders")
        bottom = OxmlElement("w:bottom")
        bottom.set(qn("w:val"), "single")
        bottom.set(qn("w:sz"), "6")
        bottom.set(qn("w:color"), "000000")
        tb.append(bottom)
        tcPr.append(tb)


def cell_text(cell, text, bold=False, italic=False, size=9, align=None):
    cell.text = ""
    p = cell.paragraphs[0]
    p.paragraph_format.space_before = Pt(1)
    p.paragraph_format.space_after = Pt(1)
    p.paragraph_format.line_spacing = 1.0
    if align is not None:
        p.alignment = align
    for t, f in runs(text):
        r = p.add_run(t)
        r.font.size = Pt(size)
        r.bold = bold or f.get("bold")
        r.italic = italic or f.get("italic")
        if f.get("mono"):
            r.font.name = "Courier New"
        if f.get("sup"):
            r.font.superscript = True


def make_table(doc, widths, rows, aligns, header=True):
    t = doc.add_table(rows=len(rows), cols=len(widths))
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.autofit = False
    for row in t.rows:
        for i, w in enumerate(widths):
            row.cells[i].width = Cm(w)
    for ri, row in enumerate(rows):
        for ci, txt in enumerate(row):
            cell_text(row and t.cell(ri, ci), txt,
                      bold=(header and ri == 0),
                      size=9, align=aligns[ci])
    borders(t, header_rows=1)
    return t


def caption(doc, text, before=True):
    p = doc.add_paragraph(style="SPIE figure caption")
    p.paragraph_format.space_before = Pt(6 if before else 2)
    p.paragraph_format.space_after = Pt(6 if not before else 2)
    add_runs(p, runs(text))
    return p


def body_par(doc, text, style="SPIE body text"):
    p = doc.add_paragraph(style=style)
    add_runs(p, runs(text))
    return p


# ---------------------------------------------------------------- tables

T1 = [
    ["#", "Failure mode", "Effect on the reported number", "Correction"],
    ["1", "Token bucket credited the same wait twice",
     "link ran at 14.73 instead of 9.60\u2009kbps, 53\u2009% fast",
     "allow the balance to go negative"],
    ["2", "Free initial burst of 1,400 bytes",
     "1.17\u2009s uncharged at 9.6\u2009kbps", "burst set to zero"],
    ["3", "\\texttt{-www} status page counted as handshake",
     "about 5\\,kB of HTML against a 1.9\\,kB handshake, 72\\,% of the count",
     "server run without \\texttt{-www}"],
    ["4", "\\texttt{NewSessionTicket} inside or outside the window",
     "12\\,% byte variation between runs", "tickets disabled on both sides"],
    ["5", "\\texttt{-CAfile} certificate copied into each ticket",
     "20{,}840 $\\to$ 32{,}236 bytes, $+$54.7\\,%",
     "\\texttt{-no\\_ticket} on the server as well"],
]

T2 = [
    ["Message", "Bytes", "Contents"],
    ["\\emph{client $\\to$ server} (total 10{,}372)", "", ""],
    ["\\quad \\texttt{ClientHello}", "1{,}357", "key share 1{,}192"],
    ["\\quad \\texttt{Certificate}", "5{,}549", "DER 5{,}514 $+$ 35 framing"],
    ["\\quad \\texttt{CertificateVerify}", "3{,}339", "signature 3{,}309 $+$ 30"],
    ["\\quad \\texttt{Finished}", "74", ""],
    ["\\quad \\emph{framing}", "53", "CCS 6, probe 23, close 24"],
    ["\\emph{server $\\to$ client} (total 10{,}468)", "", ""],
    ["\\quad \\texttt{ServerHello}", "1{,}183", "key share 1{,}096"],
    ["\\quad \\texttt{EncryptedExtensions}", "28", ""],
    ["\\quad \\texttt{CertificateRequest}", "107", ""],
    ["\\quad \\texttt{Certificate}", "5{,}549", "as above"],
    ["\\quad \\texttt{CertificateVerify}", "3{,}339", "as above"],
    ["\\quad \\texttt{Finished}", "74", ""],
    ["\\quad \\emph{framing}", "188", "CCS 6, tickets 158, close 24"],
    ["Total", "20{,}840", ""],
]

T1_CAP = ("Table 1. The five measurement pitfalls. The middle columns give the "
          "effect each had on the reported number before it was found, and the last "
          "column the change that removed it. No number in this paper predates the "
          "fixes.")
T2_CAP = ("Table 2. Per-message reconstruction of the corrected handshake. Bytes in "
          "the second column are read off the wire by the record parser; bytes in the "
          "third column follow from FIPS 203/204 and X.509 framing, so the two columns "
          "check each other. Framing rows hold the records that carry no handshake "
          "content: ChangeCipherSpec, the 23-byte liveness probe (client), the two "
          "tickets (server, 79 bytes each here), and close_notify.")
FIG_CAP = ("Fig. 1. Pitfall 5. Both bars are the same mutual-authentication "
           "ML-KEM-768+ML-DSA-65 handshake. In the left bar the server was started "
           "with -no_ticket and the two post-handshake records are 79 bytes each; in "
           "the right bar that flag was omitted and the -CAfile certificate is "
           "embedded in each ticket. Reporting the right-hand bar as the cost of "
           "post-quantum authentication would have overstated it by 54.7%.")


def main():
    body, abstract, keywords, ack = load_tex()
    bl = blocks(body)

    doc = docx.Document(TEMPLATE)
    clear_body(doc)

    p = doc.add_paragraph(style="SPIE paper title")
    add_runs(p, [("Five ways to mismeasure a post-quantum TLS 1.3 handshake "
                  "on a narrowband link", {})])

    p = doc.add_paragraph(style="SPIE Authors-Affils")
    p.paragraph_format.space_before = Pt(12)
    for text, fmt in [("Xiaoyu Huang*", {}), ("a,b", {"sup": True}),
                      (", Yiliang Han", {}), ("a,b", {"sup": True}),
                      (", Shuaishuai Zhu", {}), ("a,b", {"sup": True}),
                      (", Hui Wu", {}), ("a,b", {"sup": True}),
                      (", Zhongqiang Liu", {}), ("a,b", {"sup": True})]:
        r = p.add_run(text)
        if fmt.get("sup"):
            r.font.superscript = True

    p = doc.add_paragraph(style="SPIE Authors-Affils")
    p.paragraph_format.space_before = Pt(6)
    r = p.add_run("a")
    r.font.superscript = True
    p.add_run("Engineering University of PAP, Xi\u2019an, 710086, Shaanxi, China; ")
    r = p.add_run("b")
    r.font.superscript = True
    p.add_run("Key Lab of the Armed Police Force for Network and Information "
              "Security, Xi\u2019an, 710086, Shaanxi, China")

    p = doc.add_paragraph(style="SPIE body text")
    p.paragraph_format.space_before = Pt(6)
    p.add_run("*19591587786@163.com")

    p = doc.add_paragraph(style="SPIE abstract title")
    p.paragraph_format.space_before = Pt(12)
    p.add_run("Abstract")

    for para in [x.strip() for x in re.split(r"\n\s*\n", abstract) if x.strip()]:
        body_par(doc, re.sub(r"\s*\n\s*", " ", para), style="SPIE abstract body text")

    p = doc.add_paragraph(style="SPIE keywords")
    p.paragraph_format.space_before = Pt(6)
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    r = p.add_run("Keywords: ")
    r.bold = True
    p.add_run(keywords)

    # ---- sections
    n_tab = 0
    for kind, text in bl:
        if kind == "h1":
            p = doc.add_paragraph(style="Heading 1")
            p.paragraph_format.space_before = Pt(10)
            p.add_run(text.upper())
        elif kind == "h2":
            p = doc.add_paragraph(style="Heading 2")
            p.add_run(text)
        elif kind == "marker":
            if text == "TABLE":
                n_tab += 1
                if n_tab == 1:
                    caption(doc, T1_CAP, before=True)
                    make_table(doc, [0.9, 5.0, 6.0, 4.2], T1,
                               [WD_ALIGN_PARAGRAPH.CENTER,
                                WD_ALIGN_PARAGRAPH.LEFT,
                                WD_ALIGN_PARAGRAPH.LEFT,
                                WD_ALIGN_PARAGRAPH.LEFT])
                else:
                    caption(doc, T2_CAP, before=True)
                    make_table(doc, [6.2, 2.0, 8.0], T2,
                               [WD_ALIGN_PARAGRAPH.LEFT,
                                WD_ALIGN_PARAGRAPH.RIGHT,
                                WD_ALIGN_PARAGRAPH.LEFT])
            else:
                p = doc.add_paragraph()
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                p.paragraph_format.space_before = Pt(10)
                p.add_run().add_picture(FIG, width=Cm(9.6))
                caption(doc, FIG_CAP, before=False)
        else:
            body_par(doc, text)

    # ---- acknowledgments
    p = doc.add_paragraph(style="Heading 1")
    p.paragraph_format.space_before = Pt(12)
    p.add_run("ACKNOWLEDGMENTS")
    for para in [x.strip() for x in re.split(r"\n\s*\n", ack) if x.strip()]:
        body_par(doc, re.sub(r"\s*\n\s*", " ", para))

    # ---- references
    p = doc.add_paragraph(style="Heading 1")
    p.paragraph_format.space_before = Pt(12)
    p.add_run("REFERENCES")
    for i, ref in enumerate(REFERENCES, 1):
        p = doc.add_paragraph(style="SPIE reference listing")
        p.paragraph_format.space_after = Pt(2)
        p.paragraph_format.left_indent = Cm(0.6)
        p.paragraph_format.first_line_indent = Cm(-0.6)
        p.add_run(ref)

    doc.save(OUT)
    print("wrote", OUT)


if __name__ == "__main__":
    main()
