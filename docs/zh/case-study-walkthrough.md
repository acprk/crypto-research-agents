# 案例走读：toy-mvpbs（逐阶段）——教学示例

> **这是什么。** 一个完整、可运行的玩具研究项目，用来演示本工具包的 12 个 agent 如何通过黑板文件交接工作。
> 题目公开且属于教科书层面：在玩具 TFHE 密文上计算 4 比特 S 盒（PRESENT），比较
> (a) 每个输出比特一次 PBS；(b) 多值 PBS（Carpov–Izabachène–Mollimard，CT-RSA 2019，ePrint 2018/622）；
> (c) CMux 树 / 垂直打包（CGGI，ASIACRYPT 2017）。
> 参数不安全；计时是纯 Python 的 CPU 时间；DECISIONS.md 里的日期是示意性的。**这里没有任何研究结论。**
>
> **如何产生。** 由一个 Claude Code 会话依次扮演各个角色，每次都按照对应的 `agents/<id>.md` 与 skill 执行。
> 安装插件后，可用下文的斜杠命令驱动同样的流程（或让 `pi-orchestrator` 通过 `/cra-phase P<k>` 调度）。
> 项目中所有数字都由下列脚本于 2026-09-25 实测得到。

项目目录：`case-study/toy-mvpbs/`（黑板文件在其顶层）。英文原版：`case-study/WALKTHROUGH.md`。

## 一键复现（约 4 分钟计算，单核）

```bash
cd case-study/toy-mvpbs
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
/usr/bin/python3 code/sbox_fhe.py                        # 自检：三种策略、16 个输入（约 6 秒）
/usr/bin/python3 code/test_sbox_fhe.py                   # 7 个单元测试（约 10 秒）
/usr/bin/python3 theory/check_mvpbs_noise.py > theory/check_mvpbs_noise.log   # P3（约 7 秒）
python3 ../../skills/bib-verify/scripts/verify_bib.py refs.bib > bib-verify-report.md  # P1（需联网）
/usr/bin/python3 code/run_experiments.py                 # P5，经 crbench（约 2.5 分钟）
for s in falsify/C*/*.py; do /usr/bin/python3 "$s" | tee "${s%.py}.log"; done   # P6（约 1 分钟）
/usr/bin/python3 code/run_experiments.py --sanitise-only # 清洗 results/ 中的路径与主机名
/usr/bin/python3 code/make_figures.py                    # P7 图，只读 results/
(cd paper && make && latexmk -c)                         # P7 PDF（使用 TeX 发行版自带的 llncs）
for f in paper/main.tex paper/sections/*.tex; do
  PYTHONPATH=../../lib/bench /usr/bin/python3 -m crbench audit-tex "$f" EVIDENCE.md --check-ledger --root .
done                                                     # P7 闸门：论文中每个数字都有账本行
for ph in P0 P1 P2 P3 P4 P5 P6 P7 P8; do
  /usr/bin/python3 ../../skills/phase-gate/scripts/gate_check.py --project . --phase $ph --paper paper
done                                                     # 机械化闸门检查
```

使用 `/usr/bin/python3` 是因为它装有 numpy；代码自行把 `lib/cryptomath` 与 `lib/bench` 加入 `sys.path`，无需安装。
C3 的证伪脚本会自己重跑一次 crbench 实验（k = 64）；加 `--reuse` 则只重新解析日志。

## 各阶段

### P0 立项 · `/cra-init case-study/toy-mvpbs`，然后 `/cra-phase P0`
- **Agent：** `pi-orchestrator`。
- **读：** 人给的一句话题目；`workflows/PHASES.md`。
- **写：** `STATE.md`（论点 v0：“MV-PBS 以 k 倍速度计算 S 盒且正确性不变”——故意写得过强，留给证伪者削弱），
  止损日期、模拟投稿目标；`DECISIONS.md` **D-1**：只有“按比特切片输出”的情形才值得研究——若只需要一个半字节密文，
  用 f = S 的一次 PBS 就够了。
- **P0 闸门：** 论点可证伪、目标已定、止损日期已设 → 通过。

### P1 文献 · `/cra-lit "multi-value bootstrapping TFHE LUT"`
- **Agent：** `lit-scout`（skill：`eprint-search`、`lit-matrix`、`bib-verify`），`math-librarian`（skill：`textbook-index`）。
- **读：** `references/reading-lists/fhe-bootstrapping.md`、ePrint/Crossref；`references/textbooks/CATALOG.md`、`TOPIC-MAP.md`。
- **写：** `LITERATURE.md`（8 篇公开文献：CGGI16/17/20、DM15、CJP21、CIM19、GBA21、PRESENT07；最强基线 = 同一库内逐比特 PBS），
  `refs.bib`，`bib-verify-report.md`（**8/8 VERIFIED**；LNCS 卷号无法机器核验，于是**删除而不是凭记忆补写**），
  `MATH-REFS.md`（商环与分圆多项式事实引 Dummit–Foote，结构化矩阵引 Meyer；目录中缺概率论教材，这一缺口已报告 PI）。
- **P1 闸门：** “≥ 15 篇”一项以 DECISIONS 引用**豁免**（D-2）——`gate_check.py` 只接受 `- [~] … WAIVED: … (DECISIONS D-2)` 这种写法。

### P2 构思 · `/cra-ideas "4 blind rotations for one S-box"`
- **Agent：** `idea-miner`（skill：`idea-mining-loop`；可选 `workflows/idea-tournament.js`）；`falsifier` 在想法成为主张前先筛。
- **读：** `LITERATURE.md`；`cryptomath.costmodel.Counter` 的运算计数（逐比特 PBS 每个 S 盒 4 × 32 次 CMux）。
- **写：** `IDEAS.md`——**I1**（共享盲旋转 = MV-PBS）晋级；**I2**（用 Gray 码重排输入以减小 ‖d_i‖）在筛选时**被否决**：
  重新编码输入本身就是一次查表，即多一次 PBS；**I3**（CMux 树）晋级为主张，后被证伪。`CLAIMS.md` 登记 C1–C5，状态 `open`，各带否决条件。
- **P2 闸门：** 至少一个想法有成本模型收益与否决条件；主张已登记 → 通过。

### P3 理论 · `/cra-phase P3`（调度 `theorist`）
- **Agent：** `theorist`（skill：`sage-check`；`param-estimation` 按 D-1 跳过——玩具参数本就不安全）；
  `math-librarian` 回答“(1 − X) 在哪里可逆？”。
- **读：** `IDEAS.md` I1、`MATH-REFS.md`、`lib/cryptomath/cryptomath/fhe/noise.py`。
- **写：** `THEORY.md`——引理 L1（T_f = v0·d_f）、引理 L2（‖d_f‖² ≤ p + 2，且可取到）、定理 T1（输出方差 ‖d_f‖²·Var_BR + Var_KS）；
  `theory/check_mvpbs_noise.py`（sage-check 格式：每条陈述一行 JSON，有反例则退出码 1）及其日志：L1 在 66 564 个查表函数上验证、L2 穷举、T1a 蒙特卡洛比值 0.955–1.029。
- **改变计划的发现：** 默认参数 T1 下，密钥切换噪声（2^-12.13）压过盲旋转噪声（2^-14.47），MV-PBS 的噪声放大看不见，
  主张 C2 在那里无法被攻击。→ **D-3**：增加一个故意加噪的参数集 T2（GLWE σ = 2^-22）。
- **P3 闸门：** 每条引理都做了数值检验 → 通过。

### P4 基线 · `/cra-phase P4`（调度 `baseline-engineer`）
- **Agent：** `baseline-engineer`（skill：`baseline-pin`）。
- **读：** `references/baselines/MANIFEST.md`（TFHE-rs、tfhe C++ 的构建配方）。
- **写：** `baselines/MANIFEST.md`：公平基线是库自带的 `pbs`，密钥、编码、参数、计时范围与线程数都相同；
  在任何数字出现之前就把 `vpack` 标为“不同类”（输入是 GGSW）；生产级库不在范围内（D-1）。
- **P4 闸门：** 公平性清单已签 → 通过。

### P5 实验 · `/cra-bench "perbit vs mvpbs vs vpack, k-scan, noise at T1/T2"`
- **Agent：** `experimenter`（skill：`bench-protocol`、`log-to-evidence`；库 `crbench`）。
- **读：** `baselines/MANIFEST.md`、`THEORY.md`（T2 的定义）。
- **运行：** `code/run_experiments.py` → `crbench.runner.run_interleaved`（轮换顺序交错、1 轮预热 + 5 轮、单线程、环境采集、锁）。
  每次执行写 `results/<exp>/<arm>/r<k>.log`；每个实验写 `run.json` 与 `summary.log`。
- **P5 内部的回路（D-4）：** 第一次运行用墙钟时间，共享机器负载一度达到 70；逐比特 PBS 的 IQR 为 257 ms（中位数 383 ms），
  k = 4 加速比置信区间为 [3.10, 6.25]。experimenter 改用进程 CPU 时间（代码单线程；每个样本旁仍记录墙钟时间）后重跑：
  IQR 0.5 ms、区间 [3.79, 3.95]。被取代的数字从未进入账本。
- **写：** `EVIDENCE.md`（E1–E22：论文中印出的值、命令、日志路径、代码哈希、主机哈希、日期、重复次数/统计量）；
  `crbench evidence check EVIDENCE.md --root .` → 22 行、0 错误。
- **主要测量值：** 每个 S 盒，逐比特 PBS 291.2 ms 对 MV-PBS 75.4 ms → **3.86× [3.79, 3.95]**；
  k = 1..4 的扫描为 0.96×、2.00×、2.95×、3.96×；在 T2 下 MV-PBS 的 S 盒失败率为 14/128（k = 1）… **32/128（k = 4）**，逐比特 PBS 为 0/128。
- **P5 闸门：** 交错、≥ 3 次重复、中位数、环境已采集、候选数字全部入账 → 通过。

### P6 证伪闸门 · `/cra-falsify`（或 `workflows/falsify-round.js`）
- **Agent：** `falsifier`（skill：`falsify`，攻击顺序：定义 → 量词 → 边界参数 → 数值重算 → 基线公平性 → 文献）。
  每次攻击都是 `falsify/<claim>/` 下的一个脚本，输出 `.log` 放在旁边。
- **写入 `CLAIMS.md` 的裁决：**

| 主张 | 裁决 | 依据 |
|---|---|---|
| C1 T1 下的正确性 | **存活** | 3 组密钥种子 × 全部输入 + 极端查表（‖d‖² 最大为 18）：256/256 正确 |
| C2 “与逐比特 PBS 正确性相同” | **削弱** | T2 下对每个 k，MV-PBS 失败率的置信区间都在逐比特之上；采用措辞：*仅当* ‖d_i‖²·Var_BR + Var_KS 仍在解码余量内时正确性相同 |
| C3 “对所有 k ≤ 64，加速比 ≥ 0.9k” | **证伪** | 提出者只测了 k ≤ 4；证伪者在范围边界跑 crbench：k = 64 得 43.67× [42.53, 44.63] < 57.6（Amdahl：每个查表的后处理无法摊薄） |
| C4 “k = 4 加速比落在 [3, 4)” | **存活**（有证据） | 从每次执行的原始日志重算，配置一致、输出全对：3.86× [3.79, 3.95] |
| C5 “CMux 树比 MV-PBS 快 ≥ 5 倍” | **证伪** | 原始 7.81× 属实，但比较的是 GGSW 输入与 LWE 输入；加上提取比特和最便宜的电路自举后，端到端下界 ≥ 376 ms，即 ≤ 0.20× |
| C6 饱和（取代 C3） | **存活** | 由证伪者提出，从原始日志重新解析 |

- **退回之处：** C3 被证伪后交给 PI，PI 用 C6 取代它，而不是把主张范围缩到 k ≤ 4（那会掩盖这个效应）——**D-5**。
  C5 被证伪后，vpack 的数字从叙述中删除。C2 的削弱措辞成为论文中定理 1 之后那段话的原文。
- **P6 闸门：** 无 open 主张；被证伪的主张不进入叙述；采用削弱后的措辞 → `gate_check.py --phase P6` 通过。

### P7 写作与作图 · `/cra-write <section>` 与 `/cra-figure "speed-up vs k; failure vs k"`
- **Agent：** `writer`（skill：`paper-playbook`），`figure-artist`（skill：`paper-figures`，`figures/PATTERNS.md` 中的 P01 模式，`figures/style/palette.py`）。
- **读：** `CLAIMS.md`（只用 C1、削弱后的 C2、C4、C6）、`EVIDENCE.md`、`THEORY.md`、`results/`。
- **写：** 从 `templates/paper/` 复制出 `paper/`（LNCS、匿名版），填写各节，数字后加 `\evid{E…}` 标签；
  `paper/figs/fig_speedup_failure.pdf` 由 `code/make_figures.py` 直接从日志生成（没有手敲的数字）；`paper/main.pdf`（5 页）。
- **检查：** 对 `main.tex` 与每个 `sections/*.tex` 运行 `crbench audit-tex` → 0 错误（`paper/audit-tex.log`）。
  机械化的 `gate_check.py --paper` 又找出两个 crbench 已放行的数（`95\%`、`2^{32}`——它的匹配比 crbench 的归一化更严格）；
  二者都是定义而非测量，所以按闸门脚本的规定在行尾加 `% no-evidence: <理由>`。它还发现了 `CLAIMS.md` 的表头不匹配（该列须以 “EVIDENCE refs” 开头）。
- **P7 闸门：** 通过。

### P8 评审 → 提交（模拟）· `/cra-review "LNCS short paper"`，然后 `/cra-submit`
- **Agent：** `reviewer-sim`（skill：`venue-calibration`、`mock-review`；可选 `workflows/mock-review-panel.js`），
  `submission-rebuttal`（skill：`anonymize-check`、`camera-ready`、`artifact-pack`）。
- **写：** `REVIEWS.md`——R1 轮三个角色（专家怀疑者、通才、数据审计员）、元评审与 5 条分派到 agent 的行动项；
  **D-6** 把稿件退回 P7 一次（加入饱和那句话、说明用 CPU 时间、说明半字节输出只需一次 PBS）；全部关闭。
  `SUBMISSION.md`——格式/匿名/一致性/参考文献清单基本打勾；`anon_check.py` 配私有黑名单：HIGH=0 MEDIUM=0 LOW=3（均为信息性）；
  `pdf_checks.py`：RESULT OK。真正的上传**刻意不做**（未经本人同意，工具包绝不把任何东西发出本机）。
- **P8 闸门：** 通过（`gate-check.log`）。

## 值得搬到真实项目里的做法
1. 先写出*强*论点，再让证伪者把它削到站得住（C2、C3）。
2. 在主张范围的边界上检验加速比，而不是在测量过的地方（C3）。
3. 比较方法之前先核对输入/输出格式（C5）。
4. 在共享机器上，明确选定计时指标并把决定记下来（D-4）。
5. 被证伪的主张留在 `CLAIMS.md` 里；替代主张另起编号（C6）。
6. `crbench audit-tex` 与 `gate_check.py` 都要跑：二者有重叠但并不相同。
