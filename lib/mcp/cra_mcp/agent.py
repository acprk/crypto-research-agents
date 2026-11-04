"""cra-agent -- drive a research project with any OpenAI-compatible Chat Completions API.

    export DEEPSEEK_API_KEY=...
    cra-agent --provider deepseek --model <model-id> --project ~/papers/my-paper \
              "Call cra_resume and do the first task."

    cra-agent --base-url https://my-gateway/v1 --api-key-env MY_KEY --model m "..."

    # OpenAI SDK convention: OPENAI_BASE_URL + OPENAI_API_KEY (e.g. an OpenAI-compatible relay)
    OPENAI_BASE_URL=https://relay.example/v1 OPENAI_API_KEY=... cra-agent --model m "..."

No MCP client is needed: the same tools run in-process (cra_mcp.adapter.ToolBox), with the same
validation and invariants. Destructive tools (phase_advance, file_write) ask for confirmation
in the terminal unless --approve none. Model IDs are not built in, because providers rename
them often; pass the one your account lists.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request

from .adapter import ToolBox
from .server import INSTRUCTIONS

# OpenAI-compatible base URLs (docs/integrations/COMPATIBILITY.md, researched 2026-11)
PROVIDERS = {
    "openai":     ("https://api.openai.com/v1", "OPENAI_API_KEY"),
    "deepseek":   ("https://api.deepseek.com", "DEEPSEEK_API_KEY"),
    "glm":        ("https://api.z.ai/api/paas/v4", "ZAI_API_KEY"),
    "glm-cn":     ("https://open.bigmodel.cn/api/paas/v4", "ZHIPUAI_API_KEY"),
    "kimi":       ("https://api.moonshot.ai/v1", "MOONSHOT_API_KEY"),
    "kimi-cn":    ("https://api.moonshot.cn/v1", "MOONSHOT_API_KEY"),
    "qwen":       ("https://dashscope-intl.aliyuncs.com/compatible-mode/v1", "DASHSCOPE_API_KEY"),
    "qwen-cn":    ("https://dashscope.aliyuncs.com/compatible-mode/v1", "DASHSCOPE_API_KEY"),
    "minimax":    ("https://api.minimax.io/v1", "MINIMAX_API_KEY"),
    "openrouter": ("https://openrouter.ai/api/v1", "OPENROUTER_API_KEY"),
    "ollama":     ("http://127.0.0.1:11434/v1", ""),
    "vllm":       ("http://127.0.0.1:8000/v1", ""),
}

SYSTEM = INSTRUCTIONS + (
    " You act through tools only. Work on one task at a time: call cra_resume, take the first entry of "
    "next_tasks, load its role with role_card, do it, then call cra_resume again. When a tool returns "
    "ok=false, read `violations` and fix the cause instead of repeating the call. You cannot run shell "
    "commands: when an experiment or proof check must be run, say exactly which command the human should run "
    "and stop. Finish with a short summary of what changed."
)


class ChatClient:
    def __init__(self, base_url: str, api_key: str, model: str, timeout: float = 300):
        self.url = base_url.rstrip("/") + "/chat/completions"
        self.key, self.model, self.timeout = api_key, model, timeout

    def complete(self, messages: list[dict], tools: list[dict], temperature: float | None) -> dict:
        body = {"model": self.model, "messages": messages, "tools": tools, "tool_choice": "auto"}
        if temperature is not None:
            body["temperature"] = temperature
        headers = {"Content-Type": "application/json"}
        if self.key:
            headers["Authorization"] = f"Bearer {self.key}"
        req = urllib.request.Request(self.url, data=json.dumps(body).encode(), headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as r:
                return json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            raise SystemExit(f"API error {e.code} from {self.url}: {e.read().decode()[:800]}")


def _assistant_message(msg: dict) -> dict:
    """Echo the assistant turn back verbatim enough for every provider (incl. DeepSeek/Kimi reasoning)."""
    out = {"role": "assistant", "content": msg.get("content") or ""}
    if msg.get("tool_calls"):
        out["tool_calls"] = [{"id": tc["id"], "type": "function",
                              "function": {"name": tc["function"]["name"],
                                           "arguments": tc["function"].get("arguments") or "{}"}}
                             for tc in msg["tool_calls"]]
    if msg.get("reasoning_content"):          # thinking-mode providers expect it back within a tool turn
        out["reasoning_content"] = msg["reasoning_content"]
    return out


def run(task: str, box: ToolBox, client: ChatClient, *, max_steps: int = 30, approve: str = "destructive",
        temperature: float | None = None, ask=input, log=print, emit=None, should_stop=lambda: False,
        history: list[dict] | None = None) -> list[dict]:
    """The tool loop.  ``emit(event: dict)`` receives structured events (for GUIs); ``ask(prompt)`` decides
    approvals (return "y" to allow); ``history`` continues an earlier conversation."""
    def ev(kind, **kw):
        if emit:
            emit({"type": kind, **kw})

    tools = box.tools("openai-compat")
    messages = list(history) if history else [{"role": "system", "content": SYSTEM}]
    messages.append({"role": "user", "content": task})
    for step in range(max_steps):
        if should_stop():
            ev("stopped", step=step)
            log("\n(stopped by the user)")
            return messages
        resp = client.complete(messages, tools, temperature)
        msg = resp["choices"][0]["message"]
        messages.append(_assistant_message(msg))
        calls = msg.get("tool_calls") or []
        if msg.get("reasoning_content"):
            ev("reasoning", text=msg["reasoning_content"])
        if msg.get("content"):
            ev("assistant", text=msg["content"])
            log(f"\n[assistant] {msg['content']}")
        if not calls:
            ev("done", steps=step + 1)
            return messages
        for tc in calls:
            name, args = tc["function"]["name"], tc["function"].get("arguments") or "{}"
            ev("tool_call", id=tc["id"], name=name, arguments=args)
            log(f"[tool] {name} {args[:300]}")
            need = approve == "all" and box.is_write(name) or approve == "destructive" and box.is_destructive(name)
            if need and ask(f"  allow {name}? [y/N] ").strip().lower() not in ("y", "yes"):
                result = json.dumps({"ok": False, "violations": ["the human declined this call"],
                                     "next_actions": ["explain what you wanted to do and ask the human"]})
            else:
                result = box.call(name, args)
            ev("tool_result", id=tc["id"], name=name, result=result[:20000])
            log(f"  -> {result[:300]}{'...' if len(result) > 300 else ''}")
            messages.append({"role": "tool", "tool_call_id": tc["id"], "content": result})
    ev("limit", steps=max_steps)
    log(f"\n(stopped after {max_steps} steps; run again to continue -- state is on the blackboard)")
    return messages


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="cra-agent", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("task", nargs="?", default="Call cra_resume and do the first task in next_tasks.")
    ap.add_argument("--provider", choices=sorted(PROVIDERS), help="preset base URL + API-key variable")
    ap.add_argument("--base-url", help="any OpenAI-compatible endpoint (overrides --provider)")
    ap.add_argument("--api-key-env", help="environment variable holding the API key")
    ap.add_argument("--model", default=os.environ.get("CRA_MODEL"), help="model id as listed by your provider ($CRA_MODEL)")
    ap.add_argument("--list-models", action="store_true", help="print the endpoint's /models and exit")
    ap.add_argument("--project", default=os.environ.get("CRA_PROJECT", "."))
    ap.add_argument("--profile", default="core", choices=["core", "full", "remote"])
    ap.add_argument("--max-steps", type=int, default=30)
    ap.add_argument("--approve", default="destructive", choices=["destructive", "all", "none"],
                    help="which tool calls need a y/N confirmation (default: phase_advance, file_write)")
    ap.add_argument("--temperature", type=float, default=None)
    ap.add_argument("--transcript", help="write the full message list as JSON here")
    a = ap.parse_args(argv)
    base, key_env = PROVIDERS.get(a.provider, (None, None)) if a.provider else (None, None)
    if not a.base_url and a.provider in (None, "openai") and os.environ.get("OPENAI_BASE_URL"):
        base, key_env = os.environ["OPENAI_BASE_URL"], key_env or "OPENAI_API_KEY"   # OpenAI SDK convention
    base = a.base_url or base
    if not base:
        ap.error("give --provider, --base-url, or set OPENAI_BASE_URL")
    key_env = a.api_key_env or key_env or ""
    key = os.environ.get(key_env, "") if key_env else ""
    if key_env and not key:
        ap.error(f"set ${key_env} to your API key")
    if a.list_models:
        req = urllib.request.Request(base.rstrip("/") + "/models",
                                     headers={"Authorization": f"Bearer {key}"} if key else {})
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                data = json.loads(r.read().decode())
        except (urllib.error.URLError, OSError) as e:
            ap.exit(2, f"cannot reach {base}/models: {e}\n")
        for m in data.get("data", []):
            print(m.get("id"))
        return 0
    if not a.model:
        ap.error("give --model (see --list-models)")
    box = ToolBox(a.project, a.profile, actor=f"cra-agent:{a.model}")
    msgs = run(a.task, box, ChatClient(base, key, a.model), max_steps=a.max_steps, approve=a.approve,
               temperature=a.temperature)
    if a.transcript:
        with open(a.transcript, "w", encoding="utf-8") as fh:
            json.dump(msgs, fh, indent=1, ensure_ascii=False)
    return 0


if __name__ == "__main__":
    sys.exit(main())
