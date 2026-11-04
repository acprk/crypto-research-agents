"""`cra-mcp install --host <host>` -- wire the cra MCP server into an agent host.

Project-scoped config files (inside the research project) are written directly and merged
with existing content (only the "cra" entry is touched). User-global config files are never
modified silently: their snippet and location are printed for you to paste, or use the host's
own `... mcp add` command shown alongside.

Facts per host are summarised (with sources) in docs/integrations/COMPATIBILITY.md.
"""
from __future__ import annotations

import json
import os
import shutil
import sys

READONLY_CORE = ["cra_resume", "role_card", "skill_guide", "blackboard_read", "claim_list", "evidence_list",
                 "gate_check", "invariants_check"]

BEGIN, END = "<!-- cra:begin -->", "<!-- cra:end -->"
GUIDE = f"""{BEGIN}
## crypto-research-agents (cra MCP server)
This project is run with the `cra` MCP server (falsify-first pipeline P0-P8 for cryptography papers).
1. At the start of every session, and after any context reset, call the **`cra_resume`** tool and follow
   its `next_tasks` (each names the agent role, the inputs, the output and the tool to call).
2. Adopt a role with `role_card(<agent>)`; read procedures with `skill_guide(<skill>)`.
3. Change the ledgers only through the typed tools: `claim_register`, `claim_verdict`, `evidence_add`,
   `decision_log`, `gate_tick`, `phase_advance`. Never edit CLAIMS.md / EVIDENCE.md / DECISIONS.md by hand.
4. Invariants: only survived/weakened claims (cite as `\\claimref{{C<n>}}`) and numbers with an EVIDENCE row
   (`3.86x\\evid{{E3}}`) enter paper/. Never invent a number: run the experiment, then `evidence_add`.
   Run `invariants_check` after editing paper/.
5. Nothing leaves the machine (submission, e-mail, eprint, public repo) without explicit human approval.
{END}
"""

HOSTS = ["claude-code", "claude-desktop", "claude-ai", "chatgpt", "codex", "gemini", "qwen", "cline", "roo",
         "kilo", "cursor", "windsurf", "vscode", "zed", "opencode", "continue", "lmstudio", "trae", "cherry-studio",
         "jetbrains", "generic"]


def server_cmd(project: str, profile: str) -> tuple[str, list[str]]:
    """Absolute interpreter + module: works even where GUI apps have a minimal PATH (Claude Desktop)."""
    return sys.executable, ["-m", "cra_mcp.server", "--project", project, "--profile", profile]


def _merge_json(path: str, keypath: list[str], value) -> str:
    data = {}
    if os.path.exists(path):
        with open(path, encoding="utf-8") as fh:
            txt = fh.read().strip()
        if txt:
            try:
                data = json.loads(txt)
            except json.JSONDecodeError:
                raise SystemExit(f"{path} is not plain JSON (comments?); add this entry by hand:\n"
                                 + json.dumps({keypath[-1]: value}, indent=2))
    cur = data
    for k in keypath[:-1]:
        cur = cur.setdefault(k, {})
    cur[keypath[-1]] = value
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    return path


def _guide_file(path: str) -> str:
    """Create or update the cra block in an instruction file (idempotent)."""
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    old = open(path, encoding="utf-8").read() if os.path.exists(path) else ""
    if BEGIN in old and END in old:
        new = old[:old.index(BEGIN)] + GUIDE.strip() + old[old.index(END) + len(END):]
    else:
        new = (old.rstrip() + "\n\n" if old.strip() else "") + GUIDE.strip() + "\n"
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(new)
    return path


def _home(*p: str) -> str:
    return os.path.join(os.path.expanduser("~"), *p)


def install(host: str, project: str, profile: str = "core", dry_run: bool = False) -> list[str]:
    """Returns human-readable lines describing what was written / what to paste."""
    project = os.path.abspath(os.path.expanduser(project))
    cmd, args = server_cmd(project, profile)
    std = {"command": cmd, "args": args}
    out: list[str] = []
    P = lambda *p: os.path.join(project, *p)

    def write_json(path, keypath, value):
        if dry_run:
            out.append(f"would merge into {path}:\n{json.dumps({keypath[-1]: value}, indent=2)}")
        else:
            out.append(f"wrote {_merge_json(path, keypath, value)}")

    def guide(path):
        if dry_run:
            out.append(f"would add the cra block to {path}")
        else:
            out.append(f"wrote {_guide_file(path)}")

    def paste(where, snippet, extra=""):
        out.append(f"paste into {where}:\n{snippet}" + (f"\n{extra}" if extra else ""))

    if host == "claude-code":
        write_json(P(".mcp.json"), ["mcpServers", "cra"], std)
        guide(P("CLAUDE.md"))
        out.append("Claude Code asks once to approve the project's .mcp.json; check with /mcp. "
                   "Alternative: claude mcp add cra -s project -- " + " ".join([cmd, *args]))
        out.append("Agents/skills/slash commands as native Claude Code files: ./install.sh <project> (optional).")
    elif host == "claude-desktop":
        loc = {"darwin": _home("Library", "Application Support", "Claude", "claude_desktop_config.json"),
               "win32": os.path.join(os.environ.get("APPDATA", "%APPDATA%"), "Claude", "claude_desktop_config.json")
               }.get(sys.platform, _home(".config", "Claude", "claude_desktop_config.json") + "  (Linux path unofficial)")
        paste(loc + "  (Settings -> Developer -> Edit Config)",
              json.dumps({"mcpServers": {"cra": std}}, indent=2), "then fully quit and restart Claude Desktop.")
    elif host in ("chatgpt", "claude-ai"):
        out.append(remote_instructions(host, project))
    elif host == "codex":
        toml = (f'[mcp_servers.cra]\ncommand = {json.dumps(cmd)}\nargs = {json.dumps(args)}\n'
                f'startup_timeout_sec = 20\ntool_timeout_sec = 120\n')
        paste("~/.codex/config.toml (or <project>/.codex/config.toml for a trusted project)", toml,
              "or run:  codex mcp add cra -- " + " ".join([cmd, *args]) + "\nthen check with:  codex mcp list")
        guide(P("AGENTS.md"))
    elif host in ("gemini", "qwen"):
        d = ".gemini" if host == "gemini" else ".qwen"
        write_json(P(d, "settings.json"), ["mcpServers", "cra"], {**std, "timeout": 120000, "trust": False})
        guide(P("GEMINI.md" if host == "gemini" else "QWEN.md"))
        out.append(f"check inside the CLI with /mcp")
    elif host in ("cline",):
        paste("Cline -> MCP Servers -> Configure -> 'Configure MCP Servers' (cline_mcp_settings.json)",
              json.dumps({"mcpServers": {"cra": {**std, "disabled": False, "autoApprove": READONLY_CORE,
                                                 "timeout": 120}}}, indent=2),
              "timeout is in SECONDS in Cline. For DeepSeek see docs/integrations/cline-deepseek.md.")
        guide(P(".clinerules", "cra.md"))
    elif host == "roo":
        write_json(P(".roo", "mcp.json"), ["mcpServers", "cra"], {**std, "alwaysAllow": READONLY_CORE, "timeout": 120})
        guide(P(".roo", "rules", "cra.md"))
    elif host == "kilo":
        write_json(P(".kilocode", "mcp.json"), ["mcpServers", "cra"], {**std, "alwaysAllow": READONLY_CORE})
        guide(P("AGENTS.md"))
        out.append("newer Kilo versions read kilo.json {\"mcp\": {...}} instead -- see COMPATIBILITY.md")
    elif host == "cursor":
        write_json(P(".cursor", "mcp.json"), ["mcpServers", "cra"], std)
        guide(P(".cursor", "rules", "cra.mdc"))
        guide(P("AGENTS.md"))
    elif host == "windsurf":
        paste("~/.codeium/windsurf/mcp_config.json", json.dumps({"mcpServers": {"cra": std}}, indent=2),
              "Windsurf caps the total number of tools across servers (100); the core profile uses 15.")
        guide(P(".windsurf", "rules", "cra.md"))
    elif host == "vscode":
        write_json(P(".vscode", "mcp.json"), ["servers", "cra"], {"type": "stdio", **std})
        guide(P(".github", "copilot-instructions.md"))
        out.append("or: code --add-mcp " + json.dumps(json.dumps({"name": "cra", "type": "stdio", **std})))
    elif host == "zed":
        paste("Zed settings.json", json.dumps({"context_servers": {"cra": {**std, "env": {}}}}, indent=2),
              "Zed supports tools and prompts (no resources).")
        guide(P("AGENTS.md"))
    elif host == "opencode":
        write_json(P("opencode.json"), ["mcp", "cra"], {"type": "local", "command": [cmd, *args], "enabled": True,
                                                        "timeout": 120000})
        guide(P("AGENTS.md"))
    elif host == "continue":
        yaml = ("name: cra\nversion: 0.2.0\nschema: v1\nmcpServers:\n  - name: cra\n    command: "
                + json.dumps(cmd) + "\n    args: " + json.dumps(args) + "\n")
        if dry_run:
            out.append(f"would write {P('.continue', 'mcpServers', 'cra.yaml')}:\n{yaml}")
        else:
            os.makedirs(P(".continue", "mcpServers"), exist_ok=True)
            open(P(".continue", "mcpServers", "cra.yaml"), "w").write(yaml)
            out.append(f"wrote {P('.continue', 'mcpServers', 'cra.yaml')} (agent mode only)")
        guide(P(".continue", "rules", "cra.md"))
    elif host == "lmstudio":
        paste("~/.lmstudio/mcp.json (LM Studio -> Program -> Install -> Edit mcp.json)",
              json.dumps({"mcpServers": {"cra": std}}, indent=2),
              "use a local model with native tool calling; the core profile keeps the tool list small.")
    elif host == "trae":
        write_json(P(".trae", "mcp.json"), ["mcpServers", "cra"], std)
        out.append("enable 'Project MCP' in Trae's settings (unverified -- see COMPATIBILITY.md)")
        guide(P("AGENTS.md"))
    elif host == "cherry-studio":
        paste("Cherry Studio -> Settings -> MCP Servers -> Add -> Import from JSON",
              json.dumps({"mcpServers": {"cra": {"type": "stdio", **std}}}, indent=2))
    elif host == "jetbrains":
        write_json(P(".junie", "mcp", "mcp.json"), ["mcpServers", "cra"], std)
        guide(P(".junie", "guidelines.md"))
        out.append("AI Assistant: Settings -> Tools -> AI Assistant -> MCP -> Add -> paste the same JSON")
    elif host == "generic":
        paste("your MCP client's config (most use this 'mcpServers' shape)",
              json.dumps({"mcpServers": {"cra": std}}, indent=2),
              "for HTTP clients: cra-mcp --project <dir> --http  (then http://127.0.0.1:8765/mcp, "
              "bearer token from $CRA_MCP_TOKEN)")
        guide(P("AGENTS.md"))
    else:
        raise SystemExit(f"unknown host {host!r}; choose one of: {', '.join(HOSTS)}")
    return out


def remote_instructions(host: str, project: str) -> str:
    app = "ChatGPT" if host == "chatgpt" else "claude.ai"
    steps = {
        "chatgpt": ("ChatGPT -> Settings -> Apps (Connectors) -> Advanced -> enable Developer mode -> Create app:\n"
                    "   name 'cra', MCP server URL = the URL printed after '>>>', Authentication = No auth\n"
                    "   (the secret URL path is the credential). Write tools ask for confirmation; after changing\n"
                    "   tools press Refresh in the app settings. Availability of write tools depends on your plan."),
        "claude-ai": ("claude.ai -> Settings -> Connectors -> Add custom connector: paste the public URL printed by\n"
                      "   cra-mcp (no OAuth). On Team/Enterprise an owner adds it. Per-call timeout is 240 s."),
    }[host]
    return f"""{app} reaches MCP servers from the cloud: it needs a public HTTPS URL (no local stdio).
Step-by-step guide: docs/integrations/chatgpt.md (中文: docs/zh/integrations.md#chatgpt-逐步接入)
1. Open a tunnel to local port 8765 in a first terminal and note its https:// URL:
   cloudflared tunnel --url http://127.0.0.1:8765      (prints https://<random>.trycloudflare.com)
   ngrok http 8765                                     (prints https://<random>.ngrok-free.app)
2. In a second terminal start the server with that URL (remote profile = file access + search/fetch,
   because {app} cannot see your disk):
   cra-mcp --project {project} --http --profile remote --secret-path --public-url <tunnel URL>
   It prints the exact URL to paste (">>> paste this as the MCP server URL: ..."). The secret part of
   the path is stored in .cra/mcp-secret and stays the same across restarts.
3. {steps}
Security: everyone with the URL can read and write this project's files. Stop the tunnel when done;
never paste the URL into shared chats. Nothing in cra can submit, e-mail or publish."""


def doctor(project: str) -> int:
    ok = True

    def line(good, msg):
        nonlocal ok
        ok &= bool(good)
        print(("ok    " if good else "FAIL  ") + msg)

    line(sys.version_info >= (3, 10), f"python {sys.version.split()[0]} (>= 3.10)")
    try:
        import importlib.metadata as md
        v = md.version("mcp")
        line(v.split(".")[0] == "2", f"mcp SDK {v} (2.x)")
    except Exception as e:  # pragma: no cover
        line(False, f"mcp SDK missing: {e}")
    try:
        from cra_core.toolkit import toolkit_root
        line(True, f"toolkit checkout: {toolkit_root()}")
    except FileNotFoundError as e:
        line(False, f"{e}")
    project = os.path.abspath(os.path.expanduser(project))
    line(os.path.exists(os.path.join(project, "STATE.md")), f"research project: {project} "
         "(STATE.md present; create with `cra init <dir>` or the project_init tool)")
    try:
        from .server import tool_schemas
        n = len(tool_schemas(project, "core"))
        line(n > 0, f"server builds; core profile exposes {n} tools")
    except Exception as e:
        line(False, f"server failed to build: {e}")
    for exe in ("cra", "cra-mcp"):
        line(shutil.which(exe) is not None, f"`{exe}` on PATH" + ("" if shutil.which(exe) else
             " (configs written by `install` use the absolute interpreter path, so this is optional)"))
    for opt in ("crbench",):
        try:
            __import__(opt)
            print(f"ok    optional: {opt}")
        except ImportError:
            print(f"info  optional: {opt} not installed (audit_tex tool disabled): pip install -e lib/bench")
    return 0 if ok else 1


def main(argv: list[str]) -> int:
    import argparse
    ap = argparse.ArgumentParser(prog="cra-mcp install", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--host", required=True, choices=HOSTS)
    ap.add_argument("--project", default=os.environ.get("CRA_PROJECT", "."))
    ap.add_argument("--profile", default="core", choices=["core", "full", "remote"])
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)
    for l in install(a.host, a.project, a.profile, a.dry_run):
        print(l)
    print("\nverify: cra-mcp doctor --project " + os.path.abspath(a.project))
    return 0
