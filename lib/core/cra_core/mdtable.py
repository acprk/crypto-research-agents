"""Lossless Markdown-table editing.

Only rows that are changed or added are re-rendered; every other byte of the file (prose,
other tables, untouched rows) is preserved, so ``Document(text).render() == text``.
Cells use GitHub-flavoured Markdown escaping: a literal ``|`` inside a cell is ``\\|``.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

_SEP = re.compile(r"^\s*\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)*\|?\s*$")


def split_row(line: str) -> list[str]:
    s = line.strip()
    if s.startswith("|"):
        s = s[1:]
    if s.endswith("|") and not s.endswith("\\|"):
        s = s[:-1]
    return [c.strip().replace("\\|", "|") for c in re.split(r"(?<!\\)\|", s)]


def esc(cell: object) -> str:
    return str(cell).replace("\r", " ").replace("\n", " ").replace("|", "\\|").strip()


def render_row(cells: list[str]) -> str:
    return "| " + " | ".join(esc(c) for c in cells) + " |"


@dataclass
class Row:
    cells: list[str]
    line: int                 # 1-based line number in the source (0 for new rows)
    raw: str | None = None    # original text; None once modified

    def get(self, i: int) -> str:
        return self.cells[i] if i < len(self.cells) else ""


@dataclass
class Table:
    header: list[str]
    rows: list[Row]
    start: int                # 0-based index of the header line
    end: int                  # 0-based index one past the last row line
    keys: dict[str, int] = field(default_factory=dict)   # semantic key -> column index

    def col(self, key: str) -> int | None:
        return self.keys.get(key)

    def value(self, row: Row, key: str) -> str:
        i = self.keys.get(key)
        return row.get(i) if i is not None else ""

    def set(self, row: Row, key: str, value: str) -> None:
        i = self.keys[key]
        while len(row.cells) < len(self.header):
            row.cells.append("")
        row.cells[i] = str(value)
        row.raw = None

    def append(self, values: dict[str, str]) -> Row:
        cells = [""] * len(self.header)
        for k, v in values.items():
            if k in self.keys:
                cells[self.keys[k]] = str(v)
        r = Row(cells, 0, None)
        self.rows.append(r)
        return r

    def as_dicts(self) -> list[dict[str, str]]:
        return [{k: self.value(r, k) for k in self.keys} | {"_line": r.line} for r in self.rows]


Hints = list[tuple[str, "callable"]]


def map_header(header: list[str], hints: Hints) -> dict[str, int]:
    """Assign each semantic key to the first unused column whose lower-cased header matches."""
    out: dict[str, int] = {}
    used: set[int] = set()
    for key, pred in hints:
        for i, h in enumerate(header):
            if i in used:
                continue
            if pred(h.lower().strip("`* ")):
                out[key] = i
                used.add(i)
                break
    return out


class Document:
    """A Markdown file as lines plus the tables found in it."""

    def __init__(self, text: str):
        self.text = text
        self.lines = text.split("\n")
        self.tables = self._scan()

    def _scan(self) -> list[Table]:
        tabs, i, L = [], 0, self.lines
        while i < len(L) - 1:
            if L[i].lstrip().startswith("|") and _SEP.match(L[i + 1]):
                header = split_row(L[i])
                j = i + 2
                rows = []
                while j < len(L) and L[j].lstrip().startswith("|"):
                    rows.append(Row(split_row(L[j]), j + 1, L[j]))
                    j += 1
                tabs.append(Table(header, rows, i, j))
                i = j
            else:
                i += 1
        return tabs

    def find(self, hints: Hints, required: tuple[str, ...]) -> Table | None:
        for t in self.tables:
            keys = map_header(t.header, hints)
            if all(k in keys for k in required):
                t.keys = keys
                return t
        return None

    def render(self) -> str:
        out: list[str] = []
        pos = 0
        for t in self.tables:
            out.extend(self.lines[pos:t.start + 2])
            for r in t.rows:
                out.append(r.raw if r.raw is not None else render_row(r.cells))
            pos = t.end
        out.extend(self.lines[pos:])
        return "\n".join(out)

    def add_table(self, header: list[str], hints: Hints, after_text: str = "") -> Table:
        """Append a new empty table at the end of the document."""
        if self.lines and self.lines[-1] == "":
            self.lines.pop()
        if after_text:
            self.lines += ["", after_text]
        self.lines += ["", render_row(header), "|" + "|".join(["---"] * len(header)) + "|", ""]
        start = len(self.lines) - 3
        t = Table(header, [], start, start + 2, map_header(header, hints))
        self.tables.append(t)
        return t
