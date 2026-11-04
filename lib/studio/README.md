# CRA Studio

CRA Studio is a local desktop workbench for crypto-research-agents.
- It ships as **one executable** that is also the `cra` MCP server, the `cra` CLI and `cra-agent`.
- The model endpoint is an open interface: any OpenAI-compatible base URL, API key and model id.

Guide: [docs/studio.md](../../docs/studio.md) · 中文: [docs/zh/studio.md](../../docs/zh/studio.md)

```bash
pip install -e lib/core -e lib/bench -e lib/mcp -e lib/studio
cra-studio                       # opens http://127.0.0.1:8770/#t=<session token>
pyinstaller packaging/cra-studio.spec --noconfirm   # -> dist/CRA-Studio(.exe)
```

Tests: `cd lib/studio && python3 -m pytest -q`.
