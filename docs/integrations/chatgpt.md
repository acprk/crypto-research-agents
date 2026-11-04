# ChatGPT and the OpenAI API: interface

[中文版](../zh/integrations.md#chatgpt--openai-接口适配) · [Back to integrations](README.md)

This page describes the interface cra exposes for the OpenAI family. How you make the HTTP endpoint
reachable (reverse proxy, existing gateway, hosting) is your choice and is out of scope here.

## Three ways in

| You use | Interface | cra side |
|---|---|---|
| **ChatGPT** (developer mode → app) | remote MCP over Streamable HTTP | `cra-mcp --http --profile remote` |
| **OpenAI Responses API / Agents SDK** | remote MCP tool (`"type": "mcp"`) **or** function tools | `cra-mcp --http`, or `cra-mcp --export openai-responses` |
| **Chat Completions** (OpenAI, or any OpenAI-compatible API: DeepSeek, GLM, Qwen, Kimi, MiniMax, vLLM, Ollama) | function calling | `cra-mcp --export openai` / `openai-compat`, `cra_mcp.adapter.ToolBox`, or the ready loop `cra-agent` |

## 1. ChatGPT: what the server provides

| ChatGPT requirement | cra |
|---|---|
| Remote MCP, Streamable HTTP | `cra-mcp --project <dir> --http [--host] [--port 8765] [--path /mcp]` |
| Authentication: "No authentication" or OAuth (no static headers) | `--secret-path` makes the URL path the credential. It is persisted in `.cra/mcp-secret` (0600, git-ignored) so the app URL survives restarts; rotate with `--new-secret`. Bearer tokens (`$CRA_MCP_TOKEN`) are for API clients that can send headers. |
| Host / Origin checks behind a public hostname | `--public-url https://<your host>` (or `--allow-host <host>`) adds the host to the DNS-rebinding allow-list. Origins `https://chatgpt.com` and `https://chat.openai.com` are allowed. Requests from unknown hosts get 421. |
| Tools without `readOnlyHint` count as writes and need confirmation | Every tool declares `readOnlyHint` / `destructiveHint` / `idempotentHint` / `openWorldHint` |
| Deep research / company knowledge need read-only `search(query)` and `fetch(id)` returning **one text item holding JSON** (`{"results":[{id,title,url}]}` / `{id,title,text,url,metadata}`) | `remote` profile; format checked by `tests/test_server.py` |
| No local filesystem in ChatGPT | `remote` profile adds `file_list` / `file_read` / `file_write`, sandboxed to the project. The ledgers are refused there and must go through the typed tools. |
| Server instructions: first 512 characters self-contained | yes |
| Cached tool definitions | after updating cra, press Refresh on the app in ChatGPT |

App settings in ChatGPT: MCP server URL = `https://<your host>/mcp/<secret>` (printed after `>>>`),
authentication = No authentication. ChatGPT cannot run shell commands, so experiments run on your machine.
ChatGPT then records the log with `evidence_add`, which only accepts logs that exist in the project.

## 2. Responses API

Remote MCP tool. The server must be reachable from OpenAI.

```json
{"type": "mcp", "server_label": "cra", "server_url": "https://<host>/mcp",
 "headers": {"Authorization": "Bearer <CRA_MCP_TOKEN>"},
 "allowed_tools": ["cra_resume", "claim_list", "claim_register", "claim_verdict", "evidence_add", "gate_check"],
 "require_approval": {"never": {"tool_names": ["cra_resume", "claim_list", "gate_check"]}}}
```

Or function tools, executed locally with no network endpoint at all:

```bash
cra-mcp --export openai-responses --profile core > cra-tools.json     # flat {"type":"function","name",...}, strict
```

## 3. Chat Completions and OpenAI-compatible APIs

`cra-mcp --export openai` emits strict-mode definitions. `openai-compat` emits the same tools without `strict`,
because several compatible providers accept `strict` only on beta endpoints. Strict-mode details handled:
- every property is listed in `required`;
- optional properties are nullable, and a nullable enum lists `null`;
- defaults move into the description;
- `null` arguments are dropped before execution, so defaults apply.

Execute the model's tool calls with `ToolBox`. It uses the same in-process server, so the validation and
invariants are identical to MCP:

```python
from cra_mcp.adapter import ToolBox
box = ToolBox("~/papers/my-paper", profile="core")
tools = box.tools("openai-compat")            # or "openai" (strict)
# ... resp = client.chat.completions.create(model=..., messages=..., tools=tools)
for tc in resp.choices[0].message.tool_calls or []:
    messages.append({"role": "tool", "tool_call_id": tc.id,
                     "content": box.call(tc.function.name, tc.function.arguments)})
```

Or use the ready-made loop. It has no extra dependencies and asks for confirmation before destructive
tools:

```bash
export DEEPSEEK_API_KEY=...        # or OPENAI_API_KEY, ZAI_API_KEY, MOONSHOT_API_KEY, DASHSCOPE_API_KEY, ...
cra-agent --provider deepseek --model <model id> --project ~/papers/my-paper "Call cra_resume and do the first task."
cra-agent --base-url https://<any-openai-compatible>/v1 --api-key-env MY_KEY --model <id> "..."
```

| Provider preset | Base URL | Key variable |
|---|---|---|
| `openai` | `https://api.openai.com/v1` | `OPENAI_API_KEY` |
| `deepseek` | `https://api.deepseek.com` | `DEEPSEEK_API_KEY` |
| `glm` / `glm-cn` | `https://api.z.ai/api/paas/v4` / `https://open.bigmodel.cn/api/paas/v4` | `ZAI_API_KEY` / `ZHIPUAI_API_KEY` |
| `kimi` / `kimi-cn` | `https://api.moonshot.ai/v1` / `https://api.moonshot.cn/v1` | `MOONSHOT_API_KEY` |
| `qwen` / `qwen-cn` | `https://dashscope-intl.aliyuncs.com/compatible-mode/v1` / `https://dashscope.aliyuncs.com/compatible-mode/v1` | `DASHSCOPE_API_KEY` |
| `minimax` | `https://api.minimax.io/v1` | `MINIMAX_API_KEY` |
| `openrouter`, `ollama`, `vllm` | see `cra-agent --help` | |

Behaviour that matters for non-OpenAI providers:
- `tool_choice` is always `auto`, which DeepSeek's thinking mode requires.
- No `temperature` is sent unless you pass `--temperature`, because some thinking modes fix it.
- `reasoning_content` is echoed back within a tool turn (DeepSeek / Kimi thinking mode).
- Model IDs are not built in: pass the ID your account lists.

## Test coverage (no network, no accounts)

`lib/mcp/tests/` checks:
- strict-schema rules for every tool and profile;
- the Responses, Gemini and Anthropic formats;
- `search`/`fetch` result shape;
- an HTTP session with a public Host and ChatGPT Origin, with foreign Host/Origin rejected and the secret
  path required;
- `ToolBox` refusals;
- the `cra-agent` loop against a scripted model, including tool-call ids, approval of destructive calls and
  the `reasoning_content` echo;
- the client's wire format against a local fake OpenAI-compatible server.

Not covered: live calls to ChatGPT or any provider API.
