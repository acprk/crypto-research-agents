"""CRA Studio entry point -- one executable, several roles.

    cra-studio                         open the Studio in your browser (http://127.0.0.1:<port>/#t=<token>)
    cra-studio --port 8770 --no-browser
    cra-studio mcp --project <dir> [...]        run the cra MCP server (stdio / --http), same as `cra-mcp`
    cra-studio install --host <h> --project <dir>   write MCP config for Claude Code / Codex / Cline / ...
    cra-studio doctor --project <dir>
    cra-studio agent --model <id> --project <dir> "<task>"   terminal agent, same as `cra-agent`
    cra-studio cra <args>              the `cra` blackboard CLI
"""
from __future__ import annotations

import argparse
import os
import runpy
import socket
import sys
import threading
import webbrowser


def _free_port(preferred: int) -> int:
    for p in (preferred, 0):
        s = socket.socket()
        try:
            s.bind(("127.0.0.1", p))
            port = s.getsockname()[1]
            s.close()
            return port
        except OSError:
            s.close()
    raise RuntimeError("no free port")


def _run_script(argv: list[str]) -> int:
    """Used by the frozen app to execute bundled skill scripts (sys.executable is the app itself)."""
    path, rest = argv[0], argv[1:]
    sys.argv = [path, *rest]
    try:
        runpy.run_path(path, run_name="__main__")
    except SystemExit as e:
        return e.code if isinstance(e.code, int) else (0 if e.code is None else 1)
    return 0


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if argv[:1] == ["--run-script"]:
        return _run_script(argv[1:])
    if argv[:1] == ["mcp"]:
        from cra_mcp.server import main as mcp_main
        return mcp_main(argv[1:])
    if argv[:1] in (["install"], ["doctor"]):
        from cra_mcp.server import main as mcp_main
        return mcp_main(argv)
    if argv[:1] == ["agent"]:
        from cra_mcp.agent import main as agent_main
        return agent_main(argv[1:])
    if argv[:1] == ["cra"]:
        from cra_core.cli import main as cra_main
        return cra_main(argv[1:])

    from . import __version__
    ap = argparse.ArgumentParser(prog="cra-studio", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--port", type=int, default=int(os.environ.get("CRA_STUDIO_PORT", 8770)))
    ap.add_argument("--no-browser", action="store_true")
    ap.add_argument("--version", action="version", version=__version__)
    a = ap.parse_args(argv)

    import uvicorn
    from .app import create_app

    app = create_app()
    port = _free_port(a.port)
    url = f"http://127.0.0.1:{port}/#t={app.state.token}"
    print(f"CRA Studio {__version__}\n  open: {url}\n  (the link contains this session's token; keep it private; Ctrl+C to quit)",
          flush=True)
    if not a.no_browser:
        threading.Timer(1.0, lambda: webbrowser.open(url)).start()
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")
    return 0


if __name__ == "__main__":
    sys.exit(main())
