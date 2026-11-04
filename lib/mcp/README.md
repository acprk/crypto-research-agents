# cra-mcp — MCP server for crypto-research-agents

This package serves the research blackboard and the toolkit's checkers as Model Context Protocol tools.
- The default `core` profile has 15 tools; `full` has 24 and `remote` has 21.
- Transports: stdio, or Streamable HTTP with a bearer token or a secret path.
- All rules are implemented in `cra_core`.

```bash
pip install -e lib/core -e lib/mcp
cra-mcp install --host claude-code|codex|cline|gemini|cursor|vscode|chatgpt|... --project <dir>
cra-mcp doctor --project <dir>
cra-mcp --project <dir>                       # stdio
cra-mcp --project <dir> --http                # http://127.0.0.1:8765/mcp ($CRA_MCP_TOKEN = bearer token)
cra-mcp --list-tools --profile full           # tool names + JSON schemas
cra-mcp --export openai|anthropic|gemini      # function-calling definitions for non-MCP code
```

User guide: [docs/integrations/README.md](../../docs/integrations/README.md) (中文:
[docs/zh/integrations.md](../../docs/zh/integrations.md)).
Per-host facts and design rules: [COMPATIBILITY.md](../../docs/integrations/COMPATIBILITY.md).
Tests (schema portability, the full workflow over MCP, stdio, HTTP auth, installers):
`cd lib/mcp && python3 -m pytest -q`.

The server currently needs the toolkit checkout for templates, agents and skills: `pip install -e`, or set
`CRA_HOME`. A self-contained PyPI wheel (`uvx cra-mcp`) and a Claude Desktop `.mcpb` bundle are planned (M6).
