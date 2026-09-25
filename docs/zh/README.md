# crypto-research-agents（中文说明）

一套**多 agent 协作的密码学科研系统**：从文献调研、idea 挖掘、理论证明、baseline 复现、
公平实验、证伪审查，到论文写作、画图、模拟审稿、投稿、rebuttal、camera-ready，
全部打包为 Claude Code 的 agents / skills / 斜杠命令（Codex 通过 `AGENTS.md` 同样可用），
并配有 Python 算法库、公平基准测试框架、画图模板和一个完整的玩具示例。

![BIGMAP](../bigmap/bigmap.png)

## 一、设计思想：三条铁律

| 铁律 | 落地方式 |
|---|---|
| **先证伪，再下笔** | idea 必须先写成 `CLAIMS.md` 里可证伪的一行；`falsifier` agent 有一票否决权，按“定义与量词 → 小参数数值复算 → 边界参数 → baseline 公平性 → 文献抢占”的顺序攻击；只有 `survived`（或按削弱后措辞的 `weakened`）才能写进论文 |
| **每个数字都有日志** | `EVIDENCE.md` 记录“论文中的数字 → 命令 → 日志路径 → commit → 机器 → 重复次数/统计量”；`crbench audit-tex` 自动检查论文里每个数字 |
| **每条引用都真实存在** | `bib-verify` 逐条对 DBLP / Crossref / ePrint 核验；查不到的删除，绝不“凭记忆补全” |

agent 之间**只通过黑板文件交接**（`STATE.md`、`CLAIMS.md`、`EVIDENCE.md`……），因此每一次交接都可追溯、可审计。

## 二、12 个 agent

| agent | 职责 | 对应阶段 |
|---|---|---|
| pi-orchestrator | 阶段门槛、派单、冲突裁决 | 全程 |
| lit-scout | ePrint/DBLP 检索、相关工作矩阵、bib 核验、抢占监控 | P1 |
| math-librarian | 数学教材目录索引：“这个引理在哪本书哪一章” | P1/P3 |
| idea-miner | 8 步挖掘法 + 代价模型筛选 | P2 |
| theorist | 证明、Sage/Mathematica 数值检验、Lean4 形式化、参数与安全性估计 | P3 |
| baseline-engineer | 拉取、固定 commit、构建、公平性清单 | P4 |
| experimenter | 交错 A/B、中位数、环境记录、证据账本 | P5 |
| falsifier | 红队，一票否决 | P6（及随时） |
| writer | 按 playbook 分节写作 | P7 |
| figure-artist | 统一风格作图、从论文中学习好图的模式 | P7 |
| reviewer-sim | 按会议口径模拟三类审稿人 | P8 |
| submission-rebuttal | 匿名化、清单、artifact、rebuttal、camera-ready | P8 |

各 agent 的中文版见 `docs/zh/agents/`。

## 三、阶段与回退（P0–P8）

P0 立题 → P1 文献 → P2 idea → P3 理论 → P4 baseline → P5 实验 → **P6 证伪闸门** → P7 写作+画图 → P8 审稿/投稿/rebuttal/终稿。

- P6 推翻核心论断 → 回 P2（换 idea）或 P3（弱化定理）
- P6 发现 baseline 不公平或没复现 → 回 P4/P5
- P8 模拟审稿要求补实验 → 回 P5；表述问题 → 回 P7
- 任何时候发现被抢占 → 回 P1 做威胁评估，由 PI 在 `DECISIONS.md` 里决定转向 / 重新定位 / 放弃

详见 `workflows/PHASES.md`。

## 四、算法库覆盖面（不只 FHE）

- **代数/数论**：有限域、分圆多项式、Galois 群、CRT 槽、NTT（任意 m）、Z_{p^e}、数字提取多项式、零化多项式、Dirichlet 特征
- **格**：LWE/RLWE/MLWE/NTRU 采样、core-SVP/primal/dual 估计、lattice-estimator 封装、BKZ 模拟器、LLL
- **FHE（玩具实现）**：BGV、BFV、CKKS、TFHE（含 PBS、任意查找表）、各运算噪声公式、Paterson–Stockmeyer/BSGS、Chebyshev 模约简逼近、线性变换代价
- **对称密码**：DDT/LAT/BCT、布尔函数、APN、AES/SPN/Feistel/流密码玩具、SAT/MILP 差分线性路径建模、积分区分器、MPC/FHE 友好密码代价
- **协议**：秘密分享、Beaver 三元组、OT/OT 扩展、OPRF、PSI 与混淆电路代价模型、承诺、Fiat–Shamir、Schnorr
- **椭圆曲线**：曲线运算、BSGS/Pollard rho/Pohlig–Hellman
- **代价模型**：在实现之前先数操作，符号化比较两个算法
- **crbench**：交错运行、稳健统计、环境记录、OpenFHE/HElib/Lattigo/TFHE-rs/SAT/MP-SPDZ 等日志解析、LaTeX 表格、审计论文数字

## 五、上手

```bash
pip install -e lib/cryptomath -e lib/bench
./install.sh ~/papers/我的新论文
cd ~/papers/我的新论文 && claude
# 然后在 Claude Code 中：
/cra-init .
/cra-status
```

完整示例（玩具课题：TFHE 上评估 4-bit S-box，逐位 PBS vs 多值 PBS）见
`case-study/WALKTHROUGH.md`，中文版 `docs/zh/case-study-walkthrough.md`。

## 六、经验教训（抽象后的通用版本）

1. **强基线往往不是目标论文自己比较的那个**——先问“真正的最强 baseline 是谁”。
2. **库的默认参数 ≠ 论文里的参数**——对比前核对真实参数。
3. **引用别人的加速比前先在本机复测**；复测不出来就不能直接比较。
4. **测量一律交错运行取中位数**，不用陈旧 build，不和其他任务抢核。
5. **多 agent 协作时，主 agent 先写可证伪文件，要求 subagent 优先推翻**——提出者最容易对自己的论断盲目。
6. **“不可行”也是结果**：边界条件、失败参数要写进论文的局限性说明，而不是藏起来。
7. **rebuttal 以证据回答**：每个回应都指向日志、定理或新实验，字数预算内先答必须回答的问题。
8. **任何对外动作（投稿、邮件、公开仓库、ePrint）都必须人工确认**。
