# Host compatibility reference (researched 2026-11)

This page records what each MCP host supports, plus how cra-mcp responds to it. **Platforms change fast.**
- Every row lists its source.
- **(unverified)** means we could not confirm the point against an official page when this was written.
- Several vendor doc sites (developers/help/platform.openai.com, api-docs.deepseek.com, docs.cline.bot,
  geminicli.com) were not reachable from the build sandbox. Facts about those products come from vendor
  GitHub source code or search extracts of the official pages.
- If something here is wrong, please open an issue.

## Design rules derived from this research (enforced by `lib/mcp/tests/test_server.py`)

| Rule | Why |
|---|---|
| Server name `cra` (no `_`/`-`); tool names `^[a-z][a-z0-9_]{0,31}$` | `mcp__cra__<tool>` fits OpenAI's 64-char function names, Gemini's 63-char qualified names, and Claude Code's and Codex's 128. Gemini's policy parser splits on the first `_` of the server name. |
| Flat schemas: primitives / enums / plain defaults; no `anyOf`, `$ref`, `$defs`, `pattern` or `format`; each schema ≤ 5 KB | Gemini strips or rejects some keywords. OpenAI strict mode needs a simple subset. Codex's `tool_input_schema_max_bytes` defaults to 5000. |
| `readOnlyHint` / `destructiveHint` / `idempotentHint` / `openWorldHint` on **every** tool | ChatGPT treats tools without `readOnlyHint` as writes. The claude.ai directory requires the hints. Claude Code parallelises and retries read-only tools. |
| Default profile `core` = 15 tools | Cursor reportedly caps at about 40 tools (unverified), Windsurf at 100 across all servers, VS Code at 128 per request. Weaker models (DeepSeek, local models) choose better from short lists. |
| Results ≤ about 40 000 characters, paged with `offset` | Claude Code warns above 10k tokens. claude.ai caps results at about 150k characters. |
| Tools finish in < 60 s | 60 s is the default tool timeout in Codex and Cline; claude.ai's hard cap is 240 s. |
| Refusals are returned as `ok:false` + `violations` | Weak models recover from readable refusals better than from protocol errors. |
| No dependency on sampling or elicitation | claude.ai does not support sampling. Elicitation is reliable only in Claude Code and Codex. |
| Transports: stdio (default) + Streamable HTTP (no SSE) | Remote hosts (ChatGPT, claude.ai, Responses API) need HTTP. Cline and Roo users must then set the `type` explicitly. |
| HTTP auth: bearer token **or** secret URL path | ChatGPT offers only "No auth" or OAuth (no static headers), so the URL itself is the credential. |
| Server `instructions` start with a self-contained summary | ChatGPT asks that the first 512 characters stand alone. |
| `remote` profile adds `file_*`, `search`, `fetch` | ChatGPT and claude.ai cannot see the local disk. `search`/`fetch` follow ChatGPT's deep-research / company-knowledge shape. |

## Per host

| Host | Transport | Config | Primitives / limits | Instruction file | `cra-mcp install --host` |
|---|---|---|---|---|---|
| **Claude Code** | stdio, http, sse (deprecated), ws | `.mcp.json` `mcpServers` (project); `claude mcp add` ([docs](https://code.claude.com/docs/en/mcp)) | Tools, resources (`@`), prompts (`/mcp__cra__…`), roots, elicitation. Full tool name ≤ 128 chars. `MAX_MCP_OUTPUT_TOKENS` 25k. | `CLAUDE.md` | `claude-code` (writes `.mcp.json` + `CLAUDE.md`). Agents/skills/commands also install natively via `./install.sh`. |
| **Claude Desktop** | stdio; `.mcpb` bundles | `claude_desktop_config.json` (macOS `~/Library/Application Support/Claude/`, Windows `%APPDATA%\Claude\`; Linux path unverified) | Minimal PATH, so use absolute paths (the installer does) | — | `claude-desktop` (prints the snippet) |
| **claude.ai** custom connectors | Remote Streamable HTTP over public HTTPS ([docs](https://claude.com/docs/connectors/custom/remote-mcp)) | Settings → Connectors | Tools, prompts, resources; **no sampling**. About 150k characters per result; 240 s per call. | — | `claude-ai` (prints the tunnel steps) |
| **ChatGPT** developer mode / apps | Remote only (SSE / streaming HTTP), public HTTPS ([dev mode](https://developers.openai.com/api/docs/guides/developer-mode)) | Settings → Apps → Advanced → Developer mode → Create app; auth: none / OAuth / mixed | Tools (write tools need confirmation; `readOnlyHint` honoured). `search` + `fetch` needed only for deep research / company knowledge. Refresh the app after tool changes. Write-tool availability per plan differs between OpenAI pages (unverified for Plus/Pro). | — | `chatgpt` (prints tunnel + app steps) |
| **OpenAI Responses API / Agents SDK** | Remote MCP tool `{"type":"mcp","server_url":…,"require_approval":…}` ([docs](https://developers.openai.com/api/docs/guides/tools-remote-mcp)) | In code | `allowed_tools`; approval items | — | Run `cra-mcp --http`; see [README](README.md#openai-api-agents-sdk) |
| **Codex CLI / IDE** | stdio, Streamable HTTP | `~/.codex/config.toml` `[mcp_servers.cra]` (project `.codex/config.toml` only when trusted); `codex mcp add` ([source](https://github.com/openai/codex)) | Tools, resources, elicitation. Default timeouts: startup 10 s, tool 60 s. Names ≤ 128 bytes. | `AGENTS.md` (≤ 32 KiB total) | `codex` (prints TOML + `codex mcp add`; writes `AGENTS.md`) |
| **Gemini CLI** | stdio, SSE (`url`), HTTP (`httpUrl`) | `.gemini/settings.json` `mcpServers`; `gemini mcp add` ([docs](https://github.com/google-gemini/gemini-cli/blob/main/docs/tools/mcp-server.md)) | Strips `$schema`/`additionalProperties`; qualified name `mcp_{server}_{tool}` ≤ 63 chars | `GEMINI.md` | `gemini` |
| **Qwen Code** | as Gemini CLI | `.qwen/settings.json` | as Gemini CLI | `QWEN.md` | `qwen` |
| **Cline** | stdio, sse, `streamableHttp` (URL without `type` defaults to SSE) | `cline_mcp_settings.json` via the MCP Servers panel; `autoApprove`; `timeout` in **seconds** (default 60) ([schema](https://github.com/cline/cline)) | Tools. Native JSON tool calling since v3.35, so models without tool calling fail. | `.clinerules` | `cline` (prints the snippet; writes `.clinerules/cra.md`) — see [Cline + DeepSeek](cline-deepseek.md) |
| **Roo Code** | stdio, sse, `streamable-http` | `.roo/mcp.json`; `alwaysAllow` | | `.roo/rules` | `roo` |
| **Kilo Code** | stdio, HTTP→SSE fallback | legacy `.kilocode/mcp.json`; new `kilo.json` `mcp` key | | `AGENTS.md` (unverified) | `kilo` |
| **Cursor** | stdio, HTTP, SSE | `.cursor/mcp.json` `mcpServers` | Tool cap reportedly about 40 (unverified) | `.cursor/rules/*.mdc`, `AGENTS.md` | `cursor` |
| **Windsurf** | stdio, HTTP (`serverUrl`), SSE | `~/.codeium/windsurf/mcp_config.json` ([docs](https://docs.windsurf.com/windsurf/cascade/mcp)) | 100-tool cap across servers | `.windsurf/rules` (unverified) | `windsurf` (prints) |
| **VS Code + Copilot** | stdio, http, sse | `.vscode/mcp.json` **`servers`** key; `code --add-mcp` ([docs](https://code.visualstudio.com/docs/copilot/chat/mcp-servers)) | Tools, prompts (`/mcp.cra.*`), resources, sampling. 128 tools per request. | `.github/copilot-instructions.md` | `vscode` |
| **JetBrains Junie / AI Assistant** | stdio (HTTP unclear) | `.junie/mcp/mcp.json` ([docs](https://www.jetbrains.com/help/junie/model-context-protocol-mcp.html)) | No tokens in config | `.junie/guidelines.md` (unverified) | `jetbrains` |
| **Zed** | stdio, HTTP | settings.json `context_servers` ([docs](https://github.com/zed-industries/zed/blob/main/docs/src/ai/mcp.md)) | Tools + prompts only (no resources) | `.rules`, `AGENTS.md` | `zed` (prints) |
| **Continue** | stdio, sse, streamable-http | `.continue/mcpServers/*.yaml` | Agent mode only | `.continue/rules` | `continue` |
| **OpenCode** | local / remote | `opencode.json` `mcp` key (`command` is an array; default timeout 30 s) ([docs](https://github.com/sst/opencode)) | | `AGENTS.md` | `opencode` |
| **Trae** | stdio, http (unverified) | `.trae/mcp.json` (enable Project MCP) | | unverified | `trae` |
| **Cherry Studio** | stdio, `streamableHttp` | UI import JSON | | — | `cherry-studio` (prints) |
| **LM Studio** | stdio, HTTP | `~/.lmstudio/mcp.json` ([docs](https://lmstudio.ai/docs/app/mcp)) | Needs a model with tool calling | — | `lmstudio` (prints) |
| **Kimi Code CLI** (Kimi CLI archived) | stdio, http | `kimi mcp add --transport stdio cra -- <cmd>` (Kimi Code config unverified) | | `AGENTS.md` (unverified) | `generic` |
| **iFlow CLI** | stdio, http | `~/.iflow/settings.json`; `iflow mcp add` | | `IFLOW.md` (unverified) | `generic` |

## Models vs hosts: DeepSeek, GLM, Kimi, Qwen, MiniMax

These are **models**, not MCP hosts. There are three ways to use them with cra:
1. Pick the model inside an MCP host (Cline, Roo, Kilo, OpenCode, Cherry Studio, Continue, …).
2. Run **Claude Code** against the vendor's Anthropic-compatible endpoint by putting these in
   `~/.claude/settings.json` → `env`: `ANTHROPIC_BASE_URL`, `ANTHROPIC_AUTH_TOKEN`, `ANTHROPIC_MODEL`. A stray
   `ANTHROPIC_API_KEY` overrides the token. This route also gives you the native agents, skills and commands.
3. For your own scripts, the OpenAI-compatible endpoint plus `cra-mcp --export openai`.

| Provider | Anthropic-compatible base URL | OpenAI-compatible base URL | Notes |
|---|---|---|---|
| DeepSeek | `https://api.deepseek.com/anthropic` ([guide](https://api-docs.deepseek.com/guides/anthropic_api/)) | `https://api.deepseek.com` (`/v1`) | The model list changes; pick in the UI. As of 2026-11, search results show V4-generation models with tool calls and a 1M context. Thinking mode allows only `tool_choice: auto`. |
| Zhipu GLM (international) | `https://api.z.ai/api/anthropic` ([docs](https://docs.z.ai/scenario-example/develop-tools/claude)) | `https://api.z.ai/api/paas/v4` (Coding Plan: `/api/coding/paas/v4`) | Set `API_TIMEOUT_MS` high |
| Zhipu GLM (China) | `https://open.bigmodel.cn/api/anthropic` ([docs](https://docs.bigmodel.cn/cn/coding-plan/tool)) | `https://open.bigmodel.cn/api/paas/v4` | Coding Plan keys work only on the plan endpoint |
| Moonshot Kimi | `https://api.moonshot.ai/anthropic` ([docs](https://platform.kimi.ai/docs/guide/claude-code-kimi)) | `https://api.moonshot.ai/v1` (China `api.moonshot.cn/v1`) | The guide sets `ENABLE_TOOL_SEARCH=false` |
| Alibaba Qwen (Model Studio) | `https://dashscope-intl.aliyuncs.com/apps/anthropic` ([docs](https://www.alibabacloud.com/help/en/model-studio/claude-code)) | `https://dashscope-intl.aliyuncs.com/compatible-mode/v1` | Mainland hosts drop `-intl` (unverified) |
| MiniMax | `https://api.minimax.io/anthropic` (China `api.minimaxi.com`) ([docs](https://platform.minimax.io/docs/token-plan/claude-code)) | `https://api.minimax.io/v1` (unverified) | |

## Function-calling export constraints (`cra-mcp --export`)

- **OpenAI:** names must match `^[a-zA-Z0-9_-]{1,64}$`. Strict mode requires `additionalProperties: false` and
  every property listed in `required`, with optional fields typed nullable. The export does this.
- **Gemini:** `parameters` takes an OpenAPI-3.0 subset. Avoid `$ref`, `anyOf`+`default` and
  `additionalProperties`; the export strips them.
- **Anthropic:** `input_schema` takes plain JSON Schema.
