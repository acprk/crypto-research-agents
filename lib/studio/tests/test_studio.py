import json
import os
import time

import pytest
from starlette.testclient import TestClient

from cra_core import Project
from cra_studio import config
from cra_studio.app import create_app
from cra_studio.runner import Runner

TOKEN = "test-token-123456789"


class Scripted:
    model = "scripted"

    def __init__(self, turns):
        self.turns = list(turns)

    def complete(self, messages, tools, temperature):
        return {"choices": [{"message": self.turns.pop(0)}]}


def call(i, name, args):
    return {"id": f"c{i}", "type": "function", "function": {"name": name, "arguments": json.dumps(args)}}


@pytest.fixture
def env(tmp_path, monkeypatch):
    monkeypatch.setenv("CRA_CONFIG_DIR", str(tmp_path / "cfg"))
    for k in ("OPENAI_API_KEY", "OPENAI_BASE_URL", "CRA_MODEL"):
        monkeypatch.delenv(k, raising=False)
    runner = Runner()
    c = TestClient(create_app(TOKEN, runner), base_url="http://127.0.0.1:8770")
    c.headers["X-CRA-Token"] = TOKEN
    return c, runner, str(tmp_path / "proj")


def test_guard_token_and_host(env):
    c, _, _ = env
    assert c.get("/").status_code == 200 and "CRA Studio" in c.get("/").text
    assert c.get("/api/config", headers={"X-CRA-Token": "wrong"}).status_code == 401
    assert c.get("/api/config", headers={"Host": "evil.example"}).status_code == 421
    assert c.get("/api/config").json()["ok"]


def test_config_key_is_write_only_and_private(env, monkeypatch):
    c, _, _ = env
    r = c.post("/api/config", json={"provider": {"preset": "openai", "base_url": "https://relay.example/v1",
                                                 "api_key": "sk-secret-abcdef123456", "model": "m1"}})
    pub = r.json()["config"]["provider"]
    assert "api_key" not in pub and pub["api_key_set"] and "secret" not in json.dumps(r.json())
    assert pub["effective_base_url"] == "https://relay.example/v1"
    assert oct(os.stat(config.path()).st_mode & 0o777) == "0o600"
    c.post("/api/config", json={"provider": {"model": "m2"}})          # empty key keeps the old one
    assert config.load()["provider"]["api_key"] == "sk-secret-abcdef123456"
    c.post("/api/config", json={"provider": {"clear_api_key": True}})
    assert config.load()["provider"]["api_key"] == ""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-from-env")              # env fills, but is never saved
    assert config.load()["provider"]["api_key"] == "sk-from-env"
    c.post("/api/config", json={"max_steps": 5})
    assert "sk-from-env" not in open(config.path()).read()
    assert c.post("/api/config", json={"approve": "bogus"}).status_code == 400


def test_projects_status_ledgers_connect(env):
    c, _, proj = env
    assert c.post("/api/projects/open", json={"path": proj}).status_code == 400     # missing, no create
    r = c.post("/api/projects/open", json={"path": proj, "create": True}).json()
    assert r["ok"] and "STATE.md" in r["created"]
    assert c.get("/api/projects").json()["recent"] == [proj]
    s = c.get("/api/status", params={"project": proj}).json()["status"]
    assert s["phase"] == "P0" and s["next_tasks"]
    Project(proj).add_claim("For all toy sets one rotation suffices", "idea-miner")
    rows = c.get("/api/ledger/claims", params={"project": proj}).json()["rows"]
    assert rows[0]["id"] == "C1" and rows[0]["status"] == "open"
    assert "phase" in c.get("/api/file", params={"project": proj, "path": "STATE.md"}).json()["text"].lower()
    assert c.get("/api/file", params={"project": proj, "path": "../../etc/passwd"}).status_code == 400
    assert "claude-code" in c.get("/api/connect", params={"project": proj}).json()["hosts"]
    prev = c.get("/api/connect", params={"project": proj, "host": "cursor"}).json()["lines"]
    assert prev and not os.path.exists(os.path.join(proj, ".cursor"))                # preview writes nothing
    c.get("/api/connect", params={"project": proj, "host": "cursor", "apply": "1"})
    assert os.path.exists(os.path.join(proj, ".cursor", "mcp.json"))
    assert c.get("/api/gate", params={"project": proj}).json()["phase"] == "P0"


def test_run_requires_model_settings(env):
    c, _, proj = env
    c.post("/api/projects/open", json={"path": proj, "create": True})
    r = c.post("/api/run", json={"project": proj, "task": "go"})
    assert r.status_code == 400 and "Settings" in r.json()["error"]


def wait(c, rid, until, timeout=20, after=0):
    t0, seen = time.time(), []
    while time.time() - t0 < timeout:
        j = c.get(f"/api/run/{rid}", params={"after": after + len(seen)}).json()
        seen += j["events"]
        if until(j, seen):
            return j, seen
        time.sleep(0.05)
    raise AssertionError(f"timeout; events={seen}")


def test_agent_run_with_ui_approval(env):
    c, runner, proj = env
    c.post("/api/projects/open", json={"path": proj, "create": True})
    client = Scripted([
        {"role": "assistant", "content": None, "tool_calls": [call(1, "cra_resume", {})]},
        {"role": "assistant", "content": "", "tool_calls": [
            call(2, "claim_register", {"claim": "For all toy sets one rotation suffices", "proposer": "idea-miner",
                                       "kill": "a set needing two"}),
            call(3, "file_write", {"path": "notes/idea.md", "content": "# idea\n"})]},
        {"role": "assistant", "content": "Registered C1 and wrote a note."},
    ])
    run = runner.start(proj, "go", client=client)
    j, seen = wait(c, run.id, lambda j, s: j["status"] == "waiting_approval")
    assert j["pending"]["name"] == "file_write"
    assert c.post(f"/api/run/{run.id}/decide", json={"allow": True}).json()["ok"]
    j, seen2 = wait(c, run.id, lambda j, s: j["status"] == "done", after=len(seen))
    types = [e["type"] for e in seen + seen2]
    assert types.count("tool_call") == 3 and "approval" in types and types[-1] == "done"
    assert os.path.exists(os.path.join(proj, "notes", "idea.md"))
    assert [x.id for x in Project(proj).claims()] == ["C1"]
    # conversation continues in the same project
    run2 = runner.start(proj, "and now?", client=Scripted([{"role": "assistant", "content": "nothing else"}]))
    wait(c, run2.id, lambda j, s: j["status"] == "done")
    assert len(runner.history[proj]) > 6


def test_agent_run_deny_and_stop(env):
    c, runner, proj = env
    c.post("/api/projects/open", json={"path": proj, "create": True})
    client = Scripted([
        {"role": "assistant", "content": "", "tool_calls": [call(1, "phase_advance", {"to_phase": "P1", "rationale": "go go go go"})]},
        {"role": "assistant", "content": "", "tool_calls": [call(2, "cra_resume", {})]},
        {"role": "assistant", "content": "unreachable"},
    ])
    run = runner.start(proj, "go", client=client)
    wait(c, run.id, lambda j, s: j["status"] == "waiting_approval")
    c.post(f"/api/run/{run.id}/decide", json={"allow": False})
    j, seen = wait(c, run.id, lambda j, s: any(e["type"] == "tool_result" for e in s))  # from event 0
    assert "declined" in next(e for e in seen if e["type"] == "tool_result")["result"]
    c.post(f"/api/run/{run.id}/stop")
    wait(c, run.id, lambda j, s: j["status"] in ("stopped", "done"))
    assert Project(proj).phase() == "P0"


def test_api_errors_surface_in_events(env):
    c, runner, proj = env
    c.post("/api/projects/open", json={"path": proj, "create": True})

    class Broken:
        model = "x"

        def complete(self, *a):
            raise SystemExit("API error 401 from https://relay/v1/chat/completions: bad key")

    run = runner.start(proj, "go", client=Broken())
    j, seen = wait(c, run.id, lambda j, s: j["status"] == "error")
    assert "401" in seen[-1]["text"]


def test_main_dispatch(capsys, tmp_path):
    from cra_studio.main import main
    from cra_core.toolkit import init_project
    p = str(tmp_path / "p")
    init_project(p)
    assert main(["cra", "-p", p, "claim", "add", "For all toy sets the gate check terminates", "--proposer", "pi"]) == 0
    assert main(["mcp", "--project", p, "--list-tools"]) == 0
    assert '"cra_resume"' in capsys.readouterr().out
    script = tmp_path / "s.py"
    script.write_text("import sys; print('ran', sys.argv[1:]); sys.exit(3)")
    assert main(["--run-script", str(script), "a", "b"]) == 3
    assert "ran ['a', 'b']" in capsys.readouterr().out
