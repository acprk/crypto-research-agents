# PyInstaller spec: one-file CRA Studio executable (Studio GUI + cra MCP server + cra CLI + cra-agent).
# Build:  pip install -e lib/core -e lib/bench -e lib/mcp -e lib/studio pyinstaller
#         pyinstaller packaging/cra-studio.spec --noconfirm
# Output: dist/CRA-Studio(.exe)
import os
from PyInstaller.utils.hooks import collect_all, collect_data_files, collect_submodules, copy_metadata

ROOT = os.path.abspath(os.path.join(SPECPATH, ".."))

datas, binaries, hidden = [], [], []
# mcp: skip mcp.cli (needs the optional `typer`); everything else is collected
hidden += collect_submodules("mcp", filter=lambda name: not name.startswith("mcp.cli"))
datas += collect_data_files("mcp")
for dist in ("mcp", "cra-core", "cra-mcp", "cra-studio", "crbench", "pydantic", "starlette", "uvicorn"):
    try:
        datas += copy_metadata(dist)
    except Exception as exc:
        print(f"WARNING: no metadata for {dist}: {exc}")
for pkg in ("mcp_types", "uvicorn", "starlette", "pydantic", "sse_starlette", "jsonschema",
            "jsonschema_specifications", "cra_core", "cra_mcp", "cra_studio", "crbench"):
    try:
        d, b, h = collect_all(pkg)
        datas += d; binaries += b; hidden += h
    except Exception as exc:  # report, but keep building with what we have
        print(f"WARNING: collect_all({pkg!r}) failed: {exc}")
hidden += collect_submodules("uvicorn")

# the toolkit (agents, skills, templates, commands, phase playbook, references) -> <bundle>/toolkit
for rel in ("agents", "skills", "templates", "commands", "workflows", "references", "SPEC.md", "AGENTS.md", "CLAUDE.md"):
    src = os.path.join(ROOT, rel)
    if os.path.isdir(src):
        for d, _, files in os.walk(src):
            if "__pycache__" in d:
                continue
            for f in files:
                full = os.path.join(d, f)
                datas.append((full, os.path.join("toolkit", os.path.relpath(d, ROOT))))
    elif os.path.isfile(src):
        datas.append((src, "toolkit"))

a = Analysis([os.path.join(SPECPATH, "entry.py")], pathex=[ROOT], binaries=binaries, datas=datas,
             hiddenimports=hidden, excludes=["tkinter", "matplotlib", "numpy.tests", "PyQt5", "PySide6"])
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, a.binaries, a.datas, [], name="CRA-Studio", console=True, upx=False,
          disable_windowed_traceback=False)
