"""Function-calling adapter: the cra tools for APIs without MCP.

* ``convert(tools, fmt)`` turns the MCP tool list into the tool format of a model API:

  ===================  =================================================================
  ``openai``           Chat Completions, strict mode (``{"type":"function","function":{...}}``)
  ``openai-responses`` Responses API, strict mode (flat ``{"type":"function","name":...}``)
  ``openai-compat``    Chat Completions, non-strict -- for OpenAI-compatible APIs
                       (DeepSeek, GLM, Qwen, Kimi, MiniMax, vLLM, Ollama, ...)
  ``anthropic``        Messages API ``{"name","description","input_schema"}``
  ``gemini``           ``{"functionDeclarations": [...]}`` (OpenAPI-3.0 subset)
  ===================  =================================================================

* ``ToolBox`` executes a model's tool call (name + JSON arguments) in-process through the same
  MCP server object, so validation and invariants are identical to the MCP path::

      box = ToolBox("~/papers/my-paper", profile="core")
      tools = box.tools("openai-compat")                 # pass to chat.completions
      text = box.call(name, arguments_json)              # feed back as the tool message
"""
from __future__ import annotations

import asyncio
import copy
import json
import os

FORMATS = ("openai", "openai-responses", "openai-compat", "anthropic", "gemini")
_DROP = ("title", "$schema", "additionalProperties")


def _prop(v: dict, *, strict: bool, gemini: bool, required: bool) -> dict:
    v = {k: x for k, x in v.items() if k not in _DROP}
    default = v.pop("default", None) if (strict or gemini) else v.get("default")
    if (strict or gemini) and default not in (None, "") and "description" not in v:
        v["description"] = f"default: {json.dumps(default)}"
    if strict and not required:
        t = v.get("type")
        v["type"] = [t, "null"] if isinstance(t, str) else t
        if "enum" in v and None not in v["enum"]:
            v["enum"] = [*v["enum"], None]           # strict mode: a nullable enum must list null
    if v.get("type") == "array" and isinstance(v.get("items"), dict):
        v["items"] = _prop(v["items"], strict=strict, gemini=gemini, required=True)
    return v


def clean_schema(schema: dict, *, strict: bool = False, gemini: bool = False) -> dict:
    s = {k: v for k, v in copy.deepcopy(schema).items() if k not in _DROP}
    req = set(s.get("required", []))
    props = {k: _prop(v, strict=strict, gemini=gemini, required=k in req) for k, v in s.get("properties", {}).items()}
    s["type"] = "object"
    s["properties"] = props
    if strict:
        s["required"] = list(props)
        s["additionalProperties"] = False
    elif not req:
        s.pop("required", None)
    return s


def convert(tools: list[dict], fmt: str) -> list[dict]:
    if fmt not in FORMATS:
        raise ValueError(f"format must be one of {FORMATS}")
    desc = lambda t: t["description"][:1024]
    if fmt == "openai":
        return [{"type": "function", "function": {"name": t["name"], "description": desc(t), "strict": True,
                                                  "parameters": clean_schema(t["inputSchema"], strict=True)}}
                for t in tools]
    if fmt == "openai-responses":
        return [{"type": "function", "name": t["name"], "description": desc(t), "strict": True,
                 "parameters": clean_schema(t["inputSchema"], strict=True)} for t in tools]
    if fmt == "openai-compat":
        return [{"type": "function", "function": {"name": t["name"], "description": desc(t),
                                                  "parameters": clean_schema(t["inputSchema"])}} for t in tools]
    if fmt == "anthropic":
        return [{"name": t["name"], "description": t["description"], "input_schema": clean_schema(t["inputSchema"])}
                for t in tools]
    return [{"functionDeclarations": [{"name": t["name"], "description": t["description"],
                                       "parameters": clean_schema(t["inputSchema"], gemini=True)} for t in tools]}]


class ToolBox:
    """Run cra tools from any function-calling loop (no MCP client needed)."""

    def __init__(self, project: str, profile: str = "core", actor: str = "agent"):
        from .server import build_server
        self.project = os.path.abspath(os.path.expanduser(project))
        self.server = build_server(self.project, profile, actor)
        listed = asyncio.run(self.server.list_tools())
        self.schemas = [{"name": t.name, "description": t.description or "",
                         "inputSchema": t.input_schema if hasattr(t, "input_schema") else t.inputSchema,
                         "annotations": (t.annotations.model_dump(by_alias=True, exclude_none=True)
                                         if t.annotations else {})} for t in listed]
        self.by_name = {t["name"]: t for t in self.schemas}

    def tools(self, fmt: str = "openai-compat") -> list[dict]:
        return convert(self.schemas, fmt)

    def is_write(self, name: str) -> bool:
        a = self.by_name.get(name, {}).get("annotations", {})
        return not a.get("readOnlyHint", False)

    def is_destructive(self, name: str) -> bool:
        return bool(self.by_name.get(name, {}).get("annotations", {}).get("destructiveHint", False))

    def call(self, name: str, arguments: str | dict | None) -> str:
        """Execute one tool call; always returns a JSON string suitable for a tool-result message."""
        if name not in self.by_name:
            return json.dumps({"ok": False, "violations": [f"unknown tool {name!r}"],
                               "next_actions": ["call cra_resume to see what to do next"]})
        try:
            args = json.loads(arguments) if isinstance(arguments, str) and arguments.strip() else (arguments or {})
        except json.JSONDecodeError as e:
            return json.dumps({"ok": False, "violations": [f"arguments are not valid JSON: {e}"]})
        # strict-mode clients send null for omitted optional parameters: drop them so defaults apply
        args = {k: v for k, v in args.items() if v is not None}
        try:
            res = asyncio.run(self.server.call_tool(name, args))
        except Exception as e:  # argument validation errors etc. -> readable refusal for the model
            msg = str(e).split("For further information")[0].strip()
            return json.dumps({"ok": False, "violations": [msg[:2000]],
                               "next_actions": ["fix the arguments according to the tool's parameter schema"]})
        texts = [c.text for c in res.content if getattr(c, "type", "") == "text"]
        out = texts[0] if len(texts) == 1 else json.dumps({"content": texts})
        if getattr(res, "is_error", False) or getattr(res, "isError", False):
            return json.dumps({"ok": False, "violations": [out[:2000]]})
        return out
