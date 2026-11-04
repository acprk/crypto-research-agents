# CRA Studio — the desktop app

[中文](zh/studio.md) · [Integrations](integrations/README.md)

CRA Studio packages the whole toolkit as **one executable**: a local GUI plus the `cra` MCP server, the
`cra` CLI and the `cra-agent` loop. It follows the shape of open-source AI-for-science workbenches:
- you open a project;
- you point the app at any model endpoint;
- an agent works through tools while you watch and approve.

The implementation is original and specific to the falsify-first cryptography pipeline.

## Get it

- **Download** `CRA-Studio-windows-x64.exe`, `CRA-Studio-macos-arm64` or `CRA-Studio-linux-x64` from the
  GitHub release. The `release` workflow builds them on every `v*` tag.
  - The binaries are unsigned. On Windows, SmartScreen shows "More info → Run anyway".
  - On macOS, run `xattr -d com.apple.quarantine CRA-Studio-macos-arm64 && chmod +x CRA-Studio-macos-arm64` once.
- **Or build it yourself:**
  `pip install -e lib/core -e lib/bench -e lib/mcp -e lib/studio pyinstaller && pyinstaller packaging/cra-studio.spec --noconfirm`
  The result is in `dist/`.
- **Or run it from source:** `pip install -e lib/studio …` then `cra-studio`.

## Use it

Start `CRA-Studio`. It opens `http://127.0.0.1:8770/#t=<token>` in your browser.

1. **Projects:** open a research directory, or create one (blackboard files plus a paper skeleton).
2. **Settings → Model endpoint:** pick a preset (OpenAI, DeepSeek, GLM, Kimi, Qwen, MiniMax, OpenRouter, Ollama,
   vLLM) **or enter any OpenAI-compatible Base URL**, then the API key and the model id.
   - **Test** lists the endpoint's models.
   - The key is stored only in your user config file (mode 600), never shown again and never written to a
     project or to git. The file is at `%APPDATA%\cra\studio.json`, `~/Library/Application Support/cra/studio.json`
     or `~/.config/cra/studio.json`.
   - `OPENAI_BASE_URL` / `OPENAI_API_KEY` / `CRA_MODEL` in the environment fill empty fields.
3. **Dashboard:** phase, claim counts, evidence rows, the gate result and the next tasks. **Run** hands the first
   task to the agent.
4. **Research agent:** a chat in which the model works only through the cra tools.
   - Every tool call and result is shown.
   - Destructive calls (`phase_advance`, `file_write`) wait for your **Allow / Deny**.
   - The conversation continues per project; tick "new chat" to start fresh.
   - The agent cannot run shell commands. When an experiment is needed, it tells you the command; you run
     it, and the evidence is registered from the log.
5. **Ledgers:** the claims and evidence tables and the blackboard files.
6. **Connect tools:** writes the MCP configuration for Claude Code, Codex, Cline, Cursor, VS Code and 16 more
   hosts. The executable itself is the server, so the configs call `<CRA-Studio> mcp --project …`.

## One executable, several roles

```text
CRA-Studio                                   GUI (default)
CRA-Studio mcp --project <dir> [--http]      cra MCP server (stdio or Streamable HTTP)
CRA-Studio install --host <h> --project <d>  write MCP config for a host
CRA-Studio agent --model <id> --project <d>  terminal agent (OpenAI-compatible API)
CRA-Studio cra <args>                        blackboard CLI (init, status, gate, claim, evidence, check, hook)
CRA-Studio doctor --project <dir>            self-check
```

## Security

- The GUI binds to 127.0.0.1 only.
- Every API call needs this session's token (in the URL fragment) and a localhost Host header, so other
  web pages cannot drive it.
- The API key is write-only from the browser's point of view.
- Text you send to the agent, and the project content it reads, go to the model endpoint you configured.
  Choose that endpoint accordingly.
- Nothing in cra submits, e-mails or publishes.
