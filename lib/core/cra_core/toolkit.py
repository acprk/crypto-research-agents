"""Locate the crypto-research-agents toolkit checkout (templates, agents, skills)."""
from __future__ import annotations

import os
import sys


def toolkit_root() -> str:
    """``$CRA_HOME`` if set, else the toolkit bundled into a frozen app (PyInstaller), else the checkout
    this package was installed from (pip install -e)."""
    env = os.environ.get("CRA_HOME")
    cands = [env] if env else []
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        cands.append(os.path.join(sys._MEIPASS, "toolkit"))
    here = os.path.dirname(os.path.abspath(__file__))
    cands += [os.path.normpath(os.path.join(here, *[".."] * n)) for n in range(1, 5)]
    for c in cands:
        if c and os.path.isfile(os.path.join(c, "SPEC.md")) and os.path.isdir(os.path.join(c, "templates", "blackboard")):
            return c
    raise FileNotFoundError("cannot find the crypto-research-agents checkout; set CRA_HOME=<path to it>")


def init_project(target: str) -> list[str]:
    """Scaffold a research project (same as /cra-init).  Never overwrites existing files."""
    import shutil

    root = toolkit_root()
    os.makedirs(target, exist_ok=True)
    created = []
    bb = os.path.join(root, "templates", "blackboard")
    for f in sorted(os.listdir(bb)):
        dst = os.path.join(target, f)
        if not os.path.exists(dst):
            shutil.copy2(os.path.join(bb, f), dst)
            created.append(f)
    for d in ("results", "paper", "baselines", "lean", "falsify", "notes", ".cra"):
        os.makedirs(os.path.join(target, d), exist_ok=True)
    paper = os.path.join(target, "paper")
    if not os.listdir(paper):
        shutil.copytree(os.path.join(root, "templates", "paper"), paper, dirs_exist_ok=True)
        created.append("paper/")
    gi = os.path.join(target, ".cra", ".gitignore")
    if not os.path.exists(gi):
        with open(gi, "w") as fh:
            fh.write("lock\nmcp-secret\n")
    return created
