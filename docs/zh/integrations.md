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

## 3. ChatGPT 和 claude.ai（云端宿主）

这两个平台从云端连接 MCP 服务器，所以需要一个公网 HTTPS 地址。请使用 `remote` 档：它在 core 的基础上增加了沙箱内的 `file_list`/`file_read`/`file_write` 和 `search`/`fetch`，因为云端宿主看不到你本地的磁盘。

```bash
cloudflared tunnel --url http://127.0.0.1:8765          # 终端 1（或 ngrok http 8765），记下打印出的 https 地址
```

```bash
cra-mcp --project ~/papers/my-paper --http --profile remote --secret-path --public-url <隧道地址>   # 终端 2
```

- **ChatGPT**：设置 → Apps（连接器）→ 高级 → 打开**开发者模式** → **创建 App**：
  - MCP 服务器地址填 `>>>` 那一行给出的 URL；认证方式选 **无认证**。URL 里的随机路径就是密钥，保存在 `.cra/mcp-secret`，重启服务器后不变。
  - 然后新开一个对话：**+** → **Developer mode** → 勾选 **cra**。
  - 详细步骤和排错见下文"ChatGPT 逐步接入"一节。
  - 写入类工具每次调用都会请求确认。
  - 更新 cra 之后，要在 App 设置里点一次**刷新**。
  - 哪些套餐可以使用写入类工具，OpenAI 各页面的说法不一致，以你自己账号里看到的为准。
  - OpenAI 还提供只需出站连接的 *Secure MCP Tunnel*，可以代替公网 URL。
- **claude.ai**：设置 → Connectors → **添加自定义连接器**，填同一个 URL。

拿到 URL 的人可以读写这个项目的文件。用完请关掉隧道，不要把 URL 发到任何共享的地方。

## 4. OpenAI API / Agents SDK

先用 bearer token 以 HTTP 方式启动服务器：

```bash
CRA_MCP_TOKEN=$(openssl rand -hex 24) cra-mcp --project . --http     # http://127.0.0.1:8765/mcp
```

然后作为远程 MCP 工具传给 API。这个 URL 必须能从公网访问，可以用第 3 节的隧道：

```json
{"type": "mcp", "server_label": "cra", "server_url": "https://<域名>/mcp",
 "headers": {"Authorization": "Bearer <token>"}, "require_approval": "never"}
```

## 5. 完全不用 MCP：导出函数调用 schema

```bash
cra-mcp --export openai    > cra-tools.openai.json      # OpenAI strict 模式
cra-mcp --export anthropic > cra-tools.anthropic.json
cra-mcp --export gemini    > cra-tools.gemini.json
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

## ChatGPT 逐步接入

> 说明：cra-mcp 这一侧已经测试过，包括 HTTP 传输、秘密路径，以及经隧道转发、带 ChatGPT Origin 的请求能否通过 Host/Origin 校验。
> ChatGPT 的菜单名称来自 2026 年 11 月 OpenAI 的文档和近期的第三方教程。ChatGPT 改版很频繁，如果名称对不上，就找 "Developer mode" 和 "Create app"。

**准备**
- ChatGPT 付费账号（Plus / Pro / Business / Enterprise / Edu），开发者模式在 **ChatGPT 网页版**里。各套餐能否使用写入类工具，OpenAI 各页面说法不一；即使写入被限制，只读工具（`cra_resume`、`claim_list`、`gate_check`、`search`、`fetch` 等）仍然可用。
- 存放研究项目的电脑，并已装好 cra（见第 1 节）。
- 隧道工具。ChatGPT 从 OpenAI 的云端发起连接，访问不到你的 `localhost`。推荐 cloudflared，不需要注册：
  - macOS：`brew install cloudflared`
  - Windows：`winget install --id Cloudflare.cloudflared`
  - Linux：从 Cloudflare 官网下载 deb/rpm 包

**步骤**
1. 准备项目：`cra init ~/papers/my-paper`（已有项目可跳过），再运行 `cra-mcp doctor --project ~/papers/my-paper` 自检。
2. 终端 1（保持运行）：`cloudflared tunnel --url http://127.0.0.1:8765`，复制它打印的 `https://<随机>.trycloudflare.com`。快速隧道每次启动地址都会变；想要固定地址，可以用 Cloudflare 命名隧道，或 ngrok 的固定域名。
3. 终端 2（保持运行）：
   ```bash
   cra-mcp --project ~/papers/my-paper --http --profile remote --secret-path --public-url https://<随机>.trycloudflare.com
   ```
   它会打印一行 `>>> paste this as the MCP server URL: https://…/mcp/<密钥>`。
4. ChatGPT：**设置 → Apps → Advanced settings → 打开 Developer mode** → **Create app**：
   - 名称填 `cra`；
   - MCP Server URL 填 `>>>` 那一行给出的 URL；
   - Authentication 选 **No authentication**；
   - 勾选信任，然后创建。

   创建后应能看到 21 个工具。
5. **新开一个对话** → 点 **+** → **Developer mode** → 勾选 **cra**。第一句话可以这样说：
   > 使用 cra app。调用 cra_resume，然后完成 next_tasks 里的第一项任务（先用 role_card 加载对应角色），最后告诉我改了什么。
6. 写入类工具（`claim_register`、`evidence_add`、`file_write` 等）每次都会弹出确认，批准前请看一眼参数。
7. 以后更新了 cra，要到 **设置 → Apps → cra** 里点一次 **Refresh**，因为 ChatGPT 会缓存工具列表。

**和本地 IDE 的区别**
- ChatGPT 没有终端，**不能跑实验**。实验在你的电脑上跑，跑完后让 ChatGPT 用 `evidence_add` 登记日志（只接受项目里真实存在的日志），再在论文里引用这个数字。
- ChatGPT 只能通过 `file_read` / `file_write` 读写项目文件；CLAIMS、EVIDENCE、DECISIONS 这几个账本不能用 `file_write` 改，必须走专门的工具。
- 有了 `search` / `fetch`，ChatGPT 的深度研究模式也能检索和引用项目里的笔记和草稿。

**排错**

| 现象 | 处理 |
|---|---|
| ChatGPT 提示连接失败或列不出工具 | 确认两个终端都还在运行。用浏览器打开 `>>>` 的 URL：看到 `"Not Acceptable: Client must accept text/event-stream"` 这行 JSON 说明链路是通的（浏览器本来就不是 MCP 客户端）；看到 Cloudflare 的错误页说明隧道断了 |
| 服务器日志出现 `Invalid Host header`（421） | 隧道地址变了。用新地址重新执行第 3 步的 `--public-url`，并在 App 设置里更新 URL |
| 404 | 路径不对。要粘贴完整的 `>>>` URL，包括 `/mcp/<密钥>` |
| 更新 cra 后工具还是旧的 | 设置 → Apps → cra → Refresh |
| 写入调用被拦截 | 你的套餐或工作区不允许在开发者模式下执行写入（管理员可以限制这项）；只读工具仍然可用 |

**安全**：拿到 `>>>` URL 的人可以通过这些工具读写项目里的文件（不会超出项目目录）。用完请关掉两个终端，不要把 URL 发到任何共享的地方，也不要提交进 git。cra 没有任何投稿、发邮件或公开发布的工具。

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
