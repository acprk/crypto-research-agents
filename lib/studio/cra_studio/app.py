"""CRA Studio HTTP API + single-page UI (local only).

Security model: binds to 127.0.0.1; every /api call must carry the per-launch token
(``X-CRA-Token``, handed to the page via the URL fragment) and a localhost Host header, so other
web pages in the browser cannot drive the API (CSRF / DNS rebinding).  The API key is write-only
from the UI's point of view.
"""
from __future__ import annotations

import json
import os
import secrets
import urllib.error
import urllib.request

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import FileResponse, JSONResponse, Response
from starlette.routing import Route

from cra_core import CraError, Project
from cra_core.planner import next_actions
from cra_core.toolkit import init_project

from . import __version__, config
from .runner import Runner

STATIC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
LOCAL_HOSTS = ("127.0.0.1", "localhost", "[::1]")


def _err(msg: str, code: int = 400) -> JSONResponse:
    return JSONResponse({"ok": False, "error": msg}, status_code=code)


def create_app(token: str | None = None, runner: Runner | None = None) -> Starlette:
    token = token or secrets.token_urlsafe(24)
    runner = runner or Runner()

    def guard(fn):
        async def wrapped(request: Request):
            host = (request.headers.get("host") or "").rsplit(":", 1)[0]
            if host not in LOCAL_HOSTS:
                return _err("forbidden host", 421)
            if not secrets.compare_digest(request.headers.get("x-cra-token", ""), token):
                return _err("missing or wrong session token (reopen the URL printed by cra-studio)", 401)
            try:
                return await fn(request)
            except CraError as e:
                return _err(str(e))
            except (RuntimeError, FileNotFoundError, ValueError) as e:
                return _err(str(e))
        return wrapped

    async def body(request: Request) -> dict:
        try:
            return await request.json()
        except json.JSONDecodeError:
            return {}

    def project_arg(d: dict | None, request: Request) -> Project:
        p = (d or {}).get("project") or request.query_params.get("project") or ""
        if not p:
            raise ValueError("no project selected")
        p = os.path.abspath(os.path.expanduser(p))
        if not os.path.exists(os.path.join(p, "STATE.md")):
            raise ValueError(f"not a research project (no STATE.md): {p}")
        return Project(p, actor="studio")

    def remember(path: str) -> None:
        raw = config.load(raw=True)
        rec = [path] + [x for x in raw.get("recent_projects", []) if x != path]
        raw["recent_projects"] = rec[:12]
        config.save(raw)

    # ---------------------------------------------------------------- pages
    async def index(request: Request):
        return FileResponse(os.path.join(STATIC, "index.html"), headers={"Cache-Control": "no-store"})

    # ---------------------------------------------------------------- config
    @guard
    async def get_config(request: Request):
        return JSONResponse({"ok": True, "config": config.public(config.load()), "version": __version__})

    @guard
    async def put_config(request: Request):
        d = await body(request)
        raw = config.load(raw=True)
        prov = d.get("provider") or {}
        for k in ("preset", "base_url", "model"):
            if k in prov:
                raw["provider"][k] = str(prov[k]).strip()
        if prov.get("api_key"):                       # empty = keep the current key
            raw["provider"]["api_key"] = str(prov["api_key"]).strip()
        if prov.get("clear_api_key"):
            raw["provider"]["api_key"] = ""
        for k in ("approve", "profile", "language"):
            if k in d:
                raw[k] = str(d[k])
        if "max_steps" in d:
            raw["max_steps"] = max(1, min(200, int(d["max_steps"])))
        if "temperature" in d:
            raw["temperature"] = None if d["temperature"] in (None, "") else float(d["temperature"])
        if raw["approve"] not in ("destructive", "all", "none"):
            return _err("approve must be destructive|all|none")
        if raw["profile"] not in ("core", "full"):
            return _err("profile must be core|full")
        config.save(raw)
        return JSONResponse({"ok": True, "config": config.public(config.load())})

    @guard
    async def test_config(request: Request):
        cfg = config.load()
        base = config.effective_base_url(cfg)
        if not base:
            return _err("set a base URL or a preset first")
        key = cfg["provider"]["api_key"]
        req = urllib.request.Request(base.rstrip("/") + "/models", headers={"Authorization": f"Bearer {key}"} if key else {})
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                data = json.loads(r.read().decode())
            models = sorted(m.get("id", "") for m in data.get("data", []) if m.get("id"))
            return JSONResponse({"ok": True, "base_url": base, "models": models})
        except urllib.error.HTTPError as e:
            return _err(f"{base}/models answered HTTP {e.code}: {e.read().decode()[:300]}", 502)
        except (urllib.error.URLError, OSError, json.JSONDecodeError) as e:
            return _err(f"cannot reach {base}/models: {e}", 502)

    # ---------------------------------------------------------------- projects
    @guard
    async def projects(request: Request):
        rec = [p for p in config.load().get("recent_projects", []) if os.path.exists(os.path.join(p, "STATE.md"))]
        return JSONResponse({"ok": True, "recent": rec, "home": os.path.expanduser("~")})

    @guard
    async def open_project(request: Request):
        d = await body(request)
        path = os.path.abspath(os.path.expanduser(d.get("path", "")))
        created = []
        if d.get("create"):
            created = init_project(path)
        if not os.path.exists(os.path.join(path, "STATE.md")):
            return _err(f"no research project at {path} (tick 'create' to scaffold one)")
        remember(path)
        return JSONResponse({"ok": True, "project": path, "created": created})

    @guard
    async def status(request: Request):
        P = project_arg(None, request)
        st = P.status()
        st["next_tasks"] = next_actions(P)
        run = runner.active(P.root)
        st["active_run"] = run.id if run else None
        return JSONResponse({"ok": True, "status": st})

    @guard
    async def ledger(request: Request):
        P = project_arg(None, request)
        kind = request.path_params["kind"]
        if kind == "claims":
            data = P.claims_as_dicts()
        elif kind == "evidence":
            data = [{k: v for k, v in r.items() if k != "_line"} for r in P.evidence()]
        else:
            return _err("unknown ledger")
        return JSONResponse({"ok": True, "rows": data})

    @guard
    async def read_file(request: Request):
        P = project_arg(None, request)
        rel = request.query_params.get("path", "STATE.md")
        text = P.read(rel)
        if text is None:
            return _err(f"{rel} not found", 404)
        return JSONResponse({"ok": True, "path": rel, "text": text[:400_000]})

    @guard
    async def gate(request: Request):
        from cra_core.gates import check_gate
        P = project_arg(None, request)
        ph = request.query_params.get("phase") or P.phase()
        paper = "paper" if os.path.isdir(P.path("paper")) else None
        res = check_gate(P.root, ph, paper)
        return JSONResponse({"ok": True, "phase": ph, "results": [{"level": s, "message": m} for s, m in res]})

    # ---------------------------------------------------------------- agent runs
    @guard
    async def start_run(request: Request):
        d = await body(request)
        P = project_arg(d, request)
        task = (d.get("task") or "").strip() or "Call cra_resume and do the first task in next_tasks."
        r = runner.start(P.root, task, new_chat=bool(d.get("new_chat")))
        return JSONResponse({"ok": True, "run": r.id})

    @guard
    async def run_events(request: Request):
        r = runner.runs.get(request.path_params["rid"])
        if not r:
            return _err("unknown run", 404)
        return JSONResponse({"ok": True, **r.snapshot(int(request.query_params.get("after", 0)))})

    @guard
    async def run_decide(request: Request):
        r = runner.runs.get(request.path_params["rid"])
        if not r:
            return _err("unknown run", 404)
        d = await body(request)
        r.decide(bool(d.get("allow")))
        return JSONResponse({"ok": True})

    @guard
    async def run_stop(request: Request):
        r = runner.runs.get(request.path_params["rid"])
        if not r:
            return _err("unknown run", 404)
        r.stop()
        return JSONResponse({"ok": True})

    # ---------------------------------------------------------------- connect other hosts (MCP)
    @guard
    async def connect(request: Request):
        from cra_mcp.install import HOSTS, install
        P = project_arg(None, request)
        host = request.query_params.get("host", "")
        if host not in HOSTS:
            return JSONResponse({"ok": True, "hosts": HOSTS})
        if request.query_params.get("apply") == "1":
            lines = install(host, P.root, "core")
        else:
            lines = install(host, P.root, "core", dry_run=True)
        return JSONResponse({"ok": True, "host": host, "lines": lines})

    routes = [
        Route("/", index),
        Route("/api/config", get_config, methods=["GET"]),
        Route("/api/config", put_config, methods=["POST"]),
        Route("/api/config/test", test_config, methods=["POST"]),
        Route("/api/projects", projects),
        Route("/api/projects/open", open_project, methods=["POST"]),
        Route("/api/status", status),
        Route("/api/ledger/{kind}", ledger),
        Route("/api/file", read_file),
        Route("/api/gate", gate),
        Route("/api/run", start_run, methods=["POST"]),
        Route("/api/run/{rid}", run_events),
        Route("/api/run/{rid}/decide", run_decide, methods=["POST"]),
        Route("/api/run/{rid}/stop", run_stop, methods=["POST"]),
        Route("/api/connect", connect),
    ]
    app = Starlette(routes=routes)
    app.state.token = token
    app.state.runner = runner
    return app
