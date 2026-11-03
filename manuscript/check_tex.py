#!/usr/bin/env python3
"""Static sanity checks for main.tex that do not require a TeX installation.

Catches the error classes that are most likely when a manuscript is written
without a compiler available: undefined citation keys, dangling cross-
references, unbalanced environments, missing figure files, and used-but-
undefined macros.
"""

from __future__ import annotations

import re
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
TEX = HERE / "main.tex"
BIB = HERE / "references.bib"

problems: list[str] = []
notes: list[str] = []


def strip_comments(text: str) -> str:
    out = []
    for line in text.splitlines():
        cut = None
        for m in re.finditer(r"(?<!\\)%", line):
            cut = m.start()
            break
        out.append(line if cut is None else line[:cut])
    return "\n".join(out)


tex = strip_comments(TEX.read_text())
bib = BIB.read_text()

# ---------------------------------------------------------------- citations
cite_keys: set[str] = set()
for m in re.finditer(r"\\cite[a-zA-Z]*\*?(?:\[[^\]]*\])*\{([^}]*)\}", tex):
    for k in m.group(1).split(","):
        if k.strip():
            cite_keys.add(k.strip())

bib_keys = set(re.findall(r"@\w+\{([^,]+),", bib))
missing = sorted(cite_keys - bib_keys)
unused = sorted(bib_keys - cite_keys)
for k in missing:
    problems.append(f"citation key not in references.bib: {k}")
for k in unused:
    notes.append(f"bib entry never cited (BibTeX will drop or warn): {k}")

# ---------------------------------------------------------------- refs
labels = set(re.findall(r"\\label\{([^}]*)\}", tex))
refs = set()
for m in re.finditer(r"\\(?:ref|eqref)\{([^}]*)\}", tex):
    refs.add(m.group(1))
for r in sorted(refs - labels):
    problems.append(f"\\ref to undefined label: {r}")
for l in sorted(labels - refs):
    notes.append(f"label defined but never referenced: {l}")

dup = [l for l, c in Counter(re.findall(r"\\label\{([^}]*)\}", tex)).items() if c > 1]
for d in dup:
    problems.append(f"duplicate label: {d}")

# ---------------------------------------------------------------- environments
stack: list[tuple[str, int]] = []
for i, line in enumerate(tex.splitlines(), 1):
    for m in re.finditer(r"\\(begin|end)\{([^}]*)\}", line):
        kind, env = m.group(1), m.group(2)
        if kind == "begin":
            stack.append((env, i))
        else:
            if not stack:
                problems.append(f"line {i}: \\end{{{env}}} with no open environment")
            elif stack[-1][0] != env:
                problems.append(
                    f"line {i}: \\end{{{env}}} closes \\begin{{{stack[-1][0]}}} "
                    f"opened on line {stack[-1][1]}")
                stack.pop()
            else:
                stack.pop()
for env, line in stack:
    problems.append(f"line {line}: \\begin{{{env}}} never closed")

# ---------------------------------------------------------------- figures
for m in re.finditer(r"\\includegraphics(?:\[[^\]]*\])?\{([^}]*)\}", tex):
    target = m.group(1)
    base = HERE / target
    if not any((base.with_suffix(ext)).exists() for ext in (".pdf", ".png", ".jpg")):
        problems.append(f"figure file not found: {target}(.pdf/.png)")

# ---------------------------------------------------------------- macros
defined = set(re.findall(r"\\(?:newcommand|renewcommand)\*?\{?\\([A-Za-z]+)\}?", tex))
# commands provided by LaTeX/amsmath/the MDPI class; not exhaustive, but the
# checker only flags names that look project-specific (lowercase, multi-letter)
builtin = set("""documentclass usepackage newcommand renewcommand begin end
section subsection subsubsection paragraph label ref eqref cite includegraphics
caption centering hline cline multicolumn multirow textbf textit emph mathrm
mathit text times pm leq geq approx infty sum frac left right quad qquad
sqrt cdot ldots dots vspace hspace newline maketitle abstract keyword
Title Author AuthorNames AuthorCitation address firstnote corres
abstractkeyword makedata title reftitle externalbibliography bibliography
funding institutionalreview informedconsent dataavailability acknowledgments
conflictsofinterest authorcontributions externaleditor datereceived daterevised
dateaccepted datepublished pubvolume issuenum articlenumber doinum pubyear
copyrightyear firstpage lastpage setcounter makeatletter makeatother
texorpdfstring url si linewidth textwidth textheight columnwidth
item description enumerate hline toprule midrule bottomrule tabular table figure
small footnotesize scriptsize tiny large Large normalsize
texttt textrm textsf textsc textsl underline mbox hbox vbox par noindent
path raggedright ttfamily quote
to rightarrow leftarrow times div ast sim simeq neq ll gg subset sigma pm
dagger ddagger S P copyright registered textdegree degree celsius
abbreviations nolinkurl href emph textsuperscript textsubscript
""".split())
used = set(re.findall(r"\\([A-Za-z]{2,})", tex))
suspicious = sorted(u for u in used - builtin - defined
                    if u[0].islower() and u not in {"kbps", "Mbps"})
for u in suspicious:
    notes.append(f"command \\{u} is not obviously a builtin or a defined macro "
                 f"-- confirm it exists in the template")

# ---------------------------------------------------------------- braces
depth = 0
for i, line in enumerate(tex.splitlines(), 1):
    j = 0
    while j < len(line):
        ch = line[j]
        if ch == "\\":
            j += 2
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth < 0:
                problems.append(f"line {i}: unmatched closing brace")
                depth = 0
        j += 1
if depth != 0:
    problems.append(f"global brace imbalance: {depth:+d}")

# ---------------------------------------------------------------- report
print(f"citations: {len(cite_keys)} distinct keys, {len(bib_keys)} bib entries")
print(f"references: {len(refs)} \\ref targets, {len(labels)} labels\n")

if problems:
    print(f"ERRORS ({len(problems)}):")
    for p in problems:
        print("  -", p)
else:
    print("No structural errors found.")

if notes:
    print(f"\nNOTES ({len(notes)}):")
    for n in notes:
        print("  -", n)

sys.exit(1 if problems else 0)
