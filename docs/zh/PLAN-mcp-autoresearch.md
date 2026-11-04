# 方案：Auto-Research 工作流优化 + MCP 化 + 多平台兼容

> 状态：**已确认，正在实施**（2026-11-04）。进度见下表，平台事实以
> [docs/integrations/COMPATIBILITY.md](../integrations/COMPATIBILITY.md) 为准（含来源，未证实处已标注）。

| 里程碑 | 状态 | 交付 |
|---|---|---|
| M0 修复与卫生 | ✅ 完成 | 引用核验改为 sha256 新鲜度（mtime 降为兜底）；`scripts/check_all.sh`；GitHub Actions CI（py3.10/3.13）；测试 extra |
| M1 `cra_core` | ✅ 完成 | 无损 Markdown 表格、claim/evidence 不变量、ID+文件锁、事件流、`\claimref`/`\evid`、`cra` CLI、git pre-commit 钩子；顺带修复 3 个模板 bug（新项目 P0 门必挂、模板示例行是真数据、`\ev` 与 `\evid` 不一致） |
| M2 `cra-mcp` | ✅ 完成 | 24 个工具三档（core 15 / full 24 / remote 21）、prompts、resources、stdio + Streamable HTTP（bearer 或秘密路径）、`cra-mcp install --host`（21 个平台）、`doctor`、`--export openai/anthropic/gemini`、中英文接入文档、Cline + DeepSeek 指南 |
| M3 研究循环 | ⏳ 下一步 | `trial_start/finish`（worktree + 预算 + keep/discard 棘轮）、预算字段、`task_next(parallel)` |
| M4 兼容层收尾 | ✅ 接口适配完成 | 安装器；导出 `openai`/`openai-responses`/`openai-compat`/`anthropic`/`gemini`（strict 可空枚举等细节）；`ToolBox` 函数调用适配器；`cra-agent`（任意 OpenAI 兼容 Chat Completions：ChatGPT API、DeepSeek、GLM、Kimi、通义、MiniMax…）；ChatGPT 远程 MCP 接口（秘密路径、Host/Origin、search/fetch）。按你的要求不做网关/隧道部署；真实账号联调待你验证 |
| M4+ CRA Studio | ✅ MVP 完成 | 桌面工作台（项目/概览/研究助手/账本/设置/接入），模型接口开放配置（任意 OpenAI 兼容地址+key+模型）；单个可执行文件 = GUI + MCP 服务器 + CLI + cra-agent；PyInstaller 打包，`release` 工作流构建 Windows/macOS/Linux（Linux 已本地实测，Win/mac 由 CI 构建） |
| M5 异构红队 | ⏳ | 默认关闭 |
| M6 发布 | ⏳ | PyPI 自包含 wheel（内置 templates/agents/skills，支持 `uvx cra-mcp`）、Claude Desktop `.mcpb` |
> 范围：本仓库（toolkit）。不涉及任何私有研究内容（遵守 SPEC §0）。

---

## 0. 一句话结论

现在的系统是一套写得很好的**流程规范**（12 个角色提示词、约 30 个 skill、P0–P8 阶段门），但它的不变量
（"未经证伪的 claim 不进论文"、"每个数字都有日志"、"每条引用都核实过"）**大部分靠提示词约束**，
多智能体编排又**绑定在 Claude Code 的 Workflow 工具上**。

建议分三步：

1. **把不变量从提示词下沉到代码里**：新增 `cra-core` 状态层，成为黑板文件唯一的结构化读写入口。
2. **借鉴 auto-research 的闭环**（假设 → 跑实验 → 留下或丢弃 → 记账 → 继续），加一个有预算、能断点续跑的研究循环。
3. **把以上能力做成一个 MCP server（`cra-mcp`）**，再配一个同源 CLI，这样 Claude Code、Codex、Gemini CLI、
   Cursor、Cline、OpenCode 等宿主都能直接用；DeepSeek、GLM、Qwen、Kimi 等模型通过这些宿主或 OpenAI 兼容接口接入。

---

## 1. Review：现状与问题

### 1.1 做得好的地方（保留）
- **先证伪再写**：`CLAIMS.md` 的 open/survived/weakened/refuted 状态，加上 falsifier 的否决权，设计正确，
  案例项目里 C3、C5 被推翻就是很好的示范。
- **证据账本**：`EVIDENCE.md` 配合 `crbench audit-tex`，每个数字都要有日志。
- **引用核实**：`verify_bib.py` 依次查 ePrint → Crossref/DataCite → DBLP，这一块已经很扎实。
- **黑板交接**：agent 之间通过文件交接，可审计，也天然适配 MCP 的 resource 模型。
- `gate_check.py` 已经把阶段门的机械部分代码化了。

### 1.2 问题（按优先级）

| # | 问题 | 证据 / 位置 | 影响 |
|---|---|---|---|
| R1 | **不变量主要靠提示词执行**。只有"数字有 EVIDENCE 行"这一条有脚本强制，而且是按逐字文本匹配；"论文里的陈述对应 survived 的 claim"完全没有机械检查 | `gate_check.py` 只做数字检查；`writer.md` 靠自觉 | 换成较弱的模型（DeepSeek/GLM 等）或上下文被压缩后，最容易在这里出错 |
| R2 | **黑板是 Markdown 表格，用正则解析**。表格里出现 `\|`、换行或列顺序变动就会静默解析错；ID 分配也靠模型自己数 | `gate_check.md_table`、`crbench/evidence.py` 各写了一套解析 | 状态损坏不报错；多 agent 并发写同一文件时会冲突 |
| R3 | **用 mtime 判断"新鲜度"不可靠**。`git clone` 或 checkout 之后 mtime 会被重置 | `gate_check.py:154`；在本仓库实测 `case-study/toy-mvpbs` 的 P8 门因此 **FAIL**（bib-verify report 被判为比 refs.bib 旧） | 误报、漏报都有可能，削弱对门检的信任 |
| R4 | **编排不可移植**。`workflows/*.js` 依赖 Claude Code 的 Workflow 工具；Codex 等平台只能通过 `AGENTS.md` 让模型"扮演"角色，完全没有并行和投票 | `workflows/`、`AGENTS.md` | 声称兼容 Codex，但只有"读提示词"这一层兼容 |
| R5 | **没有研究循环**：没有实验预算、迭代账本、留下/丢弃的判定，也没有断点续跑。P2/P5 的探索主要靠模型自觉 | `idea-mining-loop` 只是流程描述 | 长时间自主运行时容易跑偏、重复试验、编数字 |
| R6 | **falsifier 同源**：三个视角是同一个模型、同一套上下文 | `falsify-round.js` | 盲点相关：自己证伪自己，效果打折扣 |
| R7 | **工程卫生**：没有 CI（没有 `.github/`）；环境里没装 pytest 时测试直接跑不起来；`install.sh` 只认 `.claude/` | — | 贡献者和用户上手门槛高 |
| R8 | **安装形态单一**：只有 Claude Code plugin 和 `install.sh` 两种方式；没有 MCP 配置、没有 `pip install` 一条命令装好的入口 | `.claude-plugin/plugin.json` | 不利于推广 |

---

## 2. 借鉴 auto-research 工作流：要吸收什么

"Auto-research"在这里指两类已经被验证有效的模式。下面只取对密码学论文工作流有用的部分：

| 模式 | 来源思路 | 在本系统中的落点 |
|---|---|---|
| **A. 规划 → 并行检索 → 带引用综合 → 引用核验** | Claude 的 deep-research 流程：主 agent 拆子问题，子 agent 并行搜索，最后由专门的引用 agent 回查 | P1 `lit-sweep`：把"每条结论都要有出处"变成结构化输出 `{claim, source_id, quote}`，由 `bib_verify` 和 `lit_matrix` 工具强制核对 |
| **B. 固定预算的实验棘轮** | auto-research 闭环：一次只改一处 → 跑固定时长 → 指标变好就 commit，变差就 revert → 结果追加进 TSV → 继续 | P2/P5 新增 `research-loop`：每次试验有 `trial_id`，记录假设、diff、命令、指标、keep/discard；每次试验在独立 git worktree 里跑；被丢弃的结果同样入账（负结果也是数据） |
| **C. 外部化的长期记忆 + 断点续跑** | 自主 agent 靠文件而非上下文记忆；上下文压缩后从文件恢复 | `.cra/events.jsonl`（append-only 事件流）+ `STATE.md`；新增工具 `cra_resume`：读取后告诉宿主"你在哪、下一步做什么、哪些不能做" |
| **D. 确定性的护栏** | Claude Code hooks（PreToolUse / Stop）、git hooks | 写入 `paper/` 前自动跑 audit；会话结束前自动跑 gate；**git pre-commit hook 跨所有平台都生效**（这是对非 Claude 宿主最可靠的强制手段） |
| **E. 异构评审** | 多模型交叉验证 | falsifier 和 reviewer-sim 可以配置成"不同模型"，见 §4.4 |
| **F. 先验证再信任** | 子 agent 返回的结果要回查 | 所有"数字"类结果只接受 `evidence_add` 写入的行（必须带命令、日志路径和日志哈希），不接受模型在正文里转述的数字 |

### 2.1 优化后的研究循环（覆盖 P2–P6）

```
          ┌──────────────── cra_resume (读 STATE + events, 给出下一步) ────────────────┐
          ▼                                                                             │
  propose hypothesis ──► claim_register (open, kill 条件, 最小实验)                      │
          │                                                                             │
          ▼                                                                             │
  falsify-first: claim_attack (≥2 视角, 可选异构模型) ── refuted ──► 记账, 回到 propose  │
          │ survived / weakened                                                         │
          ▼                                                                             │
  trial_start (worktree, 预算: 时间/次数/token) ──► 跑实验 ──► trial_finish(metric)      │
          │                                  keep: commit + evidence_add               │
          │                                  discard: revert + 记负结果               │
          ▼                                                                             │
  gate_check ── FAIL ──► 返回缺项列表 ──────────────────────────────────────────────────┘
          │ PASS
          ▼
  phase_advance (仅 orchestrator; 写 DECISIONS)
```

几条关键约定：
- **预算是一等公民**：`STATE.md` 增加 `budget:`（墙钟时间、试验次数、可选 token）；超出预算后循环强制停下，交给人决定。
- **"禁止清单"自动生成**：并行派发时，`task_next` 返回给每个 worker 的"不要做"列表来自其他进行中的任务，
  不再依赖 orchestrator 手写（对应 pi-orchestrator 中 fan-out 规则 (f)）。
- **人类审批点不变**：任何会离开本机的动作（投稿、邮件、eprint、公开仓库）在 MCP 层都**没有对应的工具**，
  只能生成清单，交给人执行。

---

## 3. 先打地基：`cra-core`（解决 R1–R3）

新增 Python 包 `lib/core`（包名 `cra_core`），是 gate_check、crbench evidence 和 MCP server 共用的唯一实现：

- **Schema**：`Claim`、`Evidence`、`Decision`、`Task`、`Trial`、`State` 用 dataclass 定义，带校验（状态枚举、ID 格式、必填列）。
- **Markdown 往返**：Markdown 仍然是人类可读的**规范存储**（不迁移格式，现有项目零成本兼容）；
  `cra_core` 负责解析和**无损回写**，包括单元格转义、保留表格前后的说明文字。解析失败直接报错，不再静默。
- **ID 分配、文件锁**：`C<n>`/`E<n>`/`D-<n>` 由代码分配；写入时对文件加锁，避免并行 agent 冲突。
- **事件流** `.cra/events.jsonl`：每次结构化写入追加一条事件（谁、何时、改了什么、对应哪个 commit），用于审计和断点续跑。
- **新鲜度改用内容哈希**（修复 R3）：`bib-verify-report.md` 写入 `refs.bib` 的 sha256，门检比对哈希而不是 mtime。
  `EVIDENCE` 行也记录日志文件的 sha256，日志被改动时 `evidence check` 会报出来。
- **用 ID 对齐论文和 claim**（加强 R1）：新增 LaTeX 宏 `\claimref{C4}`（编译后不显示）和 `\ev{E3}{3.86\times}`（显示数字，同时声明来源）。
  `audit-tex` 升级为三条检查：① 每个 `\ev` 的 ID 存在，且数字与账本一致；② 每个 `\claimref` 对应的 claim 状态是 survived/weakened；
  ③ 没被宏包住的裸数字按现有逐字规则检查（向后兼容）。

---

## 4. MCP 化：`cra-mcp`

### 4.1 总体架构

```
┌──────────── 宿主 (Claude Code / Codex / Gemini CLI / Cursor / Cline / OpenCode / ...) ────────────┐
│  宿主自己的 LLM（Claude / GPT / DeepSeek / GLM / Qwen / Kimi …）负责思考和写作                       │
└───────────────┬───────────────────────────────────────────────────────────────────────────────────┘
                │ MCP (stdio 默认；可选 Streamable HTTP)
┌───────────────▼──────────────── cra-mcp (Python, 官方 MCP SDK) ───────────────────────────────────┐
│ Tools     确定性操作：黑板读写、门检、审计、bib 核验、检索、基准、参数估计、图表、匿名检查            │
│ Resources 黑板文件、agent 角色卡、skill、阶段手册（cra://...）                                       │
│ Prompts   12 个 /cra-* 命令 + 12 个角色（宿主支持 prompts 时可直接作为斜杠命令）                     │
├───────────────────────────────────────────────────────────────────────────────────────────────────┤
│ cra_core（状态 + 不变量）   cryptomath   crbench   skills/*/scripts                                  │
└───────────────────────────────────────────────────────────────────────────────────────────────────┘
```

核心设计原则：**服务器是状态机和工具箱，宿主的模型是工人**。默认情况下服务器自己不调用任何 LLM：
不需要额外的 API key，不产生隐性费用，任何宿主都能用。

### 4.2 工具清单（约 25 个，按命名空间分组）

工具数量刻意控制在较少的范围，参数尽量用枚举，因为非 Claude 模型在工具很多、描述很长时更容易选错。

| 组 | 工具 | 说明 | 注解 |
|---|---|---|---|
| 项目 | `project_init`, `project_status`, `cra_resume` | 初始化黑板；返回阶段、未完成门项、open claims、下一步建议 | status/resume 只读 |
| 阶段 | `gate_check`, `phase_advance` | advance 前自动跑门检，失败就拒绝；必须带 DECISIONS 理由 | advance 有破坏性，需确认 |
| 任务 | `task_next`, `task_claim`, `task_complete` | 返回下一项任务，附带**角色卡 + 输入文件 + 输出格式 + 禁止清单 + kill switch** | — |
| Claim | `claim_register`, `claim_list`, `claim_set_verdict`, `claim_attack_brief` | 设置 verdict 时必须带证据路径；brief 生成给 falsifier 的攻击任务书 | — |
| 证据 | `evidence_add`, `evidence_check`, `audit_tex` | add 时校验日志存在并记录哈希 | — |
| 循环 | `trial_start`, `trial_finish`, `trial_list` | auto-research 棘轮：worktree + 预算 + keep/discard | — |
| 文献 | `eprint_search`, `bib_verify`, `lit_matrix_update`, `textbook_lookup` | 包装现有脚本；`textbook_lookup` 基于 TOC 和 TOPIC-MAP | 需联网（openWorld） |
| 计算 | `crbench_run`, `param_estimate`, `cryptomath_eval` | `cryptomath_eval` 只开放白名单函数（例如 DDT、噪声估计、core-SVP），不执行任意代码 | — |
| 写作 | `paper_section_guide`, `figure_render`, `anon_check`, `pdf_checks` | guide 返回 playbook 对应章节；render 用 house style 模板 | — |
| 评审 | `review_brief`, `rebuttal_triage` | 生成评审人设任务书和 triage 表 | — |

每个工具的返回值统一为 `{ok, data, violations[], next_actions[]}`。其中 `next_actions` 直接告诉弱一些的模型下一步调用什么，降低走偏的概率。

**安全**：所有路径限制在 `--project` 根目录之内；联网工具单独打标签，可以用 `--offline` 整体关掉；
不提供任何"发送 / 提交 / 发布"类工具；遵守 MCP 的 `readOnlyHint` / `destructiveHint` 注解，方便宿主做审批。

### 4.3 编排的可移植性（解决 R4）

`workflows/*.js` 保留给 Claude Code 用户（体验最好）。同时提供与宿主无关的等价物：

- **串行降级**：`task_next` 依次给出 lit-sweep / falsify-round 等流程的每一步，任何只会"调用工具 + 写文件"的宿主都能把流程跑完，只是不并行。
- **宿主有子 agent 时**（Claude Code、Codex 等）：`task_next(parallel=true)` 一次返回 N 个互不重叠的任务书，由宿主自己的子 agent 并行执行，最后统一用 `claim_set_verdict` 投票落账。投票规则从 JS 挪到 `cra_core`，各平台的判定结果一致。

### 4.4 可选：异构模型红队（解决 R6）

在 `.cra/providers.toml` 里配置任何 **OpenAI 兼容接口**（DeepSeek、智谱 GLM、Qwen、Kimi、本地 vLLM/Ollama 都支持这种接口）：

```toml
[falsifier.lens2]
base_url = "https://<provider>/v1"
model    = "<model-id>"
api_key_env = "DEEPSEEK_API_KEY"   # 只读环境变量，key 不落盘
```

`claim_attack(id, lens, provider=...)` 这时由服务器直接调用该模型，结果作为一票。这是**可选开关**，
默认关闭；开启后会在调用前提示：claim 的文本会发给第三方 API。这和"不经人类批准，任何东西不出本机"的原则相关，
所以首次使用需要用户显式确认，并写入 DECISIONS。如果宿主支持 MCP sampling，也可以改用宿主自己的模型，不需要额外配置 key。

### 4.5 平台兼容矩阵

> 已按调研结果实现，最新、带来源的版本见 [COMPATIBILITY.md](../integrations/COMPATIBILITY.md)。
> 调研后的主要修正：**ChatGPT** 只支持远程 HTTPS（开发者模式 App，认证方式只有"无认证"或 OAuth，
> 不能带自定义 header），因此新增 `remote` 档（文件读写 + `search`/`fetch`）和 `--secret-path`；
> Cline 的 `timeout` 单位是秒，URL 型配置不写 `type` 会默认走 SSE；Gemini CLI 会剥掉部分 schema 关键字，
> 服务器名不能含 `_`；VS Code 用 `servers` 而不是 `mcpServers`；OpenCode 用 `mcp` 且 `command` 是数组。

| 平台 / 用法 | 接入方式 | 能拿到什么 |
|---|---|---|
| **Claude Code** | 插件内置 `.mcp.json`，或 `claude mcp add cra -- cra-mcp --project .`；继续保留 agents/skills/commands/hooks | 全部（Workflow 并行、hooks 强制、MCP prompts 作为斜杠命令） |
| **Codex CLI** | `~/.codex/config.toml` 里加 `[mcp_servers.cra]`；`AGENTS.md` 改写为"先调用 `cra_resume`" | 工具 + 资源；用 AGENTS.md 指引角色 |
| **Gemini CLI / Qwen Code** | `settings.json` 里的 `mcpServers` | 工具 + prompts |
| **Cursor / Windsurf / Cline / Roo / Continue / Trae** | 各自的 `mcp.json` | 工具（prompt 和 resource 的支持程度因平台而异） |
| **OpenCode / Kimi CLI / Cherry Studio 等** | MCP 配置 | 工具 |
| **DeepSeek / GLM / Qwen / Kimi 等模型** | 这些是**模型**，不是宿主：① 在上面任一宿主里选这个模型；② 部分厂商提供 Anthropic 兼容接口，可以通过 `ANTHROPIC_BASE_URL` 让 Claude Code 换用这些模型；③ 用下面的 CLI 或参考 agent | 同所选宿主 |
| **不支持 MCP 的框架 / 自研脚本** | `cra` CLI（与 MCP 同源）；`cra tools export --format openai\|anthropic\|gemini` 导出函数调用 schema；附一个约 200 行的参考 agent `cra-agent --base-url ... --model ...`，适配任意 OpenAI 兼容端点 | 工具（用 function calling） |

> 各平台的配置文件路径和字段会变，实施时以各平台当前文档为准，并在 `docs/integrations/` 下分平台写安装说明，
> 附可复制的配置片段。

**一条命令安装**：
```bash
pipx install crypto-research-agents        # 安装 cra、cra-mcp，依赖 cra_core / cryptomath / crbench
cra install --host claude-code|codex|gemini|cursor|cline|opencode [--project .]
```
`cra install` 会为对应宿主写好 MCP 配置、入口指令文件（CLAUDE.md / AGENTS.md / GEMINI.md）和 git pre-commit hook。
现有的 `install.sh` 改为调用它，保持向后兼容。

### 4.6 跨平台的强制层（与 MCP 互补）

MCP 工具只能约束"通过工具"的写入，宿主仍然可以直接改文件。所以不变量要在三个层面同时守住：
1. **git pre-commit hook**（所有平台）：`cra check --staged` 检查对 `paper/`、`CLAIMS.md`、`EVIDENCE.md` 的改动，审计失败就拒绝提交。
2. **Claude Code hooks**（只在 Claude Code 生效）：PostToolUse 写入 `paper/**` 后跑 `audit_tex`；Stop 时跑 `gate_check`，结果作为反馈返回给模型。
3. **门检本身**：`phase_advance` 无法绕过。

---

## 5. 路线图

| 里程碑 | 内容 | 验收标准 |
|---|---|---|
| **M0 修复与卫生**（小） | R3 改为哈希比对；加 GitHub Actions 跑全部测试和 selftest；pytest 列为 dev 依赖；修正案例项目的 P8 门 | CI 绿；`gate_check --phase P8` 在新 clone 下 PASS |
| **M1 `cra_core`** | schema、Markdown 无损往返、ID/锁、事件流；gate_check 和 crbench evidence 改用它 | 对案例项目所有黑板文件做"解析 → 回写"后 diff 为空；新增 `\ev`/`\claimref` 审计 |
| **M2 `cra-mcp` v0** | 只读工具 + 黑板写工具 + 门检/审计 + resources/prompts；stdio | 用 MCP Inspector 和进程内客户端的测试覆盖所有工具 |
| **M3 研究循环** | `trial_*`、预算、worktree、`cra_resume`、`task_next`（串行和并行两种模式） | 在案例项目里用纯 MCP 工具重放 C3 → C6 的"推翻 → 替代"过程 |
| **M4 兼容层** | `cra` CLI、`cra install --host ...`、schema 导出、参考 agent、`docs/integrations/*`（中英文） | 至少在 Claude Code、Codex CLI 和一个 OpenAI 兼容模型（DeepSeek 或 GLM）上跑通 P0 → P2 冒烟流程 |
| **M5 异构红队（可选）** | providers.toml、MCP sampling 路径、首次使用的确认流程 | falsify-round 混用两种模型投票；默认关闭 |
| **M6 文档与发布** | README、BIGMAP、QUICKSTART 更新；PyPI 包；插件版本升到 0.2.0 | 新用户 10 分钟内跑通 quickstart |

建议顺序是 M0 → M1 → M2 → M3 → M4，之后按需求做 M5。M0 和 M1 本身就有价值，不依赖 MCP。

---

## 6. 需要你拍板的问题

1. **服务器语言**：建议用 Python（现有库全是 Python，用官方 MCP SDK）。是否需要额外提供 npm 包装（`npx cra-mcp`）？
2. **服务器是否允许直接调用 LLM**（§4.4）：默认关闭，作为可选项提供，这样可以吗？
3. **首批要验证的平台**：建议 Claude Code + Codex CLI + 一个国产模型（DeepSeek 还是 GLM？用什么宿主，比如 Cline 或 OpenCode？）。
4. **LaTeX 宏 `\ev` / `\claimref`**：会改变写作习惯，作为可选的推荐用法，同时保留逐字匹配作为兜底，可以吗？
5. **`workflows/*.js`**：继续维护 Claude Code 专用版本，还是以后只保留 MCP 版本？
