# Cline + DeepSeek

[中文版](../zh/integrations.md#cline--deepseek) · [Back to integrations](README.md)

> Status: the cra-mcp side is tested: the stdio server, the tool schemas, and the generated Cline
> snippet. The DeepSeek model list and Cline's UI labels come from vendor sources as of 2026-11 and were
> not tested end-to-end here. If a label differs in your version, the option it describes is still the
> one to pick.

## 1. Model

1. Install the **Cline** extension in VS Code (or a fork such as Cursor or Windsurf).
2. Open Cline → settings (gear) → **API Provider: DeepSeek** → paste your API key from
   platform.deepseek.com.
3. **Model:** pick one from the dropdown. As of 2026-11 DeepSeek lists V4-generation models (a fast one and
   a pro one), which support tool calls and a 1M context. The older `deepseek-chat` / `deepseek-reasoner`
   aliases were scheduled for retirement. Prefer the faster model for routine tool work (claims, gates)
   and the pro model for theory and falsification.
4. DeepSeek's thinking mode accepts only `tool_choice: auto`, which is what Cline sends. If you see HTTP 400
   errors about `tool_choice`, switch to the non-thinking model.

## 2. Connect cra

```bash
cra-mcp install --host cline --project ~/papers/my-paper
```

- Paste the printed JSON via Cline → **MCP Servers** → **Configure** → "Configure MCP Servers"
  (`cline_mcp_settings.json`).
- The snippet sets:
  - `autoApprove` for the 8 read-only tools, so Cline does not ask before every `cra_resume`;
  - `timeout: 120` (Cline counts **seconds**);
  - the `core` profile (15 tools).
- It also writes `.clinerules/cra.md` in the project, so every task starts with `cra_resume`.

The cra entry is created and checked like this:

```json
{
  "mcpServers": {
    "cra": {
      "command": "/abs/path/to/python3",
      "args": ["-m", "cra_mcp.server", "--project", "/abs/path/my-paper", "--profile", "core"],
      "disabled": false,
      "autoApprove": ["cra_resume", "role_card", "skill_guide", "blackboard_read", "claim_list",
                      "evidence_list", "gate_check", "invariants_check"],
      "timeout": 120
    }
  }
}
```

The MCP Servers panel should show `cra` with a green dot and 15 tools.

## 3. Work

Use **Plan** mode to decide and **Act** mode to run. A good first message:

> Call cra_resume. Take the first task in next_tasks, load its role with role_card, do only that task, then
> call cra_resume again.

Tips for DeepSeek (and other non-Claude models):
- Keep the `core` profile. Long tool lists make wrong tool choices more likely.
- One task per turn. `next_tasks[i].do_not` tells the model what *not* to touch.
- When a tool answers `ok: false`, the reason is in `violations`. Ask the model to fix the cause rather
  than retry the same call. Typical causes: missing refs on a verdict, no log for an evidence row, or a
  gate that does not pass.
- Experiments: let the model write scripts under `falsify/<claim>/` or `results/<exp>/`, run them in Cline's
  terminal, then `evidence_add` with the log path. The server refuses rows without an existing log.
- Run `cra hook install` once, so commits that break the invariants are blocked whatever the model does.

## Alternative: Claude Code with DeepSeek

DeepSeek offers an Anthropic-compatible endpoint. Claude Code can run on it and keep the native agents,
skills and `/cra-*` commands. Put this in `~/.claude/settings.json`:

```json
{"env": {"ANTHROPIC_BASE_URL": "https://api.deepseek.com/anthropic",
         "ANTHROPIC_AUTH_TOKEN": "<your DeepSeek key>",
         "ANTHROPIC_MODEL": "<DeepSeek model id>"}}
```

Make sure no `ANTHROPIC_API_KEY` is set in your shell, because it would take precedence. Then run
`cra-mcp install --host claude-code --project …`.
