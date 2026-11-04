# Using crypto-research-agents from any AI platform

[中文版](../zh/integrations.md) · [Compatibility reference (sources, limits)](COMPATIBILITY.md) · [Cline + DeepSeek](cline-deepseek.md)

The research workflow is exposed as an MCP server, **`cra-mcp`**, so any MCP-capable host can drive it.
- It provides **15 tools** in the default `core` profile: resume, claims, evidence, gates, phases, decisions,
  bib-verify, role cards and skill guides.
- The workflow's rules live in the server, so they are enforced in the same way whichever model or IDE
  you use.
- The server never calls an LLM itself and needs no API key.

## 1. Install (once)

```bash
git clone <this repo> ~/crypto-research-agents
cd ~/crypto-research-agents
pip install -e lib/core -e lib/bench -e lib/cryptomath -e lib/mcp     # Python >= 3.10
cra init ~/papers/my-paper                                            # a research project
cra-mcp doctor --project ~/papers/my-paper
```

## 2. Connect your platform

```bash
cra-mcp install --host <host> --project ~/papers/my-paper    # add --dry-run to preview
```

| You use | `--host` | What happens |
|---|---|---|
| Claude Code | `claude-code` | writes `.mcp.json` + `CLAUDE.md`; approve once, check with `/mcp`. Optional: `./install.sh <project>` for the native agents, skills and `/cra-*` commands. |
| Claude Desktop | `claude-desktop` | prints the `claude_desktop_config.json` entry; restart the app |
| claude.ai (web) | `claude-ai` | prints the remote-connector steps (§3) |
| **ChatGPT** | `chatgpt` | prints the developer-mode app steps (§3) |
| Codex CLI / IDE | `codex` | prints the `config.toml` block and `codex mcp add …`; writes `AGENTS.md` |
| Gemini CLI | `gemini` | writes `.gemini/settings.json` + `GEMINI.md` |
| Qwen Code | `qwen` | writes `.qwen/settings.json` + `QWEN.md` |
| **Cline** (e.g. with DeepSeek) | `cline` | prints the `cline_mcp_settings.json` entry; writes `.clinerules/cra.md` — see [cline-deepseek.md](cline-deepseek.md) |
| Roo Code / Kilo Code | `roo` / `kilo` | writes `.roo/mcp.json` / `.kilocode/mcp.json` |
| Cursor | `cursor` | writes `.cursor/mcp.json` + `.cursor/rules/cra.mdc` |
| Windsurf | `windsurf` | prints the `mcp_config.json` entry |
| VS Code + Copilot | `vscode` | writes `.vscode/mcp.json` (`servers` key) + `.github/copilot-instructions.md` |
| JetBrains (Junie / AI Assistant) | `jetbrains` | writes `.junie/mcp/mcp.json` |
| Zed | `zed` | prints the `context_servers` entry |
| OpenCode | `opencode` | writes `opencode.json` (`mcp` key) |
| Continue | `continue` | writes `.continue/mcpServers/cra.yaml` |
| Trae / Cherry Studio / LM Studio | `trae` / `cherry-studio` / `lmstudio` | writes or prints the `mcpServers` entry |
| anything else (Kimi Code CLI, iFlow, …) | `generic` | prints the common `mcpServers` JSON |

Configs use the absolute Python interpreter path, so hosts with a minimal `PATH` (GUI apps) still work.
- Files inside your project are merged: only the `cra` entry is added or replaced.
- Files in your home directory are never edited; the installer prints what to paste.

Then, in the host, say: **"call cra_resume and continue the project"**.

## 3. ChatGPT and claude.ai (cloud hosts)

**Step-by-step guide with troubleshooting: [chatgpt.md](chatgpt.md).**

ChatGPT and claude.ai connect from the cloud, so they need a public HTTPS URL. Use the `remote` profile:
it adds sandboxed `file_list`/`file_read`/`file_write` and `search`/`fetch`, because these hosts cannot
see your disk.

```bash
cloudflared tunnel --url http://127.0.0.1:8765          # terminal 1 (or: ngrok http 8765) -> note the https URL
```

```bash
cra-mcp --project ~/papers/my-paper --http --profile remote --secret-path --public-url <tunnel URL>   # terminal 2
```

- **ChatGPT:** Settings → Apps (Connectors) → Advanced → enable **Developer mode** → **Create app**:
  - MCP server URL = the URL printed after `>>>`; Authentication = **No auth**. The random URL path is the
    secret; it is kept in `.cra/mcp-secret` and stays the same across restarts.
  - Then, in a new chat: **+** → **Developer mode** → enable **cra**.
  - Write tools ask for confirmation.
  - After updating cra, press **Refresh** in the app settings.
  - Which plans may use write tools differs between OpenAI's own pages; check yours.
  - OpenAI also offers an outbound-only *Secure MCP Tunnel* instead of a public URL.
- **claude.ai:** Settings → Connectors → **Add custom connector** with the same URL.

Anyone who has the URL can read and write that project's files, so stop the tunnel when you are done.

## 4. OpenAI API / Agents SDK

To use cra from the OpenAI API or Agents SDK, serve it over HTTP with a bearer token:

```bash
CRA_MCP_TOKEN=$(openssl rand -hex 24) cra-mcp --project . --http     # http://127.0.0.1:8765/mcp
```

Then pass it as a remote MCP tool. The URL must be publicly reachable, for example through the tunnel
from §3:

```json
{"type": "mcp", "server_label": "cra", "server_url": "https://<host>/mcp",
 "headers": {"Authorization": "Bearer <token>"}, "require_approval": "never"}
```

## 5. No MCP at all: function-calling schemas

```bash
cra-mcp --export openai    > cra-tools.openai.json      # strict-mode function definitions
cra-mcp --export anthropic > cra-tools.anthropic.json
cra-mcp --export gemini    > cra-tools.gemini.json
```

The same operations are also available from the shell as `cra …` (`cra --help`).

## 6. Profiles

| Profile | Tools | Use when |
|---|---|---|
| `core` (default) | 15 | any host; best for smaller or cheaper models and hosts with tool caps |
| `full` | 24 | local power use: adds ePrint search, lit-matrix lint, core-SVP screen, audit-tex, anonymity scan, file tools |
| `remote` | 21 | ChatGPT / claude.ai: core + file access + `search`/`fetch` |

## 7. Enforcement on every platform

- **Server rules.** Verdicts need evidence and refs, evidence needs an existing log (its hash is
  recorded), phases cannot skip a failing gate, and `file_write` refuses the ledger files.
- **Git hook.** `cra hook install` adds a pre-commit hook in the project. It blocks commits whose paper cites
  a non-survived claim (`\claimref{C9}`) or an unknown evidence row, or whose logs changed after
  recording. It works with any IDE or agent.
- **Gates.** `gate_check` / `cra gate P<k>` is the mechanical part of every phase gate.
