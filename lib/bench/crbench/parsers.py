"""Regex-based, pluggable log-parser registry.

A *parser* turns raw tool output into a list of :class:`Record` objects with
normalised units (time -> seconds, memory/traffic -> bytes, security -> bits).

Shipped parsers (names used by ``crbench parse --parser NAME``):

``generic``           "time: 1.23 s", "Elapsed = 12 ms", "took 3.4sec", "RESULT name=... time=..."
``criterion``         Rust criterion (TFHE-rs, arkworks, ...):  ``time:   [1.1 ms 1.2 ms 1.3 ms]``
``gobench``           Go ``testing`` benchmarks (Lattigo, gnark): ``BenchmarkX-8  100  12345 ns/op``
``gbench``            Google Benchmark console (OpenFHE/SEAL/HEXL benches): ``BM_X  123 ns  120 ns  1000``
``helib``             HElib ``printAllTimers``: ``  name: 12.3 / 4 = 3.07   [file]``
``openfhe``           OpenFHE example style ``<Label> time: 12.3 ms`` / ``... took 12 ms``
``lattice-estimator`` ``usvp :: rop: ≈2^129.4, red: ..., β: 377, ...`` -> bits of security per attack
``sat``               CaDiCaL / CryptoMiniSat / kissat: solve time + SAT/UNSAT status
``mpspdz``            MP-SPDZ: ``Time = 0.12 seconds``, ``Data sent = 1.2 MB in ~10 rounds``
``gnu-time``          ``/usr/bin/time -v``: wall clock and max RSS

Register your own with :func:`register_parser` (see ``tests/test_parsers.py``).
"""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from typing import Callable, Iterable

TIME_UNITS = {
    "ns": 1e-9, "nanoseconds": 1e-9,
    "us": 1e-6, "µs": 1e-6, "μs": 1e-6, "microseconds": 1e-6,
    "ms": 1e-3, "milliseconds": 1e-3, "msec": 1e-3,
    "s": 1.0, "sec": 1.0, "secs": 1.0, "second": 1.0, "seconds": 1.0,
    "min": 60.0, "mins": 60.0, "minutes": 60.0,
    "h": 3600.0, "hours": 3600.0,
}
SIZE_UNITS = {
    "b": 1, "byte": 1, "bytes": 1,
    "kb": 1e3, "mb": 1e6, "gb": 1e9,
    "kib": 1024, "mib": 1024 ** 2, "gib": 1024 ** 3,
}
NUM = r"[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?"
TU = r"(?:ns|us|µs|μs|ms|msec|milliseconds|microseconds|nanoseconds|seconds|second|secs|sec|s|minutes|mins|min|hours|h)"


def to_seconds(value: float, unit: str) -> float:
    u = unit.strip()
    factor = TIME_UNITS.get(u, TIME_UNITS.get(u.lower()))
    if factor is None:
        raise ValueError(f"unknown time unit {unit!r}")
    return float(value) * factor


def to_bytes(value: float, unit: str) -> float:
    u = unit.strip().lower()
    if u not in SIZE_UNITS:
        raise ValueError(f"unknown size unit {unit!r}")
    return float(value) * SIZE_UNITS[u]


@dataclass
class Record:
    metric: str            # e.g. "time", "rop_bits", "max_rss", "sat_status"
    value: float | str
    unit: str              # normalised unit: "s", "B", "bits", "" ...
    label: str = ""        # benchmark / attack / timer name if the log provides one
    line: int = 0          # 1-based line number in the source text
    raw: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


ParserFn = Callable[[str], list[Record]]


@dataclass
class Parser:
    name: str
    fn: ParserFn
    description: str = ""
    sniff: re.Pattern | None = None  # used by auto-detection


REGISTRY: dict[str, Parser] = {}


def register_parser(name: str, description: str = "", sniff: str | None = None):
    """Decorator: ``@register_parser("mytool", sniff=r"MyTool v\\d")``."""

    def deco(fn: ParserFn) -> ParserFn:
        REGISTRY[name] = Parser(name, fn, description, re.compile(sniff, re.M) if sniff else None)
        return fn

    return deco


def regex_parser(name: str, pattern: str, metric: str = "time", kind: str = "time",
                 description: str = "", sniff: str | None = None, flags=re.M | re.I) -> ParserFn:
    """Build and register a one-regex parser.

    ``pattern`` must have named groups ``value`` and ``unit`` (``unit`` optional ->
    seconds for time), and optionally ``label``.
    """
    rx = re.compile(pattern, flags)

    def fn(text: str) -> list[Record]:
        out = []
        for m in rx.finditer(text):
            gd = m.groupdict()
            v = float(gd["value"])
            unit = gd.get("unit") or ("s" if kind == "time" else "")
            if kind == "time":
                v, unit = to_seconds(v, unit), "s"
            elif kind == "size":
                v, unit = to_bytes(v, unit), "B"
            out.append(Record(metric, v, unit, (gd.get("label") or "").strip(),
                              text.count("\n", 0, m.start()) + 1, m.group(0).strip()))
        return out

    register_parser(name, description, sniff)(fn)
    return fn


def _lineno(text: str, pos: int) -> int:
    return text.count("\n", 0, pos) + 1


# ---------------------------------------------------------------- generic
_GENERIC = re.compile(
    rf"^(?P<label>[^\n:=]*?)\b(?:time|elapsed|took|duration|runtime|latency)\b\s*(?:\([^)]*\))?\s*[:=]?\s*(?P<value>{NUM})\s*(?P<unit>{TU})\b",
    re.I | re.M,
)
_RESULT_KV = re.compile(r"^RESULT\b(?P<body>.*)$", re.M)


@register_parser("generic", "time: X s / elapsed = X ms / took X sec; RESULT k=v lines")
def parse_generic(text: str) -> list[Record]:
    out = []
    for m in _GENERIC.finditer(text):
        out.append(Record("time", to_seconds(float(m["value"]), m["unit"]), "s",
                          m["label"].strip(" \t-:>"), _lineno(text, m.start()), m.group(0).strip()))
    for m in _RESULT_KV.finditer(text):
        kv = dict(re.findall(r"(\w+)=(\S+)", m["body"]))
        label = kv.pop("name", kv.pop("label", ""))
        for k, v in kv.items():
            tm = re.fullmatch(rf"({NUM})({TU})?", v)
            if not tm:
                if k in ("status", "check", "verdict"):
                    out.append(Record(k, v, "", label, _lineno(text, m.start()), m.group(0)))
                continue
            val, unit = float(tm.group(1)), tm.group(2)
            if unit:
                out.append(Record(k, to_seconds(val, unit), "s", label, _lineno(text, m.start()), m.group(0)))
            else:
                out.append(Record(k, val, "", label, _lineno(text, m.start()), m.group(0)))
    return out


# ---------------------------------------------------------------- criterion (Rust)
_CRIT = re.compile(
    rf"^(?P<label>\S[^\n]*?)?\s*\n?\s*time:\s+\[(?P<lo>{NUM})\s*(?P<ulo>\S+)\s+(?P<mid>{NUM})\s*(?P<umid>\S+)\s+(?P<hi>{NUM})\s*(?P<uhi>[^\]\s]+)\s*\]",
    re.M,
)


@register_parser("criterion", "Rust criterion: time: [lo mid hi]; reports mid (point estimate) plus lo/hi",
                 sniff=r"time:\s+\[")
def parse_criterion(text: str) -> list[Record]:
    out = []
    for m in _CRIT.finditer(text):
        label = (m["label"] or "").strip()
        ln = _lineno(text, m.start("lo"))
        out.append(Record("time", to_seconds(float(m["mid"]), m["umid"]), "s", label, ln, m.group(0).strip()))
        out.append(Record("time_lo", to_seconds(float(m["lo"]), m["ulo"]), "s", label, ln))
        out.append(Record("time_hi", to_seconds(float(m["hi"]), m["uhi"]), "s", label, ln))
    return out


# ---------------------------------------------------------------- go test -bench (Lattigo, gnark)
_GOB = re.compile(rf"^(?P<label>Benchmark\S+?)(?:-\d+)?\s+(?P<iters>\d+)\s+(?P<value>{NUM})\s+ns/op(?P<rest>.*)$", re.M)


@register_parser("gobench", "go test -bench: BenchmarkX-8  N  T ns/op [B/op allocs/op]", sniff=r"^Benchmark\S+\s+\d+\s+\S+\s+ns/op")
def parse_gobench(text: str) -> list[Record]:
    out = []
    for m in _GOB.finditer(text):
        ln = _lineno(text, m.start())
        out.append(Record("time", float(m["value"]) * 1e-9, "s", m["label"], ln, m.group(0).strip()))
        bm = re.search(rf"({NUM})\s+B/op", m["rest"])
        if bm:
            out.append(Record("alloc", float(bm.group(1)), "B", m["label"], ln))
    return out


# ---------------------------------------------------------------- google benchmark
_GB = re.compile(rf"^(?P<label>BM_\S+|\S+/\S+)\s+(?P<wall>{NUM})\s+(?P<uw>ns|us|ms|s)\s+(?P<cpu>{NUM})\s+(?P<uc>ns|us|ms|s)\s+(?P<iters>\d+)", re.M)


@register_parser("gbench", "Google Benchmark console: name  Time unit  CPU unit  Iterations", sniff=r"^-{20,}\s*\n?Benchmark\s+Time\s+CPU")
def parse_gbench(text: str) -> list[Record]:
    out = []
    for m in _GB.finditer(text):
        ln = _lineno(text, m.start())
        out.append(Record("time", to_seconds(float(m["wall"]), m["uw"]), "s", m["label"], ln, m.group(0).strip()))
        out.append(Record("cpu_time", to_seconds(float(m["cpu"]), m["uc"]), "s", m["label"], ln))
    return out


# ---------------------------------------------------------------- HElib timers
_HELIB = re.compile(rf"^\s*(?P<label>[A-Za-z_][\w:<>~]*)\s*:\s*(?P<total>{NUM})\s*/\s*(?P<count>\d+)\s*=\s*(?P<avg>{NUM})", re.M)


@register_parser("helib", "HElib printAllTimers: name: total / count = avg  (seconds)", sniff=r":\s*\S+\s*/\s*\d+\s*=\s*\S+\s+\[")
def parse_helib(text: str) -> list[Record]:
    out = []
    for m in _HELIB.finditer(text):
        ln = _lineno(text, m.start())
        out.append(Record("time_total", float(m["total"]), "s", m["label"], ln, m.group(0).strip()))
        out.append(Record("time", float(m["avg"]), "s", m["label"], ln))
        out.append(Record("count", float(m["count"]), "", m["label"], ln))
    return out


# ---------------------------------------------------------------- OpenFHE example style
_OFHE = re.compile(rf"^(?P<label>[^\n:]*?)\s*(?:time|took)\s*(?:\[\s*(?P<bunit>[a-zµμ]+)\s*\])?\s*[:=]?\s*(?P<value>{NUM})\s*(?P<unit>{TU})?\b", re.M | re.I)


@register_parser("openfhe", "OpenFHE examples: '<Label> time: 12.3 ms', 'Bootstrapping time [ms]: 123'")
def parse_openfhe(text: str) -> list[Record]:
    out = []
    for m in _OFHE.finditer(text):
        unit = m["unit"] or m["bunit"]
        if not unit:
            continue
        out.append(Record("time", to_seconds(float(m["value"]), unit), "s", m["label"].strip(" -:"), _lineno(text, m.start()), m.group(0).strip()))
    return out


# ---------------------------------------------------------------- lattice-estimator
_LE = re.compile(rf"^\s*(?P<label>[\w\-]+)\s*::\s*rop:\s*[≈~]?\s*2\^(?P<value>{NUM})(?P<rest>[^\n]*)$", re.M)
_BETA = re.compile(r"(?:β|beta):\s*(\d+)")


@register_parser("lattice-estimator", "LWE.estimate output lines 'attack :: rop: ≈2^X, ... β: B'; value = log2(rop) bits", sniff=r"::\s*rop:")
def parse_lattice_estimator(text: str) -> list[Record]:
    out = []
    for m in _LE.finditer(text):
        ln = _lineno(text, m.start())
        out.append(Record("rop_bits", float(m["value"]), "bits", m["label"], ln, m.group(0).strip()))
        b = _BETA.search(m["rest"])
        if b:
            out.append(Record("beta", float(b.group(1)), "", m["label"], ln))
    if out:
        best = min((r for r in out if r.metric == "rop_bits"), key=lambda r: r.value)
        out.append(Record("security_bits", best.value, "bits", f"min:{best.label}", best.line))
    return out


# ---------------------------------------------------------------- SAT solvers
_SAT_T = re.compile(
    rf"^c\s+(?:total process time since initialization|Total time(?: \(this thread\))?|process-time|total real time since initialization)\s*:?\s*(?P<value>{NUM})\s*(?P<unit>seconds|s)?",
    re.M | re.I,
)
_SAT_S = re.compile(r"^s\s+(SATISFIABLE|UNSATISFIABLE|UNKNOWN)\s*$", re.M)


@register_parser("sat", "CaDiCaL/CryptoMiniSat/kissat 'c total process time ...' + 's SATISFIABLE'", sniff=r"^s\s+(?:UN)?SATISFIABLE")
def parse_sat(text: str) -> list[Record]:
    out = [Record("time", float(m["value"]), "s", "solver", _lineno(text, m.start()), m.group(0).strip()) for m in _SAT_T.finditer(text)]
    for m in _SAT_S.finditer(text):
        out.append(Record("sat_status", m.group(1), "", "solver", _lineno(text, m.start()), m.group(0).strip()))
    return out


# ---------------------------------------------------------------- MP-SPDZ
_MPS_T = re.compile(rf"^Time\s*=\s*(?P<value>{NUM})\s*seconds", re.M)
_MPS_D = re.compile(rf"^Data sent\s*=\s*(?P<value>{NUM})\s*(?P<unit>[KMG]?B)(?:\s*in\s*~?(?P<rounds>\d+)\s*rounds)?", re.M)
_MPS_G = re.compile(rf"^Global data sent\s*=\s*(?P<value>{NUM})\s*(?P<unit>[KMG]?B)", re.M)


@register_parser("mpspdz", "MP-SPDZ: Time = X seconds; Data sent = X MB in ~R rounds; Global data sent", sniff=r"^Data sent\s*=")
def parse_mpspdz(text: str) -> list[Record]:
    out = []
    for m in _MPS_T.finditer(text):
        out.append(Record("time", float(m["value"]), "s", "party", _lineno(text, m.start()), m.group(0).strip()))
    for m in _MPS_D.finditer(text):
        ln = _lineno(text, m.start())
        out.append(Record("comm", to_bytes(float(m["value"]), m["unit"]), "B", "party", ln, m.group(0).strip()))
        if m["rounds"]:
            out.append(Record("rounds", float(m["rounds"]), "", "party", ln))
    for m in _MPS_G.finditer(text):
        out.append(Record("comm_global", to_bytes(float(m["value"]), m["unit"]), "B", "all", _lineno(text, m.start()), m.group(0).strip()))
    return out


# ---------------------------------------------------------------- GNU time -v
_GT_W = re.compile(r"Elapsed \(wall clock\) time \(h:mm:ss or m:ss\):\s*(?P<value>[\d:.]+)")
_GT_M = re.compile(r"Maximum resident set size \(kbytes\):\s*(?P<value>\d+)")


@register_parser("gnu-time", "/usr/bin/time -v wall clock + max RSS", sniff=r"Maximum resident set size")
def parse_gnu_time(text: str) -> list[Record]:
    out = []
    for m in _GT_W.finditer(text):
        parts = [float(p) for p in m["value"].split(":")]
        secs = 0.0
        for p in parts:
            secs = secs * 60 + p
        out.append(Record("time", secs, "s", "wall", _lineno(text, m.start()), m.group(0).strip()))
    for m in _GT_M.finditer(text):
        out.append(Record("max_rss", float(m["value"]) * 1024, "B", "process", _lineno(text, m.start()), m.group(0).strip()))
    return out


# ---------------------------------------------------------------- dispatch
def detect(text: str) -> list[str]:
    """Return names of parsers whose sniff pattern matches ``text`` (most specific first)."""
    hits = [p.name for p in REGISTRY.values() if p.sniff is not None and p.sniff.search(text)]
    return hits or ["generic"]


def parse_text(text: str, parser: str | Iterable[str] = "auto") -> list[Record]:
    names = detect(text) if parser == "auto" else ([parser] if isinstance(parser, str) else list(parser))
    out: list[Record] = []
    for n in names:
        if n not in REGISTRY:
            raise KeyError(f"unknown parser {n!r}; known: {sorted(REGISTRY)}")
        out.extend(REGISTRY[n].fn(text))
    return out


def parse_file(path: str, parser: str = "auto") -> list[Record]:
    with open(path, encoding="utf-8", errors="replace") as f:
        return parse_text(f.read(), parser)


def values(records: Iterable[Record], metric: str = "time", label: str | None = None) -> list[float]:
    return [float(r.value) for r in records if r.metric == metric and (label is None or r.label == label)]


if __name__ == "__main__":
    demo = "keygen time: 12.5 ms\nusvp :: rop: ≈2^131.2, red: ≈2^131.2, δ: 1.0040, β: 385, d: 1900, tag: usvp\n"
    for r in parse_text(demo, ["generic", "lattice-estimator"]):
        print(r)
