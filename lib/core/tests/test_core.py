import glob
import json
import os
import shutil
import subprocess
import threading

import pytest

from cra_core import CraError, Document, Project, check_gate
from cra_core.cli import main as cra
from cra_core.gates import check_invariants
from cra_core.schema import CLAIM_HINTS, EVIDENCE_HINTS
from cra_core.toolkit import init_project, toolkit_root

ROOT = toolkit_root()
CASE = os.path.join(ROOT, "case-study", "toy-mvpbs")


@pytest.mark.parametrize("path", sorted(glob.glob(os.path.join(ROOT, "case-study", "**", "*.md"), recursive=True)
                                       + glob.glob(os.path.join(ROOT, "templates", "blackboard", "*.md"))))
def test_markdown_roundtrip_is_lossless(path):
    text = open(path, encoding="utf-8").read()
    assert Document(text).render() == text


def test_edit_touches_only_the_changed_row():
    text = "# T\n\nprose | not a table\n\n| ID | status | x |\n|---|---|---|\n| C1 |  open | a \\| b |\n| C2 | open | c |\n\ntail\n"
    doc = Document(text)
    t = doc.find(CLAIM_HINTS, ("id", "status"))
    assert t.value(t.rows[0], "id") == "C1"
    t.set(t.rows[1], "status", "refuted")
    out = doc.render()
    assert "| C1 |  open | a \\| b |" in out          # untouched row kept byte-for-byte
    assert "| C2 | refuted | c |" in out and out.endswith("tail\n")


def test_case_study_parses():
    p = Project(CASE)
    assert p.phase() == "P8"
    assert [c.id for c in p.claims()] == [f"C{i}" for i in range(1, 7)]
    assert {c.status for c in p.claims()} == {"survived", "weakened", "refuted"}
    assert len(p.evidence()) == 22


def test_case_study_gates_pass():
    for ph in ("P6", "P7", "P8"):
        res = check_gate(CASE, ph, "paper")
        assert not [m for s, m in res if s == "FAIL"], res
    assert not [m for s, m in check_invariants(CASE) if s == "FAIL"]


@pytest.fixture
def proj(tmp_path):
    d = tmp_path / "proj"
    init_project(str(d))
    return Project(str(d), actor="tester")


def test_init_project_passes_its_own_checks(proj):
    assert proj.phase() == "P0"
    assert proj.claims() == [] and proj.evidence() == []      # template examples are not table rows
    assert not [m for s, m in check_invariants(proj.root) if s == "FAIL"]
    res = check_gate(proj.root, "P0")
    assert any("unticked" in m for s, m in res if s == "FAIL")  # real P0 checklist, not "no gate section"


def test_claim_lifecycle_and_rules(proj):
    c1 = proj.add_claim("For all n <= 64 the method needs <= n/2 rotations", "idea-miner", kill="one n with more")
    c2 = proj.add_claim("The method is optimal among all linear schedules", "theorist")
    assert (c1, c2) == ("C1", "C2")
    with pytest.raises(CraError):
        proj.add_claim("short", "x")
    with pytest.raises(CraError, match="needs falsifier evidence"):
        proj.set_verdict(c1, "survived", "")
    with pytest.raises(CraError, match="refs"):
        proj.set_verdict(c1, "survived", "tried n=1..64")
    with pytest.raises(CraError, match="weakened wording"):
        proj.set_verdict(c1, "weakened", "n=63 needs 32", refs="E1")
    c = proj.set_verdict(c1, "weakened", "n=63 needs 32", refs="E1", weakened_wording="for n <= 62 ...")
    assert c.status == "weakened" and "Adopted weakened wording" in c.claim
    proj.set_verdict(c2, "refuted", "counterexample schedule in falsify/C2/x.log")
    with pytest.raises(CraError, match="DECISIONS"):
        proj.set_verdict(c2, "survived", "new proof", refs="THEORY T2")
    assert proj.set_verdict(c2, "survived", "new proof", refs="THEORY T2", decision="D-3").status == "survived"
    acts = [e["action"] for e in proj.events()]
    assert acts.count("claim.register") == 2 and acts.count("claim.verdict") == 3
    assert all(e["actor"] == "tester" for e in proj.events())


def test_evidence_rules_and_tamper_detection(proj):
    with pytest.raises(CraError, match="log"):
        proj.add_evidence("2.0x", "python3 bench.py", "")
    with pytest.raises(CraError, match="not found"):
        proj.add_evidence("2.0x", "python3 bench.py", "results/none.log")
    os.makedirs(proj.path("results/a"))
    open(proj.path("results/a/run.log"), "w").write("speedup 2.0x\n")
    e1 = proj.add_evidence("2.0x", "python3 bench.py", "results/a/run.log", meaning="speedup")
    e2 = proj.add_evidence("0.5", "derived: 1/E1", "-")
    assert (e1, e2) == ("E1", "E2")
    with pytest.raises(CraError, match="unknown E9"):
        proj.add_evidence("1", "derived: E9", "-")
    assert proj.check_evidence() == []
    open(proj.path("results/a/run.log"), "a").write("edited\n")
    assert any("changed since" in m for s, m in proj.check_evidence())


def test_paths_cannot_escape_project(proj):
    with pytest.raises(CraError):
        proj.path("../outside")


def test_paper_tags(proj):
    os.makedirs(proj.path("results/a"))
    open(proj.path("results/a/r.log"), "w").write("x")
    proj.add_evidence("2.0x", "bench", "results/a/r.log")
    cid = proj.add_claim("Our method is at least twice as fast at set T1", "idea-miner")
    open(proj.path("paper/sections/x.tex"), "w").write("We are 2.0x faster.\\claimref{%s}\\evid{E1}\n" % cid)
    fails = [m for s, m in check_invariants(proj.root) if s == "FAIL"]
    assert any("is 'open'" in m for m in fails)               # open claim cited in the paper
    proj.set_verdict(cid, "survived", "reran", refs="E1")
    assert not [m for s, m in check_invariants(proj.root) if s == "FAIL"]
    open(proj.path("paper/sections/x.tex"), "a").write("And 3.0x smaller.\\evid{E7}\n")
    fails = [m for s, m in check_invariants(proj.root) if s == "FAIL"]
    assert any("E7" in m for m in fails)


def test_concurrent_writers_get_distinct_ids(proj):
    ids, errs = [], []

    def worker(i):
        try:
            ids.append(Project(proj.root).add_claim(f"Claim number {i} holds for every toy parameter", "w"))
        except Exception as e:  # pragma: no cover
            errs.append(e)

    th = [threading.Thread(target=worker, args=(i,)) for i in range(12)]
    [t.start() for t in th]
    [t.join() for t in th]
    assert not errs and sorted(ids, key=lambda s: int(s[1:])) == [f"C{i}" for i in range(1, 13)]
    assert len(proj.claims()) == 12


def test_cli_roundtrip(proj, capsys):
    assert cra(["-p", proj.root, "claim", "add", "For every toy set the gate check terminates", "--proposer", "pi"]) == 0
    assert capsys.readouterr().out.strip() == "C1"
    assert cra(["-p", proj.root, "status", "--json"]) == 0
    s = json.loads(capsys.readouterr().out)
    assert s["phase"] == "P0" and s["claims"]["open"] == ["C1"]
    assert cra(["-p", proj.root, "gate", "P0"]) == 1
    assert cra(["-p", proj.root, "claim", "verdict", "C1", "survived", "--evidence", "x"]) == 2   # refused: no refs


@pytest.mark.skipif(shutil.which("git") is None, reason="git not installed")
def test_pre_commit_hook_blocks_bad_reference(proj, monkeypatch):
    env = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@example.invalid",
               GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@example.invalid")
    run = lambda *a: subprocess.run(a, cwd=proj.root, capture_output=True, text=True, env=env)
    run("git", "init", "-q")
    assert cra(["-p", proj.root, "hook", "install"]) == 0
    if shutil.which("cra") is None:
        pytest.skip("cra console script not on PATH")
    open(proj.path("paper/sections/x.tex"), "w").write("As shown.\\claimref{C9}\n")
    run("git", "add", "-A")
    assert run("git", "commit", "-qm", "bad").returncode != 0
    open(proj.path("paper/sections/x.tex"), "w").write("As shown.\n")
    run("git", "add", "-A")
    assert run("git", "commit", "-qm", "good").returncode == 0


def test_phase_advance_tick_waive_and_decisions(proj):
    with pytest.raises(CraError, match="does not pass"):
        proj.advance_phase("P1", "skip the scoping gate")
    with pytest.raises(CraError, match="skip"):
        proj.advance_phase("P3", "jump ahead three phases")
    for it in ("falsifiable", "venue", "in-scope", "budget"):
        proj.tick_gate_item("P0", it)
    with pytest.raises(CraError, match="DECISIONS id"):
        proj.tick_gate_item("P0", "kill", waive_reason="toy")
    with pytest.raises(CraError, match="matches 0"):
        proj.tick_gate_item("P0", "no such item")
    did = proj.add_decision("Waive the kill date: teaching toy", options="set / waive")
    assert did == "D-1"
    proj.tick_gate_item("P0", "kill", waive_reason="teaching toy", decision=did)
    r = proj.advance_phase("P1", "P0 gate passes")
    assert r == {"from": "P0", "to": "P1", "decision": "D-2"} and proj.phase() == "P1"
    state = proj.read("STATE.md")
    assert "## Gate P1" in state and "- **Phase:** P1 Literature" in state
    assert not [m for s, m in check_gate(proj.root, "P0") if s == "FAIL"]     # old gate kept as the log
    back = proj.advance_phase("P0", "thesis too vague (REVIEWS R0)")
    assert back["to"] == "P0" and proj.phase() == "P0"
    assert "D-3" in proj.read("DECISIONS.md")


def test_planner_puts_falsifier_first(proj):
    from cra_core.planner import next_actions
    proj.add_claim("For all toy sets the method needs one blind rotation", "idea-miner")
    acts = next_actions(proj)
    assert acts[0]["agent"] == "falsifier" and acts[0]["tool"] == "claim_verdict"
    assert all("do_not" in a and "id" in a for a in acts)
    assert any(a["agent"] == "pi-orchestrator" and "P0 gate item" in a["task"] for a in acts)
