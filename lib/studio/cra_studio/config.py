"""User settings: the model endpoint is an open interface -- any OpenAI-compatible base URL + key + model.

Stored in the per-user config dir (never in a project, never in git), file mode 0600:
  Windows  %APPDATA%\\cra\\studio.json
  macOS    ~/Library/Application Support/cra/studio.json
  Linux    $XDG_CONFIG_HOME/cra/studio.json  (default ~/.config/cra/studio.json)
Environment variables fill empty fields: OPENAI_BASE_URL, OPENAI_API_KEY, CRA_MODEL.
"""
from __future__ import annotations

import json
import os
import sys

from cra_mcp.agent import PROVIDERS

DEFAULTS = {
    "provider": {"preset": "openai", "base_url": "", "api_key": "", "model": ""},
    "approve": "destructive",          # destructive | all | none
    "max_steps": 30,
    "temperature": None,
    "profile": "full",
    "recent_projects": [],
    "language": "",                    # "" = follow the browser
}


def config_dir() -> str:
    if os.environ.get("CRA_CONFIG_DIR"):
        return os.environ["CRA_CONFIG_DIR"]
    if sys.platform == "win32":
        return os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "cra")
    if sys.platform == "darwin":
        return os.path.expanduser("~/Library/Application Support/cra")
    return os.path.join(os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~/.config")), "cra")


def path() -> str:
    return os.path.join(config_dir(), "studio.json")


def load(raw: bool = False) -> dict:
    """Saved settings; unless ``raw``, empty provider fields are filled from the environment
    (raw is what gets saved back, so environment secrets are never written to disk)."""
    cfg = json.loads(json.dumps(DEFAULTS))
    try:
        with open(path(), encoding="utf-8") as fh:
            saved = json.load(fh)
        for k, v in saved.items():
            if k == "provider" and isinstance(v, dict):
                cfg["provider"].update(v)
            elif k in cfg:
                cfg[k] = v
    except (FileNotFoundError, json.JSONDecodeError):
        pass
    if raw:
        return cfg
    p = cfg["provider"]
    p["base_url"] = p["base_url"] or os.environ.get("OPENAI_BASE_URL", "")
    p["api_key"] = p["api_key"] or os.environ.get("OPENAI_API_KEY", "")
    p["model"] = p["model"] or os.environ.get("CRA_MODEL", "")
    return cfg


def save(cfg: dict) -> None:
    os.makedirs(config_dir(), exist_ok=True)
    tmp = path() + ".tmp"
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        json.dump(cfg, fh, indent=1, ensure_ascii=False)
    os.replace(tmp, path())


def effective_base_url(cfg: dict) -> str:
    p = cfg["provider"]
    return p["base_url"] or PROVIDERS.get(p["preset"], ("", ""))[0]


def public(cfg: dict) -> dict:
    """Config for the UI: the key is never sent back, only whether one is set."""
    out = json.loads(json.dumps(cfg))
    key = out["provider"].pop("api_key", "")
    out["provider"]["api_key_set"] = bool(key)
    out["provider"]["api_key_hint"] = (key[:3] + "…" + key[-4:]) if len(key) > 10 else ("set" if key else "")
    out["provider"]["effective_base_url"] = effective_base_url(cfg)
    out["presets"] = {k: v[0] for k, v in PROVIDERS.items()}
    out["config_path"] = path()
    return out
