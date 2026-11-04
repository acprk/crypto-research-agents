"""Background agent runs for the Studio UI: events, approvals, stop, per-project conversation."""
from __future__ import annotations

import threading
import time
import traceback
import uuid

from cra_mcp.adapter import ToolBox
from cra_mcp.agent import ChatClient, run as agent_run

from . import config


class Run:
    def __init__(self, project: str, task: str):
        self.id = uuid.uuid4().hex[:12]
        self.project, self.task = project, task
        self.events: list[dict] = []
        self.status = "running"            # running | waiting_approval | done | stopped | error
        self.pending: dict | None = None
        self._decision: str | None = None
        self._cv = threading.Condition()
        self._stop = False
        self.messages: list[dict] = []

    # -- called from the agent thread
    def emit(self, e: dict) -> None:
        with self._cv:
            e = {"n": len(self.events), "ts": time.time(), **e}
            self.events.append(e)
            self._cv.notify_all()

    def ask(self, prompt: str) -> str:
        with self._cv:
            last = next((e for e in reversed(self.events) if e["type"] == "tool_call"), {})
            self.pending = {"name": last.get("name", "?"), "arguments": last.get("arguments", ""), "id": last.get("id")}
            self.status, self._decision = "waiting_approval", None
            self.emit({"type": "approval", **self.pending})
            while self._decision is None and not self._stop:
                self._cv.wait(timeout=1.0)
            d = self._decision or "n"
            self.pending, self.status = None, "running"
            return d

    # -- called from the UI
    def decide(self, allow: bool) -> None:
        with self._cv:
            self._decision = "y" if allow else "n"
            self._cv.notify_all()

    def stop(self) -> None:
        with self._cv:
            self._stop = True
            self._cv.notify_all()

    def snapshot(self, after: int = 0) -> dict:
        with self._cv:
            return {"id": self.id, "status": self.status, "pending": self.pending,
                    "events": self.events[after:], "next": len(self.events)}


class Runner:
    def __init__(self):
        self.runs: dict[str, Run] = {}
        self.history: dict[str, list[dict]] = {}     # project -> conversation (continue / new chat)
        self.lock = threading.Lock()

    def active(self, project: str) -> Run | None:
        return next((r for r in self.runs.values() if r.project == project and r.status in ("running", "waiting_approval")), None)

    def start(self, project: str, task: str, *, client: ChatClient | None = None, new_chat: bool = False) -> Run:
        with self.lock:
            if self.active(project):
                raise RuntimeError("an agent run is already active for this project")
            cfg = config.load()
            if client is None:
                p = cfg["provider"]
                base = config.effective_base_url(cfg)
                if not base or not p["model"]:
                    raise RuntimeError("set the model endpoint (base URL / preset) and the model id in Settings")
                client = ChatClient(base, p["api_key"], p["model"])
            r = Run(project, task)
            self.runs[r.id] = r
            if new_chat:
                self.history.pop(project, None)
        hist = self.history.get(project)

        def work():
            try:
                box = ToolBox(project, cfg.get("profile", "full"), actor=f"studio:{getattr(client, 'model', 'model')}")
                msgs = agent_run(task, box, client, max_steps=int(cfg.get("max_steps", 30)),
                                 approve=cfg.get("approve", "destructive"), temperature=cfg.get("temperature"),
                                 ask=r.ask, log=lambda *a: None, emit=r.emit, should_stop=lambda: r._stop,
                                 history=hist)
                self.history[project] = msgs[-200:] if len(msgs) <= 200 else [msgs[0]] + msgs[-199:]
                r.status = "stopped" if r._stop else "done"
            except BaseException as e:  # SystemExit from API errors included
                r.emit({"type": "error", "text": str(e) or e.__class__.__name__,
                        "trace": traceback.format_exc()[-2000:]})
                r.status = "error"

        threading.Thread(target=work, daemon=True, name=f"cra-run-{r.id}").start()
        return r
