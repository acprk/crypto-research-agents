import json
import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from cra_core import Project
from cra_core.toolkit import init_project, toolkit_root
from cra_mcp.adapter import FORMATS, ToolBox, convert
from cra_mcp.agent import ChatClient, run
from cra_mcp.server import tool_schemas

CASE = os.path.join(toolkit_root(), "case-study", "toy-mvpbs")


@pytest.fixture
def proj(tmp_path):
    d = str(tmp_path / "p")
    init_project(d)
    return d


def _walk(schema):
    yield schema
    for v in schema.get("properties", {}).values():
        yield from _walk(v)
    if isinstance(schema.get("items"), dict):
        yield from _walk(schema["items"])


@pytest.mark.parametrize("profile", ["core", "full", "remote"])
def test_openai_strict_rules(profile):
    tools = tool_schemas(CASE, profile)
    for fmt in ("openai", "openai-responses"):
        for t in convert(tools, fmt):
            fn = t["function"] if fmt == "openai" else t
            assert fn["strict"] is True and len(fn["description"]) <= 1024
            p = fn["parameters"]
            assert p["additionalProperties"] is False and set(p["required"]) == set(p["properties"])
            for s in _walk(p):
                assert "default" not in s and "title" not in s
                if "enum" in s and isinstance(s.get("type"), list) and "null" in s["type"]:
                    assert None in s["enum"]                  # nullable enum must list null


def test_responses_format_is_flat():
    t = convert(tool_schemas(CASE, "core"), "openai-responses")[0]
    assert t["type"] == "function" and "name" in t and "function" not in t


def test_gemini_and_compat_formats():
    g = convert(tool_schemas(CASE, "full"), "gemini")[0]["functionDeclarations"]
    for d in g:
        for s in _walk(d["parameters"]):
            assert not ({"default", "additionalProperties", "title", "anyOf", "$ref"} & set(s))
    c = convert(tool_schemas(CASE, "core"), "openai-compat")
    assert all("strict" not in t["function"] for t in c)
    a = convert(tool_schemas(CASE, "core"), "anthropic")
    assert all(t["input_schema"]["type"] == "object" for t in a)
    with pytest.raises(ValueError):
        convert([], "nope")
    assert set(FORMATS) == {"openai", "openai-responses", "openai-compat", "anthropic", "gemini"}


def test_toolbox_calls_and_refusals(proj):
    box = ToolBox(proj, "core")
    r = json.loads(box.call("claim_register", json.dumps({"claim": "For all toy sets one rotation suffices",
                                                          "proposer": "idea-miner", "kill": "a set needing two",
                                                          "refs": None})))       # strict clients send null
    assert r["ok"] and r["data"]["id"] == "C1"
    assert not json.loads(box.call("claim_list", '{"status": "bogus"}'))["ok"]
    assert not json.loads(box.call("no_such_tool", "{}"))["ok"]
    assert not json.loads(box.call("claim_list", "{not json"))["ok"]
    assert box.is_destructive("phase_advance") and not box.is_write("cra_resume")


class ScriptedClient:
    """Plays back a fixed sequence of assistant messages (what an LLM would return)."""

    def __init__(self, turns):
        self.turns, self.seen = list(turns), []

    def complete(self, messages, tools, temperature):
        self.seen.append((json.loads(json.dumps(messages)), tools))
        return {"choices": [{"message": self.turns.pop(0)}]}


def _call(i, name, args):
    return {"id": f"call_{i}", "type": "function", "function": {"name": name, "arguments": json.dumps(args)}}


def test_agent_loop_drives_the_blackboard(proj):
    client = ScriptedClient([
        {"role": "assistant", "content": None, "reasoning_content": "think", "tool_calls": [_call(1, "cra_resume", {})]},
        {"role": "assistant", "content": "", "tool_calls": [
            _call(2, "claim_register", {"claim": "For all toy sets one rotation suffices", "proposer": "idea-miner",
                                        "kill": "a set needing two"}),
            _call(3, "phase_advance", {"to_phase": "P1", "rationale": "try to advance"})]},
        {"role": "assistant", "content": "Registered C1; P0 gate is not done yet."},
    ])
    asked = []
    msgs = run("go", ToolBox(proj), client, ask=lambda q: asked.append(q) or "n", log=lambda *a: None)
    assert [c.id for c in Project(proj).claims()] == ["C1"]
    assert Project(proj).phase() == "P0"                        # destructive call needed approval; declined
    assert len(asked) == 1 and "phase_advance" in asked[0]
    tool_msgs = [m for m in msgs if m["role"] == "tool"]
    assert [m["tool_call_id"] for m in tool_msgs] == ["call_1", "call_2", "call_3"]
    assert "declined" in tool_msgs[2]["content"]
    # second request echoes the first assistant turn incl. reasoning_content (DeepSeek / Kimi thinking mode)
    second_request = client.seen[1][0]
    assert second_request[2]["reasoning_content"] == "think" and second_request[2]["tool_calls"][0]["id"] == "call_1"
    assert msgs[-1]["content"].startswith("Registered C1")


def test_chat_client_wire_format(monkeypatch):
    """ChatClient against a local fake OpenAI-compatible server."""
    got = {}

    class H(BaseHTTPRequestHandler):
        def do_POST(self):
            got["path"] = self.path
            got["auth"] = self.headers.get("Authorization")
            got["body"] = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            out = json.dumps({"choices": [{"message": {"role": "assistant", "content": "hi"}}]}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(out)))
            self.end_headers()
            self.wfile.write(out)

        def log_message(self, *a):
            pass

    srv = HTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    monkeypatch.setenv("NO_PROXY", "127.0.0.1")
    monkeypatch.setenv("no_proxy", "127.0.0.1")
    try:
        c = ChatClient(f"http://127.0.0.1:{srv.server_port}/v1", "k123", "some-model")
        r = c.complete([{"role": "user", "content": "x"}], convert(tool_schemas(CASE, "core"), "openai-compat"), None)
    finally:
        srv.shutdown()
    assert r["choices"][0]["message"]["content"] == "hi"
    assert got["path"] == "/v1/chat/completions" and got["auth"] == "Bearer k123"
    b = got["body"]
    assert b["model"] == "some-model" and b["tool_choice"] == "auto" and len(b["tools"]) == 15
    assert "temperature" not in b                     # DeepSeek thinking mode rejects custom temperature
