# 在各 AI 平台上使用 crypto-research-agents

[English](../integrations/README.md) · [平台兼容性参考（来源与限制）](../integrations/COMPATIBILITY.md)

整个研究流程被封装成 MCP 服务器 **`cra-mcp`**，任何支持 MCP 的宿主都能直接用。
- 默认的 `core` 档提供 15 个工具：断点续跑、claim、证据、阶段门、阶段推进、决策记录、引用核验、角色卡、skill 流程。
- 工作流的规则在服务器里用代码执行，所以不管换哪个模型、哪个 IDE，约束都一样。
- 服务器本身不调用任何大模型，也不需要 API key。

## 1. 安装（一次）

```bash
git clone <本仓库> ~/crypto-research-agents
cd ~/crypto-research-agents
pip install -e lib/core -e lib/bench -e lib/cryptomath -e lib/mcp     # Python >= 3.10
cra init ~/papers/my-paper                                            # 新建一个研究项目
cra-mcp doctor --project ~/papers/my-paper                            # 自检
```

## 2. 接入你的平台

```bash
cra-mcp install --host <平台> --project ~/papers/my-paper    # 加 --dry-run 可以先预览，不写文件
```

| 你用的平台 | `--host` | 效果 |
|---|---|---|
| Claude Code | `claude-code` | 写 `.mcp.json` 和 `CLAUDE.md`。首次使用时批准一次，用 `/mcp` 查看。可选：`./install.sh <项目>` 安装原生的 agents、skills 和 `/cra-*` 命令 |
| Claude Desktop | `claude-desktop` | 打印 `claude_desktop_config.json` 的配置项，粘贴后重启应用 |
| claude.ai 网页版 | `claude-ai` | 打印远程连接器的步骤（见第 3 节） |
| **ChatGPT** | `chatgpt` | 打印开发者模式 App 的步骤（见第 3 节） |
| Codex CLI / IDE 插件 | `codex` | 打印 `config.toml` 配置段和 `codex mcp add …` 命令；写 `AGENTS.md` |
| Gemini CLI | `gemini` | 写 `.gemini/settings.json` 和 `GEMINI.md` |
| 通义 Qwen Code | `qwen` | 写 `.qwen/settings.json` 和 `QWEN.md` |
| **Cline**（如配 DeepSeek） | `cline` | 打印 `cline_mcp_settings.json` 的配置项；写 `.clinerules/cra.md`（见下文 Cline + DeepSeek 一节） |
| Roo Code / Kilo Code | `roo` / `kilo` | 写 `.roo/mcp.json` / `.kilocode/mcp.json` |
| Cursor | `cursor` | 写 `.cursor/mcp.json` 和 `.cursor/rules/cra.mdc` |
| Windsurf | `windsurf` | 打印 `mcp_config.json` 的配置项 |
| VS Code + Copilot | `vscode` | 写 `.vscode/mcp.json`（注意 key 是 `servers`）和 `.github/copilot-instructions.md` |
| JetBrains（Junie / AI Assistant） | `jetbrains` | 写 `.junie/mcp/mcp.json` |
| Zed | `zed` | 打印 `context_servers` 的配置项 |
| OpenCode | `opencode` | 写 `opencode.json`（key 是 `mcp`） |
| Continue | `continue` | 写 `.continue/mcpServers/cra.yaml` |
| Trae / Cherry Studio / LM Studio | `trae` / `cherry-studio` / `lmstudio` | 写入或打印 `mcpServers` 配置项 |
| 其他（Kimi Code CLI、iFlow 等） | `generic` | 打印通用的 `mcpServers` JSON |

生成的配置使用 Python 解释器的绝对路径，所以 PATH 很短的 GUI 应用也能正常启动服务器。
- 项目目录里的配置文件：只增加或替换 `cra` 这一项，其他内容保留。
- 用户主目录下的全局配置：一律不自动修改，只打印需要粘贴的内容。

接好后，在对话里说：**"调用 cra_resume，然后继续这个项目"**。

## 3. ChatGPT、claude.ai 与 OpenAI API

完整的接口说明见下文"ChatGPT / OpenAI 接口适配"一节（英文版：[chatgpt.md](../integrations/chatgpt.md)）。

- **ChatGPT / claude.ai**：走远程 MCP。运行 `cra-mcp --project <目录> --http --profile remote --secret-path --public-url https://<你的域名>`，把打印出的 `>>>` 那行 URL 填到 App 或连接器的地址栏，认证选"无"。`remote` 档额外提供限定在项目目录内的文件工具，以及符合 ChatGPT 规范的 `search`/`fetch`。服务怎样对外可达由你自己决定。
- **Responses API / Agents SDK**：可以作为远程 MCP 工具接入（`"type": "mcp"`，bearer token 取自 `$CRA_MCP_TOKEN`），也可以用 `cra-mcp --export openai-responses` 导出为本地函数工具。

## 4. Chat Completions 与 OpenAI 兼容接口（ChatGPT API、DeepSeek、GLM、通义、Kimi 等）

```bash
cra-mcp --export openai          # strict 模式的函数定义（Chat Completions）
cra-mcp --export openai-compat   # 同样的工具，但不带 strict（适用于各家兼容接口）
cra-agent --provider deepseek --model <模型id> --project <目录> "调用 cra_resume，完成第一项任务"
```

如果要接进你自己写的循环，把模型返回的每个 tool call 交给 `cra_mcp.adapter.ToolBox(project).call(name, arguments)` 执行即可。它和 MCP 路径用的是同一套参数校验和不变量。

## 5. 其他函数调用接口

```bash
cra-mcp --export anthropic       # Messages API 的 input_schema
cra-mcp --export gemini          # functionDeclarations（OpenAPI 3.0 子集）
```

同样的操作在命令行里也能用 `cra …` 完成（见 `cra --help`）。

## 6. 工具档位

| 档位 | 工具数 | 适用场景 |
|---|---|---|
| `core`（默认） | 15 | 任何宿主；最适合较小或较便宜的模型，以及有工具数量上限的宿主 |
| `full` | 24 | 本地深度使用：加上 ePrint 检索、文献矩阵检查、core-SVP 估计、audit-tex、匿名检查、文件工具 |
| `remote` | 21 | ChatGPT / claude.ai：core + 文件访问 + `search`/`fetch` |

## 7. 不变量如何在所有平台上生效

- **服务器层**：
  - 记录 verdict 必须附证据和引用编号。
  - 证据必须指向真实存在的日志，并记录日志的哈希。
  - 阶段门不过就不能推进阶段。
  - `file_write` 拒绝直接修改 CLAIMS、EVIDENCE、DECISIONS 这几个账本文件。
- **git 钩子**：在项目里运行一次 `cra hook install`。之后，只要论文引用了未通过证伪的 claim（`\claimref{C9}`）或不存在的证据行，或者日志在登记后被改过，提交就会被拒绝。这一层与使用哪个 IDE 或 agent 无关。
- **阶段门**：`gate_check`（命令行是 `cra gate P<k>`）负责每个阶段门里能机械检查的部分。

---

## ChatGPT / OpenAI 接口适配

本节只讲接口本身。服务怎样对外可达（反向代理、现有网关、托管）由你决定，不在本文范围内。

**ChatGPT 的要求与 cra 的对应**

| ChatGPT 的要求 | cra 的实现 |
|---|---|
| 远程 MCP，Streamable HTTP | `cra-mcp --project <目录> --http [--host] [--port 8765] [--path /mcp]` |
| 认证只能是"无认证"或 OAuth，不能带自定义 header | `--secret-path`：URL 路径本身就是凭证。密钥保存在 `.cra/mcp-secret`（权限 0600，不进 git），重启后不变，App 地址不会失效；用 `--new-secret` 更换。能带 header 的 API 客户端可以用 bearer token（`$CRA_MCP_TOKEN`） |
| 通过公网域名访问时的 Host / Origin 校验 | `--public-url https://<你的域名>`（或 `--allow-host <域名>`）把该域名加入允许列表；允许的 Origin 包括 `https://chatgpt.com` 和 `https://chat.openai.com`；来自其他域名的请求返回 421 |
| 没有 `readOnlyHint` 的工具一律当作写入，需要用户确认 | 每个工具都声明了 `readOnlyHint` / `destructiveHint` / `idempotentHint` / `openWorldHint` |
| 深度研究 / 公司知识模式需要只读的 `search(query)` 和 `fetch(id)`，且必须**只返回一个 text 内容项，内容是 JSON 字符串** | `remote` 档已提供，返回格式由测试保证 |
| ChatGPT 没有本地文件系统 | `remote` 档提供 `file_list` / `file_read` / `file_write`，只能访问项目目录；CLAIMS、EVIDENCE、DECISIONS 这几个账本不能用 `file_write` 改，必须走专门的工具 |
| 服务器说明的前 512 个字符要能独立看懂 | 已满足 |
| ChatGPT 会缓存工具定义 | 更新 cra 后，在 ChatGPT 的 App 设置里点一次刷新 |

在 ChatGPT 的 App 设置中：MCP 服务器地址填 `https://<你的域名>/mcp/<密钥>`（就是 `>>>` 那一行），认证选"无"。ChatGPT 不能执行命令，实验要在你自己的电脑上跑，跑完后由 ChatGPT 用 `evidence_add` 登记日志；该工具只接受项目里真实存在的日志。

**Responses API**：作为远程 MCP 工具使用的写法：
```json
{"type": "mcp", "server_label": "cra", "server_url": "https://<域名>/mcp",
 "headers": {"Authorization": "Bearer <CRA_MCP_TOKEN>"},
 "require_approval": {"never": {"tool_names": ["cra_resume", "claim_list", "gate_check"]}}}
```
也可以完全不暴露服务：用 `cra-mcp --export openai-responses` 导出函数工具（扁平格式，strict 模式），在本地执行。

**Chat Completions / OpenAI 兼容接口**：
- `--export openai` 输出 strict 模式的定义。`openai-compat` 输出同样的工具但不带 `strict`，因为不少兼容接口只在 beta 端点上支持 `strict`。
- 为满足 strict 模式，导出时做了这些处理：所有参数都列进 `required`；可选参数改为可为 null，可为 null 的枚举里加上 `null`；默认值移到参数说明里；执行前丢掉值为 null 的参数，让默认值生效。
- 要接进你自己的循环，把每个 tool call 交给 `ToolBox(project).call(name, arguments)` 执行，返回值作为 tool 消息回传给模型。

也可以直接用现成的 `cra-agent`。它只用 Python 标准库，执行破坏性工具（`phase_advance`、`file_write`）前会在终端请求确认：

```bash
export DEEPSEEK_API_KEY=...
cra-agent --provider deepseek --model <模型id> --project ~/papers/my-paper "调用 cra_resume，完成第一项任务"
```

| 预设 | 接口地址 | API key 环境变量 |
|---|---|---|
| `openai` | `https://api.openai.com/v1` | `OPENAI_API_KEY` |
| `deepseek` | `https://api.deepseek.com` | `DEEPSEEK_API_KEY` |
| `glm` / `glm-cn` | `https://api.z.ai/api/paas/v4` / `https://open.bigmodel.cn/api/paas/v4` | `ZAI_API_KEY` / `ZHIPUAI_API_KEY` |
| `kimi` / `kimi-cn` | `https://api.moonshot.ai/v1` / `https://api.moonshot.cn/v1` | `MOONSHOT_API_KEY` |
| `qwen` / `qwen-cn` | DashScope 国际站 / 国内站的 `compatible-mode/v1` | `DASHSCOPE_API_KEY` |
| `minimax` | `https://api.minimax.io/v1` | `MINIMAX_API_KEY` |
| 其他 | `--base-url <任意兼容地址> --api-key-env <变量名>` | |

为适配非 OpenAI 的模型，`cra-agent` 还做了这些处理：
- `tool_choice` 固定为 `auto`，这是 DeepSeek 思考模式的要求；
- 不主动发送 `temperature`，因为部分思考模式会固定这个值；
- 在工具调用轮次里把 `reasoning_content` 原样回传（DeepSeek、Kimi 的思考模式需要）；
- 不内置模型 id，请填你账号里实际列出的 id。

**测试覆盖**（不需要联网，也不需要账号）：
- 所有档位、所有工具都符合 strict schema 规则；
- Responses、Gemini、Anthropic 三种导出格式；
- `search`/`fetch` 的返回格式；
- 带公网 Host 和 ChatGPT Origin 的 HTTP 会话可以通过，陌生的 Host/Origin 被拒绝，缺少秘密路径会被拒绝；
- `ToolBox` 对错误调用的拒绝；
- `cra-agent` 的完整循环（用脚本模拟模型回复，覆盖 tool_call_id、破坏性工具的确认和 `reasoning_content` 回传）；
- 对本地伪造的 OpenAI 兼容服务器检查请求格式。

**未覆盖**：真实调用 ChatGPT 或任何厂商的 API。

---

## Cline + DeepSeek

> 说明：cra-mcp 这一侧已经测试过，包括 stdio 服务器、工具 schema 和生成的 Cline 配置片段。
> DeepSeek 的模型列表和 Cline 的界面文字来自 2026 年 11 月的官方资料，没有在这里做端到端实测。
> 如果你看到的名称不一样，按功能找对应的选项即可。

### 1. 配置模型
1. 在 VS Code（或 Cursor、Windsurf 等分支）中安装 **Cline** 扩展。
2. 打开 Cline 设置 → **API Provider 选 DeepSeek** → 粘贴在 platform.deepseek.com 申请的 API key。
3. **选择模型**：从下拉框里选。截至 2026 年 11 月，DeepSeek 主推 V4 代模型（一个快速版、一个 pro 版），都支持工具调用和 1M 上下文；旧的 `deepseek-chat` / `deepseek-reasoner` 别名已计划下线。日常的工具操作（claim、阶段门）用快速版，理论推导和证伪用 pro 版。
4. DeepSeek 的思考模式只接受 `tool_choice: auto`，Cline 发送的正是这个值。如果报 `tool_choice` 相关的 400 错误，换成非思考模式的模型。

### 2. 接入 cra
```bash
cra-mcp install --host cline --project ~/papers/my-paper
```
- 把打印出来的 JSON 粘贴到：Cline → **MCP Servers** → **Configure** → "Configure MCP Servers"（即 `cline_mcp_settings.json`）。
- 这段配置做了三件事：
  - 给 8 个只读工具设置 `autoApprove`，这样每次调用 `cra_resume` 不用手动确认；
  - `timeout: 120`（Cline 的单位是**秒**）；
  - 使用 `core` 档（15 个工具）。
- 同时会在项目里写入 `.clinerules/cra.md`，让每个任务都从 `cra_resume` 开始。
- 配好后，MCP Servers 面板里的 `cra` 应该显示绿点和 15 个工具。

### 3. 日常使用
用 **Plan** 模式商量方案，用 **Act** 模式执行。推荐的第一句话：
> 调用 cra_resume，取 next_tasks 里的第一项任务，用 role_card 加载对应角色，只完成这一项任务，然后再调用一次 cra_resume。

DeepSeek（以及其他非 Claude 模型）的使用建议：
- 保持 `core` 档。工具列表越长，越容易选错工具。
- 每轮只做一项任务。`next_tasks[i].do_not` 列出了这项任务不该碰的内容。
- 工具返回 `ok: false` 时，原因写在 `violations` 里。让模型去修原因，不要重复同一个调用。常见原因有：verdict 缺引用编号、证据行没有日志、阶段门没过。
- 做实验时，让模型把脚本写在 `falsify/<claim>/` 或 `results/<exp>/` 下，在 Cline 的终端里运行，再用 `evidence_add` 登记日志路径。没有真实日志的证据行会被服务器拒绝。
- 运行一次 `cra hook install`。这样不管模型怎么操作，破坏不变量的提交都会被拦下。

### 另一种方式：Claude Code + DeepSeek
DeepSeek 提供 Anthropic 兼容接口，Claude Code 可以直接换用 DeepSeek 模型，同时保留原生的 agents、skills 和 `/cra-*` 命令。在 `~/.claude/settings.json` 中写入：
```json
{"env": {"ANTHROPIC_BASE_URL": "https://api.deepseek.com/anthropic",
         "ANTHROPIC_AUTH_TOKEN": "<你的 DeepSeek key>",
         "ANTHROPIC_MODEL": "<DeepSeek 模型 id>"}}
```
确保 shell 环境里没有设置 `ANTHROPIC_API_KEY`，否则它的优先级更高。然后运行 `cra-mcp install --host claude-code --project …`。

智谱 GLM、Kimi、通义千问、MiniMax 的 Anthropic 兼容地址和 OpenAI 兼容地址，见[兼容性参考](../integrations/COMPATIBILITY.md#models-vs-hosts-deepseek-glm-kimi-qwen-minimax)。
