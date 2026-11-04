import asyncio
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import time

import pytest
from mcp import Client, StdioServerParameters

from cra_core.toolkit import init_project, toolkit_root
from cra_mcp.server import build_server, export, tool_schemas

CASE = os.path.join(toolkit_root(), "case-study", "toy-mvpbs")


def run(coro):
    return asyncio.run(coro)


def payload(res):
    """Structured result of a tool call (fall back to JSON text)."""
    if getattr(res, "structured_content", None):
        sc = res.structured_content
        return sc.get("result", sc) if isinstance(sc, dict) else sc
    return json.loads(res.content[0].text)


@pytest.fixture
def proj(tmp_path):
    d = str(tmp_path / "p")
    init_project(d)
    return d


# ----------------------------------------------------------------- schema portability
@pytest.mark.parametrize("profile", ["core", "full", "remote"])
def test_tool_schemas_are_portable(profile):
    tools = tool_schemas(CASE, profile)
    names = [t["name"] for t in tools]
    assert len(names) == len(set(names))
    if profile == "core":
        assert len(tools) <= 15                                  # small default for weaker models / tool caps
    for t in tools:
        assert re.fullmatch(r"[a-z][a-z0-9_]{0,31}", t["name"]), t["name"]   # mcp__cra__<name> <= 64 chars
        s = json.dumps(t["inputSchema"])
        for bad in ('"anyOf"', '"oneOf"', '"allOf"', '"$ref"', '"$defs"', '"pattern"', '"format"'):
            assert bad not in s, (t["name"], bad)                 # Gemini / OpenAI-strict safe
        assert len(s) <= 5000, t["name"]                          # Codex tool_input_schema_max_bytes default
        assert all(re.fullmatch(r"[A-Za-z0-9_]{1,64}", p) for p in t["inputSchema"].get("properties", {}))
        a = t["annotations"]
        for k in ("readOnlyHint", "destructiveHint", "idempotentHint", "openWorldHint"):
            assert k in a, (t["name"], k)                         # ChatGPT / claude.ai need explicit hints
        assert 20 <= len(t["description"]) <= 1024


def test_openai_strict_export():
    for f in export("openai", CASE, "full"):
        fn = f["function"]
        p = fn["parameters"]
        assert re.fullmatch(r"[a-zA-Z0-9_-]{1,64}", fn["name"])
        assert p["additionalProperties"] is False and set(p["required"]) == set(p["properties"])
        assert all("default" not in v for v in p["properties"].values())
    g = export("gemini", CASE, "core")[0]["functionDeclarations"]
    assert "additionalProperties" not in json.dumps(g)
    assert export("anthropic", CASE, "core")[0]["input_schema"]["type"] == "object"


# ----------------------------------------------------------------- in-memory protocol round trip
def test_full_workflow_over_mcp(proj):
    async def go():
        async with Client(build_server(proj, "full", actor="tester")) as c:
            r = payload(await c.call_tool("cra_resume", {}))
            assert r["ok"] and r["data"]["phase"] == "P0" and r["data"]["next_tasks"]
            r = payload(await c.call_tool("claim_register", {"claim": "For all n <= 64 the toy needs <= n/2 rotations",
                                                             "proposer": "idea-miner", "kill": "one n with more"}))
            assert r["ok"] and r["data"]["id"] == "C1"
            r = payload(await c.call_tool("claim_verdict", {"claim_id": "C1", "status": "survived", "evidence": "tried"}))
            assert not r["ok"] and "refs" in r["violations"][0]          # refused, readable
            r = payload(await c.call_tool("file_write", {"path": "CLAIMS.md", "content": "x"}))
            assert not r["ok"]                                            # ledgers only via typed tools
            r = payload(await c.call_tool("file_write", {"path": "../escape.txt", "content": "x"}))
            assert not r["ok"]
            r = payload(await c.call_tool("file_write", {"path": "results/a/run.log", "content": "2.0x\n"}))
            assert r["ok"]
            r = payload(await c.call_tool("evidence_add", {"printed": "2.0x", "command": "python3 bench.py",
                                                           "log": "results/a/run.log"}))
            assert r["ok"] and r["data"]["id"] == "E1"
            r = payload(await c.call_tool("claim_verdict", {"claim_id": "C1", "status": "survived",
                                                            "evidence": "n=1..64, falsify/C1/x.log", "refs": "E1"}))
            assert r["ok"] and r["data"]["status"] == "survived"
            r = payload(await c.call_tool("file_write", {"path": "paper/sections/x.tex",
                                                         "content": "We are 2.0x faster.\\claimref{C1}\\claimref{C2}\n"}))
            assert any("C2" in v for v in r["violations"])                # reported right after the write
            r = payload(await c.call_tool("phase_advance", {"to_phase": "P1", "rationale": "try to skip the gate"}))
            assert not r["ok"] and "does not pass" in r["violations"][0]
            for item in ("falsifiable", "venue", "in-scope", "budget", "kill"):
                assert payload(await c.call_tool("gate_tick", {"phase": "P0", "item": item}))["ok"]
            r = payload(await c.call_tool("phase_advance", {"to_phase": "P1", "rationale": "P0 gate passes"}))
            assert r["ok"] and r["data"]["to"] == "P1"
            r = payload(await c.call_tool("role_card", {"agent": "falsifier"}))
            assert "Mission" in r["data"]["text"]
            r = payload(await c.call_tool("skill_guide", {"skill": "falsify"}))
            assert "verdict" in r["data"]["text"]
            prompts = [p.name for p in (await c.list_prompts()).prompts]
            assert "cra-status" in prompts and "cra-falsify" in prompts
            res = await c.read_resource("cra://project/CLAIMS.md")
            assert "C1" in res.contents[0].text
    run(go())
    ev = [json.loads(l)["action"] for l in open(os.path.join(proj, ".cra", "events.jsonl"))]
    assert "phase.advance" in ev and "claim.verdict" in ev


def test_remote_profile_search_fetch():
    async def go():
        async with Client(build_server(CASE, "remote")) as c:
            r = payload(await c.call_tool("search", {"query": "multi-value PBS"}))
            assert r["results"] and {"id", "title", "url"} <= set(r["results"][0])
            f = payload(await c.call_tool("fetch", {"id": r["results"][0]["id"]}))
            assert f["text"] and f["url"].startswith("cra://project/")
            r = payload(await c.call_tool("gate_check", {"phase": "P8"}))
            assert r["ok"] and r["data"]["passes"]
    run(go())


# ----------------------------------------------------------------- real transports
def test_stdio_transport(proj):
    exe = shutil.which("cra-mcp")
    params = StdioServerParameters(command=exe or sys.executable,
                                   args=(["--project", proj] if exe else ["-m", "cra_mcp.server", "--project", proj]))

    async def go():
        async with Client(params) as c:
            names = [t.name for t in (await c.list_tools()).tools]
            assert "cra_resume" in names and len(names) == 15
            assert payload(await c.call_tool("cra_resume", {}))["data"]["phase"] == "P0"
    run(go())


def _post(url, body, headers):
    import urllib.error
    import urllib.request
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers=headers, method="POST")
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))   # never via a proxy
    try:
        with opener.open(req, timeout=10) as r:
            return r.status, r.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()


def _free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


@pytest.mark.parametrize("mode", ["bearer", "secret-path"])
def test_http_transport_requires_auth(proj, mode):
    port = _free_port()
    env = dict(os.environ, CRA_MCP_TOKEN="s3cret" if mode == "bearer" else "")
    args = [sys.executable, "-m", "cra_mcp.server", "--project", proj, "--http", "--port", str(port)]
    if mode == "secret-path":
        args.append("--secret-path")
    p = subprocess.Popen(args, env=env, stderr=subprocess.PIPE, text=True)
    try:
        url = None
        t0 = time.time()
        while time.time() - t0 < 20:
            line = p.stderr.readline()
            m = re.search(r"local URL : (\S+)", line)
            if m:
                url = m.group(1)
                break
        assert url, "server did not start"
        for _ in range(50):
            try:
                socket.create_connection(("127.0.0.1", port), timeout=0.2).close()
                break
            except OSError:
                time.sleep(0.1)
        hdr = {"Accept": "application/json, text/event-stream", "Content-Type": "application/json"}
        body = {"jsonrpc": "2.0", "id": 1, "method": "initialize",
                "params": {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "t", "version": "0"}}}
        if mode == "bearer":
            assert _post(url, body, hdr)[0] == 401
            code, text = _post(url, body, hdr | {"Authorization": "Bearer s3cret"})
        else:
            assert re.search(r"/mcp/[\w-]{20,}$", url)
            assert _post(f"http://127.0.0.1:{port}/mcp", body, hdr)[0] in (404, 405, 307)
            code, text = _post(url, body, hdr)
        assert code == 200 and "cra" in text
    finally:
        p.terminate()
        p.wait(timeout=10)


def test_refuses_public_bind_without_auth(proj):
    r = subprocess.run([sys.executable, "-m", "cra_mcp.server", "--project", proj, "--http", "--host", "0.0.0.0"],
                       env=dict(os.environ, CRA_MCP_TOKEN=""), capture_output=True, text=True, timeout=30)
    assert r.returncode == 2 and "refusing" in r.stderr


def _start_http(proj, *extra, env_token=""):
    port = _free_port()
    args = [sys.executable, "-m", "cra_mcp.server", "--project", proj, "--http", "--port", str(port), *extra]
    p = subprocess.Popen(args, env=dict(os.environ, CRA_MCP_TOKEN=env_token), stderr=subprocess.PIPE, text=True)
    lines, t0 = [], time.time()
    while time.time() - t0 < 20:
        line = p.stderr.readline()
        lines.append(line)
        if "local URL" in line:
            break
    for _ in range(50):
        try:
            socket.create_connection(("127.0.0.1", port), timeout=0.2).close()
            break
        except OSError:
            time.sleep(0.1)
    # read the rest of the banner without blocking forever
    t1 = time.time()
    while time.time() - t1 < 1.5:
        import select
        if select.select([p.stderr], [], [], 0.2)[0]:
            lines.append(p.stderr.readline())
    return p, port, "".join(lines)


def test_chatgpt_tunnel_setup(proj):
    """Simulate ChatGPT behind a cloudflared quick tunnel: public Host header, ChatGPT Origin, secret path."""
    pub = "https://abc-def.trycloudflare.com"
    p, port, banner = _start_http(proj, "--profile", "remote", "--secret-path", "--public-url", pub)
    try:
        m = re.search(r">>> paste this as the MCP server URL: (https://abc-def\.trycloudflare\.com(/mcp/[\w-]+))", banner)
        assert m, banner
        path = m.group(2)
        local = f"http://127.0.0.1:{port}{path}"
        hdr = {"Accept": "application/json, text/event-stream", "Content-Type": "application/json",
               "Host": "abc-def.trycloudflare.com", "Origin": "https://chatgpt.com"}
        body = {"jsonrpc": "2.0", "id": 1, "method": "initialize",
                "params": {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "openai-mcp", "version": "1"}}}
        code, text = _post(local, body, hdr)
        assert code == 200 and '"cra"' in text, (code, text)
        assert _post(local, body, hdr | {"Host": "evil.example"})[0] in (400, 403, 421)       # DNS-rebinding guard
        assert _post(local, body, hdr | {"Origin": "https://evil.example"})[0] in (400, 403)
        assert _post(f"http://127.0.0.1:{port}/mcp", body, hdr)[0] == 404                   # secret required
    finally:
        p.terminate()
        p.wait(timeout=10)
    # the secret survives a restart, so the ChatGPT app URL stays valid
    p2, _, banner2 = _start_http(proj, "--profile", "remote", "--secret-path", "--public-url", pub)
    p2.terminate()
    p2.wait(timeout=10)
    assert path in banner2
    assert "mcp-secret" in open(os.path.join(proj, ".cra", ".gitignore")).read()
    assert oct(os.stat(os.path.join(proj, ".cra", "mcp-secret")).st_mode & 0o777) == "0o600"


def test_http_client_session_calls_tools(proj):
    """A real MCP client over Streamable HTTP (as a remote host would use it)."""
    p, port, _ = _start_http(proj, "--profile", "remote", env_token="")
    try:
        async def go():
            async with Client(f"http://127.0.0.1:{port}/mcp") as c:
                names = [t.name for t in (await c.list_tools()).tools]
                assert {"search", "fetch", "file_write", "cra_resume"} <= set(names) and len(names) == 21
                r = payload(await c.call_tool("claim_register", {"claim": "For every toy set the gate check terminates",
                                                                 "proposer": "pi-orchestrator", "kill": "one set loops"}))
                assert r["ok"] and r["data"]["id"] == "C1"
        asyncio.run(go())
    finally:
        p.terminate()
        p.wait(timeout=10)
