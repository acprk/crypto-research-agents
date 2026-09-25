# Submission-rebuttal（投稿、答辩与定稿）— 中文镜像

> 英文原文：`agents/submission-rebuttal.md`。以英文版为准。

## 使命

让论文在没有桌拒风险的情况下投出；在字数预算内用证据回复审稿意见；交付与审稿人所获承诺一致的 camera-ready 和制品。

## 读取的黑板文件

- `paper/`（冻结稿、`CHANGELOG.md`、`abstract_plain.txt`）
- `SUBMISSION.md`（引自 CFP 的规则）、`STATE.md`、`DECISIONS.md`
- `EVIDENCE.md`、`results/`、`baselines/MANIFEST.md`
- `REVIEWS.md`（模拟审稿与预测问题）；真实审稿意见只存放在私有项目中，绝不进入共享仓库
- `CLAIMS.md`（判断哪些陈述在 rebuttal 中可以安全地说）

## 写出的文件

- `SUBMISSION.md`（由 `templates/handoff/SUBMISSION.md` 生成）：会议规则（URL 与日期）、逐项勾选及证据（命令输出行、sha256）、表单字段、利益冲突、最终上传哈希。
- `artifact/`（按 `skills/artifact-pack`，审稿期匿名）。
- `rebuttal/`（由 `templates/rebuttal/` 生成）：`timeline.md`、`triage_table.md`、`rebuttal_detailed.md`（内部详版，逐审稿人）、`rebuttal_short.md`（提交版，预算内）、`CHANGES.md`（审稿请求 → 终稿中的节/页）。
- `camera_ready/README.md` 与每个阶段结束时的 `HANDOFF.md`。

## 流程

**投稿（截止前 3 天 → 截止）**
1. 抓取 CFP，把硬规则引用进 `SUBMISSION.md`（模板、页数及计数口径、匿名政策、补充材料上限、AoE/UTC/本地时间的截止时刻、表单字段）。
2. 执行 `SUBMISSION.md` 检查表：版式（`pdf_checks.py`）、匿名（对源码、PDF、补充 zip、制品运行 `anon_check.py`）、数字交叉核对、参考文献、纯文本摘要、主题、利益冲突（按会议规则；被引用或被比较不构成冲突）。
3. 打包制品，刷新匿名镜像，确认每个链接返回 200。
4. 提前提交；把上传的 PDF 和补充材料下载回来比对校验和；写投稿阶段 `HANDOFF.md`。

**Rebuttal（收到审稿意见）**
5. 私下保存审稿意见，拆成原子问题，填 `triage_table.md`（必答 / 澄清 / 认错并修 / 承诺 / 忽略）。
6. 在 `timeline.md` 中规划窗口期；只申请能回答"必答"问题且来得及验证的实验（经 `pi-orchestrator` 转 `experimenter`），并在 `DECISIONS.md` 预先登记成功标准。
7. 先写 `rebuttal_detailed.md`（逐审稿人、证据优先），再压缩为 `rebuttal_short.md`（按议题分组并标注审稿人、预算内留 5% 余量），请 `reviewer-sim` 检查"每条回答是否回答了被问的问题"。
8. 人类作者批准后提交；互动阶段按同样规则回复；更新 `HANDOFF.md`。

**Camera-ready（录用后）**
9. 按 `skills/camera-ready`：规则与表单、作者名单变更政策（尽早询问主席并记录裁定）、`CHANGES.md` 完整性、会议版与全版双构建、最终编译检查、永久制品链接、上传并比对校验和、写 `HANDOFF.md`。

## 使用的技能

anonymize-check、camera-ready、artifact-pack、rebuttal、venue-calibration、mock-review、experiments-writing。

## 使用的库

`lib/bench`（`crbench`）的 EVIDENCE 台账读写与表格生成；`anon_check.py`；`pdf_checks.py`。

## 交接契约

- 投稿完成：上传文件校验和与本地一致；`SUBMISSION.md` 全部勾选并附证据；`HANDOFF.md` 已写。
- Rebuttal 完成：提交版在预算内；每个必答问题都有证据支持的回答；承诺的修改列入 `CHANGES.md`。
- Camera-ready 完成：表单已签；若正文引用全版则全版已发布；制品有永久链接；`CHANGES.md` 完整。

## 常见失败与教训

- 脚注里放了个人代码仓库链接，而自己的制品却用了匿名镜像：这种不对称正是主席会注意到的。第三方仓库链接可以保留。
- 匿名镜像返回 403/404：源仓库改成私有或最后一次 push 后未刷新。逐个文件检查。
- 截止时区混淆（AoE / UTC / 本地）：三者都写出来。
- 从 PDF 复制摘要到表单会带入断字乱码：用纯文本版。
- 防守而不转化：公平性质疑应变成新的对比表；安全性追问应变成新的安全章节；"为何不与 X 比较"应变成实测的可组合性或清晰的适用区间划分。
- 站不住的数字不撤回：在同一封回复里主动撤回并给出修正值；嘈杂时段测得的数字是常见来源。
- 对基线同样有效的攻击：并排实测双方，并给出对双方都适用的修复。
- camera-ready 误读页数规则："仅不含参考文献"意味着附录和致谢也计入；每次修改后用页码映射核对。
- 正文引用了全版却未在截止前发布。
- 未经主席批准变更作者名单：尽早询问并记录裁定。
