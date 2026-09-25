"""EVIDENCE.md ledger: read, append, validate, and audit a .tex file against it.

Ledger format (SPEC §3), a single Markdown table::

    | ID | number/fact as printed in paper | command | log path | commit | machine | date | runs/median |
    |----|----|----|----|----|----|----|----|
    | E1 | 1.23 s | crbench run ... | results/toy/run.json | 1a2b3c4 | host:ab12cd | 2026-01-01 | 5 / median |
    | E2 | 2.00× | derived: E1/E3 | - | - | - | 2026-01-01 | - |

Rules enforced here:

* every row has ID, printed value, command and (unless ``derived:``) a log path;
* IDs are unique; ``derived:`` rows only reference existing IDs;
* with ``root`` given, log paths must exist;
* ``audit_tex``: every *measurement-like* number in the paper body is either listed in
  some row's printed column, or explicitly tagged ``\\evid{ID}`` (and then it must
  match that row), or sits on a line carrying ``% crbench:ignore``.
"""
from __future__ import annotations

import os
import re
import time
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation

HEADER = ["ID", "number/fact as printed in paper", "command", "log path", "commit", "machine", "date", "runs/median"]
KEYS = ["id", "printed", "command", "log", "commit", "machine", "date", "runs"]
_HEADER_HINTS = [
    ("id", ("id",)),
    ("printed", ("number", "fact", "printed", "value")),
    ("command", ("command", "cmd")),
    ("log", ("log",)),
    ("commit", ("commit",)),
    ("machine", ("machine", "host")),
    ("date", ("date",)),
    ("runs", ("runs", "median", "repeat")),
]


@dataclass
class Issue:
    severity: str  # "error" | "warning"
    kind: str
    message: str
    line: int = 0
    number: str = ""

    def __str__(self) -> str:
        loc = f"line {self.line}: " if self.line else ""
        return f"[{self.severity}] {self.kind}: {loc}{self.message}"


# ------------------------------------------------------------------ ledger I/O
def _split_row(line: str) -> list[str]:
    s = line.strip()
    if s.startswith("|"):
        s = s[1:]
    if s.endswith("|"):
        s = s[:-1]
    cells = re.split(r"(?<!\\)\|", s)
    return [c.strip().replace(r"\|", "|") for c in cells]


def _map_header(cells: list[str]) -> dict[int, str]:
    m: dict[int, str] = {}
    for i, c in enumerate(cells):
        lc = c.lower()
        for key, hints in _HEADER_HINTS:
            if key in m.values():
                continue
            if (key == "id" and lc.strip("`* ") == "id") or (key != "id" and any(h in lc for h in hints)):
                m[i] = key
                break
    return m


def read_ledger(path: str) -> list[dict]:
    """Parse the first Markdown table with an ``ID`` column.  Each row dict has KEYS + ``_line``."""
    rows: list[dict] = []
    if not os.path.exists(path):
        return rows
    with open(path, encoding="utf-8") as f:
        lines = f.readlines()
    colmap: dict[int, str] | None = None
    for ln, line in enumerate(lines, 1):
        if not line.strip().startswith("|"):
            if colmap is not None and rows:
                break  # end of the table
            continue
        cells = _split_row(line)
        if colmap is None:
            m = _map_header(cells)
            if "id" in m.values() and "printed" in m.values():
                colmap = m
            continue
        if all(re.fullmatch(r":?-{2,}:?", c) for c in cells if c):
            continue
        row = {k: "" for k in KEYS}
        for i, c in enumerate(cells):
            if i in colmap:
                row[colmap[i]] = c
        row["_line"] = ln
        if row["id"]:
            rows.append(row)
    return rows


def next_id(rows: list[dict], prefix: str = "E") -> str:
    nums = [int(m.group(1)) for r in rows if (m := re.fullmatch(rf"{re.escape(prefix)}(\d+)", r["id"]))]
    return f"{prefix}{max(nums, default=0) + 1}"


def _esc(s: str) -> str:
    return str(s).replace("|", r"\|").replace("\n", " ")


def append_row(path: str, printed: str, command: str, log: str, commit: str = "", machine: str = "",
               date: str | None = None, runs: str = "", id: str | None = None) -> str:
    rows = read_ledger(path)
    rid = id or next_id(rows)
    if any(r["id"] == rid for r in rows):
        raise ValueError(f"duplicate evidence ID {rid}")
    date = date or time.strftime("%Y-%m-%d")
    new = "| " + " | ".join(_esc(x) for x in [rid, printed, command, log, commit, machine, date, runs]) + " |\n"
    if not os.path.exists(path) or not rows and "| ID" not in open(path, encoding="utf-8").read():
        mode = "a" if os.path.exists(path) else "w"
        with open(path, mode, encoding="utf-8") as f:
            if mode == "w":
                f.write("# EVIDENCE\n\nNo number enters the paper without a row here.\n\n")
            f.write("| " + " | ".join(HEADER) + " |\n|" + "|".join(["---"] * len(HEADER)) + "|\n" + new)
        return rid
    with open(path, encoding="utf-8") as f:
        lines = f.readlines()
    last = max(r["_line"] for r in rows) if rows else None
    if last is None:  # header exists but no rows: insert after separator
        for i, l in enumerate(lines):
            if re.match(r"^\|\s*:?-{2,}", l):
                last = i + 1
                break
    lines.insert(last, new)
    with open(path, "w", encoding="utf-8") as f:
        f.writelines(lines)
    return rid


def validate_ledger(rows: list[dict], root: str | None = None) -> list[Issue]:
    issues: list[Issue] = []
    ids = [r["id"] for r in rows]
    seen = set()
    for r in rows:
        ln = r.get("_line", 0)
        if r["id"] in seen:
            issues.append(Issue("error", "duplicate-id", f"ID {r['id']} appears twice", ln))
        seen.add(r["id"])
        for k in ("printed", "command"):
            if not r[k]:
                issues.append(Issue("error", "missing-field", f"{r['id']}: empty '{k}'", ln))
        derived = r["command"].lower().startswith("derived")
        if derived:
            for ref in re.findall(r"\b([A-Z]+\d+)\b", r["command"]):
                if ref not in ids:
                    issues.append(Issue("error", "bad-derivation", f"{r['id']} derives from unknown {ref}", ln))
        else:
            if not r["log"] or r["log"] in ("-", "--"):
                issues.append(Issue("error", "missing-log", f"{r['id']}: measured value without a log path", ln))
            elif root is not None:
                for lp in re.split(r"[,;]\s*", r["log"].strip("`")):
                    lp = lp.strip("` ")
                    if lp and not os.path.exists(os.path.join(root, lp)):
                        issues.append(Issue("error", "log-not-found", f"{r['id']}: {lp} does not exist under root", ln))
            for k in ("commit", "machine", "date", "runs"):
                if not r[k] or r[k] in ("-", "--"):
                    issues.append(Issue("warning", "missing-field", f"{r['id']}: empty '{k}'", ln))
    return issues


# ------------------------------------------------------------------ number handling
_NUM_RX = re.compile(r"(?<![\w.])[-+]?(?:\d{1,3}(?:(?:,|\{,\}|\\,)\d{3})+|\d+)(?:\.\d+)?(?![\w])|(?<![\w.])\.\d+")


def normalize_number(tok: str) -> str | None:
    t = tok.replace("{,}", "").replace("\\,", "").replace(",", "").lstrip("+")
    try:
        d = Decimal(t)
    except InvalidOperation:
        return None
    d = d.normalize()
    s = format(d, "f")
    return "0" if s in ("-0", "0") else s


def numbers_in(text: str) -> list[str]:
    out = []
    for m in _NUM_RX.finditer(text):
        n = normalize_number(m.group(0))
        if n is not None:
            out.append(n)
    return out


# units that make a bare integer "measurement-like"
_UNIT_RX = re.compile(
    r"^\s*(?:~|\\,|\\;|\\ |\$)?\s*(?:\\times|×|x\b|\\%|%|ms\b|s\b|sec|µs|\\mu\s*s|us\b|ns\b|min\b|h\b|hours?\b|seconds?\b|"
    r"[KMGT]i?B\b|bytes?\b|bits?\b|cycles?\b|ops\b|MHz|GHz|kbit|Mbit|Gbit|rounds?\b|\\mathrm\{\s*(?:ms|s|MB|GB|KB|KiB|MiB|GiB)\s*\})",
    re.I,
)

_DROP_CMDS_WITH_ARG = (
    "label", "ref", "eqref", "cref", "Cref", "autoref", "pageref", "cite", "citep", "citet", "citeauthor", "citeyear",
    "url", "input", "include", "includegraphics", "usepackage", "documentclass", "bibliography", "bibliographystyle",
    "vspace", "hspace", "setlength", "addtolength", "begin", "end", "hypersetup", "definecolor", "setcounter",
    "addcontentsline", "newcommand", "renewcommand", "providecommand", "DeclareMathOperator", "multicolumn", "cline", "cmidrule",
    "tabcolsep", "arraystretch", "resizebox", "scalebox", "rule", "linespread", "fontsize", "href",
)


def strip_tex(line: str) -> str:
    """Remove comments and non-prose command arguments from one line of LaTeX."""
    line = re.sub(r"(?<!\\)%.*$", "", line)
    # \cmd*[opt]{arg}  (one level of braces is enough for these commands)
    names = "|".join(_DROP_CMDS_WITH_ARG)
    line = re.sub(rf"\\(?:{names})\*?(?:\[[^\]]*\])*(?:\{{[^{{}}]*\}})?(?:\{{[^{{}}]*\}})?", " ", line)
    line = re.sub(r"\\evid\{[^}]*\}", " ", line)
    line = re.sub(r"\\[a-zA-Z]+\d*", lambda m: " " if re.search(r"\d", m.group(0)) else m.group(0), line)
    return line


def _measurement_numbers(line: str, strict: bool) -> list[tuple[str, str]]:
    out = []
    for m in _NUM_RX.finditer(line):
        raw = m.group(0)
        n = normalize_number(raw)
        if n is None:
            continue
        if strict:
            out.append((raw, n))
            continue
        after = line[m.end(): m.end() + 24]
        before = line[max(0, m.start() - 2): m.start()]
        is_decimal = "." in raw
        has_sep = bool(re.search(r",|\{,\}|\\,", raw))
        has_unit = bool(_UNIT_RX.match(after))
        is_exponent = before.endswith("^") or before.endswith("^{")
        if is_exponent and not strict:
            # 2^{128}: security exponents are claims too -> audit them
            out.append((raw, n))
        elif is_decimal or has_sep or has_unit:
            out.append((raw, n))
    return out


def audit_tex(tex_path: str, ledger_rows: list[dict], strict: bool = False, body_only: bool = True) -> list[Issue]:
    """Check every measurement-like number in ``tex_path`` against the ledger."""
    with open(tex_path, encoding="utf-8") as f:
        lines = f.read().split("\n")
    by_id = {r["id"]: r for r in ledger_rows}
    known: set[str] = set()
    for r in ledger_rows:
        known.update(numbers_in(r["printed"]))
    has_document = any(r"\begin{document}" in l for l in lines)
    in_body = not (body_only and has_document)
    issues: list[Issue] = []
    ignore_block = False
    for ln, raw_line in enumerate(lines, 1):
        if r"\begin{document}" in raw_line:
            in_body = True
            continue
        if r"\end{document}" in raw_line:
            break
        if "crbench:ignore-begin" in raw_line:
            ignore_block = True
            continue
        if "crbench:ignore-end" in raw_line:
            ignore_block = False
            continue
        if not in_body or ignore_block or "crbench:ignore" in raw_line:
            continue
        # explicit evidence tags: number immediately before \evid{ID}
        for m in re.finditer(r"\\evid\{([^}]*)\}", raw_line):
            eid = m.group(1).strip()
            prev = numbers_in(strip_tex(raw_line[max(0, m.start() - 60): m.start()]))
            if eid not in by_id:
                issues.append(Issue("error", "unknown-id", f"\\evid{{{eid}}} not in EVIDENCE.md", ln))
            elif prev and prev[-1] not in numbers_in(by_id[eid]["printed"]):
                issues.append(Issue("error", "mismatch", f"value {prev[-1]} tagged {eid} but ledger prints '{by_id[eid]['printed']}'", ln, prev[-1]))
        text = strip_tex(raw_line)
        for raw, n in _measurement_numbers(text, strict):
            if n not in known:
                ctx = text.strip()
                ctx = ctx if len(ctx) <= 90 else ctx[:87] + "..."
                issues.append(Issue("error", "untraced", f"number {raw} has no EVIDENCE row  ::  {ctx}", ln, raw))
    return issues


if __name__ == "__main__":
    import tempfile

    d = tempfile.mkdtemp()
    led = os.path.join(d, "EVIDENCE.md")
    append_row(led, "1.23 s", "crbench run ...", "results/a.log", "abc123", "host:x", "2026-01-01", "5/median")
    append_row(led, "2.00×", "derived: E1/E1", "-", date="2026-01-01")
    tex = os.path.join(d, "p.tex")
    open(tex, "w").write("\\begin{document}\nIt takes 1.23 s, a 2.00$\\times$ gain, but 9.9 ms is untraced.\n\\end{document}\n")
    rows = read_ledger(led)
    for i in validate_ledger(rows) + audit_tex(tex, rows):
        print(i)
