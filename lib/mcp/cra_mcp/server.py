"""cra-mcp -- run the crypto-research-agents MCP server.

    cra-mcp --project ~/papers/my-paper                      # stdio (Claude Code, Codex, Cline, Cursor, ...)
    cra-mcp --project . --profile full                       # all tools
    cra-mcp --project . --http --port 8765                   # Streamable HTTP on 127.0.0.1:8765/mcp
    cra-mcp --project . --http --profile remote --secret-path --public-url https://abc.trycloudflare.com
                                                             # ChatGPT / claude.ai through a tunnel
    cra-mcp --list-tools [--profile core]                    # print the tool list (names + schemas)
    cra-mcp --export openai|anthropic|gemini                 # function-calling schemas for non-MCP hosts
    cra-mcp install --host <claude-code|codex|cline|gemini|cursor|vscode|chatgpt|...> --project <dir>
    cra-mcp doctor --project <dir>                           # check the installation

Project directory: --project, else $CRA_PROJECT, else the current directory.
Profiles: core (15 tools, default; best for smaller models), full (all local tools),
remote (core + file access + search/fetch, for hosts without a local filesystem).
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import secrets
import sys

from mcp.server.mcpserver import MCPServer
from mcp.types import ToolAnnotations

from . import __version__
from .tools import PROFILES, RULES, Context, build_tools, select

INSTRUCTIONS = (
    "cra = crypto-research-agents: a falsify-first pipeline for cryptography papers (phases P0-P8, "
    "blackboard files in the project). Call cra_resume first in every session; it returns the phase, "
    "gate status and the next tasks with the tool to call. " + RULES + " Use role_card(<agent>) to adopt a role "
    "and skill_guide(<skill>) for procedures."
)


def build_server(project: str, profile: str = "core", actor: str = "mcp") -> MCPServer:
    ctx = Context(project, actor=actor)
    srv = MCPServer(name="cra", title="crypto-research-agents", version=__version__, instructions=INSTRUCTIONS)
    for t in select(build_tools(ctx), profile):
        ann = ToolAnnotations(title=t.title, read_only_hint=t.read_only, destructive_hint=t.destructive,
                              idempotent_hint=t.idempotent, open_world_hint=t.open_world)
        srv.add_tool(t.fn, name=t.name, title=t.title, description=(t.fn.__doc__ or "").strip(), annotations=ann)
    _add_prompts(srv, ctx)
    _add_resources(srv, ctx)
    return srv


def _add_prompts(srv: MCPServer, ctx: Context) -> None:
    """The /cra-* slash commands, as MCP prompts (slash commands in Claude Code, Gemini CLI, VS Code, Zed)."""
    try:
        cdir = os.path.join(ctx.toolkit, "commands")
        files = sorted(f for f in os.listdir(cdir) if f.endswith(".md"))
    except (FileNotFoundError, OSError):
        return
    for f in files:
        text = open(os.path.join(cdir, f), encoding="utf-8").read()
        m = re.match(r"^---\n(.*?)\n---\n(.*)$", text, re.S)
        meta, body = (m.group(1), m.group(2).strip()) if m else ("", text)
        desc = re.search(r"^description:\s*(.+)$", meta, re.M)
        name = f[:-3]

        def make(body=body):
            def prompt(arguments: str = "") -> str:
                return (body.replace("$ARGUMENTS", arguments or "(none)") +
                        "\n\n(Through MCP: start with the cra_resume tool; use role_card / skill_guide for the "
                        "agent and skill files mentioned above, and the typed claim_/evidence_/gate_ tools for "
                        "every blackboard change.)")
            return prompt

        srv.prompt(name=name, description=desc.group(1).strip() if desc else name)(make())


def _add_resources(srv: MCPServer, ctx: Context) -> None:
    for board in ("STATE.md", "CLAIMS.md", "EVIDENCE.md", "DECISIONS.md"):
        def make(board=board):
            def read() -> str:
                return ctx.P.read(board) or f"({board} does not exist yet)"
            return read
        srv.resource(f"cra://project/{board}", name=board, description=f"project blackboard: {board}",
                     mime_type="text/markdown")(make())


# ----------------------------------------------------------------------------- HTTP
class _BearerAuth:
    """Minimal ASGI guard: require ``Authorization: Bearer <token>``."""

    def __init__(self, app, token: str):
        self.app, self.token = app, token.encode()

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            hdr = dict(scope.get("headers") or []).get(b"authorization", b"")
            if not secrets.compare_digest(hdr, b"Bearer " + self.token):
                await send({"type": "http.response.start", "status": 401,
                            "headers": [(b"content-type", b"text/plain"), (b"www-authenticate", b"Bearer")]})
                await send({"type": "http.response.body", "body": b"unauthorized"})
                return
        await self.app(scope, receive, send)


def serve_http(srv: MCPServer, host: str, port: int, path: str, token: str | None, allow_hosts: list[str]) -> None:
    import uvicorn
    from mcp.server.transport_security import TransportSecuritySettings

    hosts = [f"{h}:{port}" for h in ("127.0.0.1", "localhost")] + ["127.0.0.1", "localhost"] + allow_hosts
    sec = TransportSecuritySettings(enable_dns_rebinding_protection=True, allowed_hosts=hosts,
                                    allowed_origins=["https://chatgpt.com", "https://chat.openai.com",
                                                     "https://claude.ai"] + [f"https://{h}" for h in allow_hosts])
    app = srv.streamable_http_app(streamable_http_path=path, transport_security=sec, host=host)
    if token:
        app = _BearerAuth(app, token)
    uvicorn.run(app, host=host, port=port, log_level="warning")


def _secret(project: str, rotate: bool = False) -> str:
    """Secret URL path segment, persisted in <project>/.cra/mcp-secret so the connector URL survives restarts."""
    d = os.path.join(project, ".cra")
    p = os.path.join(d, "mcp-secret")
    if not rotate and os.path.exists(p):
        v = open(p).read().strip()
        if re.fullmatch(r"[A-Za-z0-9_-]{20,}", v):
            return v
    os.makedirs(d, exist_ok=True)
    v = secrets.token_urlsafe(24)
    fd = os.open(p, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as fh:
        fh.write(v + "\n")
    gi = os.path.join(d, ".gitignore")
    lines = open(gi).read().split() if os.path.exists(gi) else []
    if "mcp-secret" not in lines:
        with open(gi, "a") as fh:
            fh.write("mcp-secret\n")
    return v


# ----------------------------------------------------------------------------- export
def tool_schemas(project: str, profile: str) -> list[dict]:
    srv = build_server(project, profile)
    tools = asyncio.run(srv.list_tools())
    out = []
    for t in tools:
        d = t.model_dump(by_alias=True, exclude_none=True)
        out.append({"name": d["name"], "description": d.get("description", ""), "inputSchema": d["inputSchema"],
                    "annotations": d.get("annotations", {})})
    return out


def _clean(schema: dict, strict: bool) -> dict:
    """Drop JSON-Schema keywords some function-calling APIs reject; optionally OpenAI strict form."""
    s = {k: v for k, v in schema.items() if k not in ("title", "$schema", "additionalProperties")}
    if s.get("type") == "object":
        props = {k: {kk: vv for kk, vv in v.items() if kk != "title"} for k, v in s.get("properties", {}).items()}
        if strict:
            for k, v in props.items():
                v.pop("default", None)
                if k not in s.get("required", []):
                    v["type"] = [v["type"], "null"] if isinstance(v.get("type"), str) else v.get("type")
            s["required"] = list(props)
            s["additionalProperties"] = False
        s["properties"] = props
    return s


def export(fmt: str, project: str, profile: str) -> list[dict]:
    tools = tool_schemas(project, profile)
    if fmt == "anthropic":
        return [{"name": t["name"], "description": t["description"], "input_schema": _clean(t["inputSchema"], False)}
                for t in tools]
    if fmt == "openai":
        return [{"type": "function", "function": {"name": t["name"], "description": t["description"][:1024],
                                                  "parameters": _clean(t["inputSchema"], True), "strict": True}}
                for t in tools]
    if fmt == "gemini":
        return [{"functionDeclarations": [{"name": t["name"], "description": t["description"],
                                           "parameters": _clean(t["inputSchema"], False)} for t in tools]}]
    raise ValueError(fmt)


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if argv[:1] == ["install"]:
        from .install import main as install_main
        return install_main(argv[1:])
    if argv[:1] == ["doctor"]:
        from .install import doctor
        dp = argparse.ArgumentParser(prog="cra-mcp doctor")
        dp.add_argument("--project", default=os.environ.get("CRA_PROJECT", "."))
        return doctor(dp.parse_args(argv[1:]).project)
    ap = argparse.ArgumentParser(prog="cra-mcp", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--project", default=os.environ.get("CRA_PROJECT", "."))
    ap.add_argument("--profile", choices=PROFILES, default=os.environ.get("CRA_PROFILE", "core"))
    ap.add_argument("--actor", default=os.environ.get("CRA_ACTOR", "mcp"), help="name recorded in .cra/events.jsonl")
    ap.add_argument("--http", action="store_true", help="serve Streamable HTTP instead of stdio")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--path", default="/mcp")
    ap.add_argument("--secret-path", action="store_true",
                    help="serve at /mcp/<random> (for hosts that cannot send headers, e.g. ChatGPT no-auth)")
    ap.add_argument("--token-env", default="CRA_MCP_TOKEN", help="env var holding a bearer token (HTTP)")
    ap.add_argument("--allow-host", action="append", default=[], help="public host name of a tunnel (repeatable)")
    ap.add_argument("--public-url", default="",
                    help="public HTTPS base URL of your tunnel, e.g. https://abc.trycloudflare.com "
                         "(implies --allow-host <its host>; prints the exact URL to paste into ChatGPT / claude.ai)")
    ap.add_argument("--new-secret", action="store_true", help="rotate the persisted --secret-path secret")
    ap.add_argument("--list-tools", action="store_true")
    ap.add_argument("--export", choices=["openai", "anthropic", "gemini"])
    ap.add_argument("--version", action="version", version=__version__)
    a = ap.parse_args(argv)
    project = os.path.abspath(os.path.expanduser(a.project))

    if a.list_tools:
        print(json.dumps(tool_schemas(project, a.profile), indent=1, ensure_ascii=False))
        return 0
    if a.export:
        print(json.dumps(export(a.export, project, a.profile), indent=1, ensure_ascii=False))
        return 0

    srv = build_server(project, a.profile, a.actor)
    if not a.http:
        srv.run("stdio")
        return 0
    token = os.environ.get(a.token_env) or None
    if a.public_url:
        from urllib.parse import urlparse
        u = urlparse(a.public_url if "://" in a.public_url else "https://" + a.public_url)
        if not u.hostname:
            print(f"cannot parse --public-url {a.public_url!r}", file=sys.stderr)
            return 2
        a.allow_host.append(u.hostname)
    path = a.path.rstrip("/") + (f"/{_secret(project, a.new_secret)}" if a.secret_path else "")
    public = a.host not in ("127.0.0.1", "localhost", "::1") or a.allow_host
    if public and not token and not a.secret_path:
        print("refusing to serve beyond localhost without auth: set $%s or use --secret-path" % a.token_env,
              file=sys.stderr)
        return 2
    print(f"cra-mcp {__version__}: project {project}, profile {a.profile}", file=sys.stderr)
    print(f"  local URL : http://{a.host}:{a.port}{path}", file=sys.stderr)
    for h in a.allow_host:
        print(f"  public URL: https://{h}{path}", file=sys.stderr)
    if a.public_url:
        print(f"\n  >>> paste this as the MCP server URL: https://{a.allow_host[-1]}{path}\n", file=sys.stderr)
    if a.secret_path:
        print("  the URL path is the secret (kept in .cra/mcp-secret, same across restarts; "
              "rotate with --new-secret): do not share or commit it", file=sys.stderr)
    serve_http(srv, a.host, a.port, path, token, a.allow_host)
    return 0


if __name__ == "__main__":
    sys.exit(main())
