# 实测结果 — DS V4.1 Flash（2026-10-19）

| 项 | 值 |
|---|---|
| 被测模型 | **DeepSeek V4.1 Flash**（`opencode/deepseek-v4.1-flash-free`） |
| 思考模式 | **max（开启）**；9 格共产生 **94,032** reasoning token（`out 106,910` 中含此项） |
| Agent harness | **opencode v2.0.32**（`opencode run --standalone --auto --format json`） |
| 机器 | AI-3090（4× RTX 3090，24GB；本基准为 API 模型，不占 GPU） |
| 档位 | **低（low）**：3 题 × 3 trial = 9 格 |
| 完成日期 | **2026-10-19** |
| 原始记录 | `results/low.jsonl`；四指标快照 `results/summary-low.md`；冒烟/其他档见 `results/` 其余文件 |

## 两次 low 跑分一览（均为 opencode + DS V4.1 Flash）

| # | 任务版本 | 原始记录 | 成功率 | 总耗时 | 总token | tok/s |
|---|---|---|---|---|---|---|
| ① | 首跑（可区分版：selftest dry-none = 0.3125 / 0.4 / ❌） | `results/low.jsonl` | 7/9 = 78% | 22m44s | 557,719 | 409 |
| ② | 复跑（上游原样版：干净 clone `4d011b1`，未改任务） | `results/dsv41-low-upstream-2026-10-19.jsonl` | 8/9 = 89% | 27m05s | 756,040 | 465 |

> ⚠️ ② 中 `make-ci-green` / `add-feature` 上游现状 dry-none 即通过（无区分度，6 格属送分），唯一可区分题 `misleading-error` 为 2/3；① 与 ② 任务难度不同，横向对比请用同一版本。

## 四指标（总）— ① 首跑（可区分版）

| 指标 | 值 |
|---|---|
| 🏆 成功率 | **7/9 = 78%** |
| ⏱️ 总耗时 | **22m44s**（9 格，均 152s/格） |
| 🪙 总 token | **557,719**（in 450,809 / out 106,910，其中 reasoning 94,032；cache 读 5,214,336） |
| ⚡ 速度 | **409 tok/s**（token 总量 ÷ 智能体墙钟） |

> 口径：token 计 in+out（不含 cache 读）；速度分母为 agent 墙钟（含工具调用与文件操作时间）；
> 成功率 = checker 判分 exit 0 的格数（非 agent 自述）；成本 $0（免费档模型）。

## 四指标（分任务）— ① 首跑（可区分版）

| 任务 | 成功率 | 总耗时 | 总token | tok/s |
|---|---|---|---|---|
| make-ci-green | 3/3 = 100% | 10m23s | 212,713 | 342 |
| add-feature | 2/3 = 67% | 5m43s | 169,081 | 493 |
| misleading-error | 2/3 = 67% | 6m38s | 175,925 | 442 |
| **合计** | **7/9 = 78%** | **22m44s** | **557,719** | **409** |

> 快照文件：`results/summary-low.md`（总）、`results/summary-low-tasks.md`（分任务）。
> 生成命令：`bash bench.sh summary --tier low [--by-task] --md <file>`

## 逐格明细 — ① 首跑（可区分版）

| 题目 | trial | 结果 | 墙钟 | score | token(in/out) |
|---|---|---|---|---|---|
| make-ci-green | 1 | ✅ | 267s | 1.00 | 67,010 (54,618/12,392) |
| make-ci-green | 2 | ✅ | 154s | 1.00 | 65,701 (49,275/16,426) |
| make-ci-green | 3 | ✅ | 202s | 1.00 | 80,002 (58,015/21,987) |
| add-feature | 1 | ✅ | 174s | 1.00 | 71,237 (57,767/13,470) |
| add-feature | 2 | ✅ | 122s | 1.00 | 64,541 (55,562/8,979) |
| add-feature | 3 | ❌ | 46s | 0.40 | 33,303 (30,780/2,523) |
| misleading-error | 1 | ✅ | 106s | — | 35,999 (29,960/6,039) |
| misleading-error | 2 | ❌ | 50s | 0 | 17,107 (15,229/1,878) |
| misleading-error | 3 | ✅ | 243s | — | 122,819 (99,603/23,216) |

## 观察（供参考）

- **抖动明显**：同一题、同参数多次跑，既有 46s 提前放弃（`add-feature t3` 只过 40% 测试），也有 267s 死磕成功；`misleading-error` 2 次中 1 次失败。n=1 或 n=3 的数字只能当冒烟，做对比请 ≥3 trial 并看分布。
- 该模型 token 消耗中 cache 读占比极高（5.2M cache vs 0.56M in+out），说明多轮 agent 循环中前缀复用充分 → 真实计费成本会显著低于标称。
- 复现（同配置）：`bash bench.sh low --harness opencode --model opencode/deepseek-v4.1-flash-free --trials 3`，随后 `bash bench.sh summary --tier low`。
- 对比（换模型/harness）：`bash bench.sh matrix --tier low --combos "opencode:<模型A>,opencode:<模型B>,codex:<模型C>" --trials 3`，跑完自动出四指标对比表（或随时 `bash bench.sh compare --tier low`）。

## ② 复跑：上游原样任务（2026-10-19 早，隔离 clone）

环境：上游 `4d011b1` 全新 clone（任务与 Codex/DSH 跑分所用版本一致），agent 工位为该 clone 内的 `work/` 副本，不接触 `solution/`、`checker_data/`；harness / 模型 / 思考模式同 ①。

### 四指标（总）

| 指标 | 值 |
|---|---|
| 🏆 成功率 | **8/9 = 89%**（其中唯一可区分题 `misleading-error` 2/3） |
| ⏱️ 总耗时 | **27m05s**（9 格，均 181s/格） |
| 🪙 总 token | **756,040**（in 610,157 / out 145,883；cache 读 5,740,032） |
| ⚡ 速度 | **465 tok/s** |

### 四指标（分任务）

| 任务 | 成功率 | 总耗时 | 总token | tok/s |
|---|---|---|---|---|
| add-feature | 3/3 = 100% | 11m19s | 356,909 | 526 |
| make-ci-green | 3/3 = 100% | 11m28s | 305,506 | 444 |
| misleading-error | 2/3 = 67% | 4m19s | 93,625 | 362 |
| **合计** | **8/9 = 89%** | **27m05s** | **756,040** | **465** |

### 逐格明细

| 题目 | trial | 结果 | 墙钟 | score | token(in/out) |
|---|---|---|---|---|---|
| make-ci-green | 1 | ✅ | 336s | 1.00 | 131,473 (108,028/23,445) |
| make-ci-green | 2 | ✅ | 111s | 1.00 | 39,010 (27,925/11,085) |
| make-ci-green | 3 | ✅ | 241s | 1.00 | 135,023 (103,384/31,639) |
| add-feature | 1 | ✅ | 275s | 1.00 | 162,734 (133,143/29,591) |
| add-feature | 2 | ✅ | 278s | 1.00 | 137,666 (110,351/27,315) |
| add-feature | 3 | ✅ | 126s | 1.00 | 56,509 (44,521/11,988) |
| misleading-error | 1 | ✅ | 106s | — | 50,040 (44,921/5,119) |
| misleading-error | 2 | ✅ | 119s | — | 33,713 (29,738/3,975) |
| misleading-error | 3 | ❌ | 33s | — | 9,872 (8,146/1,726) |

> 快照：`results/summary-dsv41-low-upstream-2026-10-19.md`（总）、`...-tasks.md`（分任务）。
> 同版本任务下的 Codex 对比见 [`results/low-comparison-3way-2026-10-19.md`](results/low-comparison-3way-2026-10-19.md) 末尾补充节。

## ③ GLM-5.3 Flash Free：上游原样任务（2026-10-19 上午主跑 / 下午重测，隔离 clone）

环境：上游 `4d011b1` 全新 clone（同 ② 口径，与 Codex/DSH 同题版本）；harness 同前（opencode CLI），模型 `opencode/glm-5.3-flash-free`（max 默认）。

### 四指标（总）

| 指标 | 值 |
|---|---|
| 🏆 成功率 | **8/9 = 89%**（唯一可区分题 `misleading-error` 2/3） |
| ⏱️ 总耗时 | **19m31s**（9 格，均 130s/格） |
| 🪙 总 token | **347,731**（in 309,761 / out 37,970；cache 读 2,334,784） |
| ⚡ 速度 | **297 tok/s** |

### 四指标（分任务）

| 任务 | 成功率 | 总耗时 | 总token | tok/s |
|---|---|---|---|---|
| add-feature | 3/3 = 100% | 3m56s | 100,132 | 425 |
| make-ci-green | 3/3 = 100% | 10m19s | 133,202 | 215 |
| misleading-error | 2/3 = 67% | 5m16s | 114,397 | 362 |
| **合计** | **8/9 = 89%** | **19m31s** | **347,731** | **297** |

### 逐格明细

| 题目 | trial | 结果 | 墙钟 | score | token(in/out) |
|---|---|---|---|---|---|
| add-feature | 1 | ✅ | 66s | 1.00 | 35,234 (33,829/1,405) |
| add-feature | 2 | ✅ | 119s | 1.00 | 28,393 (24,246/4,147) |
| add-feature | 3 | ✅ | 51s | 1.00 | 36,505 (33,502/3,003) |
| make-ci-green | 1 | ✅ | 175s | 1.00 | 40,953 (35,922/5,031) |
| make-ci-green | 2 | ✅ | 337s | 1.00 | 67,670 (54,474/13,196) |
| make-ci-green | 3 | ✅ | 107s | 1.00 | 24,579 (21,458/3,121) |
| misleading-error | 1 | ❌ | 61s | — | 30,556 (29,250/1,306) |
| misleading-error | 2 | ✅ | 56s | — | 46,928 (46,109/819) |
| misleading-error | 3 | ✅ | 199s | — | 36,913 (30,971/5,942) |

> 记录：`results/glm53-low-2026-10-19.jsonl`；快照：`results/summary-glm53-low-2026-10-19{,-tasks}.md`。
> misleading-error 取重测批 A 三格（见下方勘误节）；重测双批留档 `results/glm53-low-misleading-redo-2026-10-19.jsonl`。

### 同题四方对比（low · 上游原样 · 均 3×3）

| 指标 | GLM-5.3 Flash（opencode） | DS V4.1 Flash（opencode） | Codex gpt-6-luna | DSH deepseek-flash |
|---|---|---|---|---|
| checker 成功率 | 8/9 | 8/9 | 9/9* | 9/9 |
| 总耗时 | **19m31s** | 27m05s | 4m56s | 5m31s |
| 总 token（非缓存 in+out） | 347,731 | 756,040 | 182,190 | **146,792** |
| tok/s | 297 | 465 | **616** | 443 |
| misleading-error（唯一可区分题） | 2/3 | 2/3 | 3/3 | 3/3 |

*Codex 9/9 中 6 格为无区分度送分；严格同题有效对比见 misleading-error 行。

### 勘误：GLM 首批 misleading-error 三格假阳性（已剔除）

- 现象：首批三格 5–6s 即 ✅，但 agent 进程 rc=1、0 token（opencode 调用瞬间失败、空跑）。
- 根因链：**DS ② 批 t3 的 agent（06:16）跑出自己的工作目录，越界修改了 tasks/ 原题库** `workspace/settings.json`（`"rat"` → `"rate"`），污染了底座；GLM 批复制到已修复底座 + 空 agent ⇒ 判分假通过。
- 处置：`git checkout` 还原底座 → 复验 dry-none 失败（区分度恢复）→ misleading-error 重测两批（批A 2/3、批B 3/3）；本节数据取批A。
- 启示：**runner 应在每格前后校验 tasks/ 完整性**；DS 批内 t3 的 checker 判分不受影响（判分用的是其自身副本），但「t3 仅 33s 失败」当时未识别为可疑。

## ④ MiniMax-M3 / MiniMax-M3.1-Flash（MiniMax Code 桌面会话 · 独立 sub-agent harness）

📌 **6 方完整对比表（DS / Codex / DSH / GLM / M3 / M3.1-Flash）** → [`results/low-comparison-6way-2026-10-19.md`](results/low-comparison-6way-2026-10-19.md)

| 模型 | harness | 成功率 | 总耗时（端到端） | 总 token | tok/s | 原始记录 |
|---|---|---|---|---|---|---|
| `minimax/MiniMax-M3`（thinking） | 独立 mavis worker session（每格 fresh context） | **9/9 = 100%** | 10m34s | 268,589 | 423 | [`mclaude-low-3trial-realusage-2026-10-19.jsonl`](results/mclaude-low-3trial-realusage-2026-10-19.jsonl) |
| `minimax/MiniMax-M3.1-Flash`（thinking / effort=default） | 同上 | **9/9 = 100%** | **7m37s** | **226,090** | **494** | [`mclaude-m31flash-low-3trial-2026-10-19.jsonl`](results/mclaude-m31flash-low-3trial-2026-10-19.jsonl) |

- **协议**：与其它方完全一致（同一任务版本 `4d011b1`、3 题 × 3 trial、judge 用仓库原生 checker、父端复跑校验 `solved`）。每格 = 一个**全新的独立 mavis 子会话**，只见任务 instruction 与自己的 workspace 副本，不见其它 trial 的上下文。
- **token/wall 是真值**：从 mavis runtime 的 `local_runtime_token_usage` 逐 session 汇总（非估算）。`agent_wall_s` = 每格墙钟；另有 `end_to_end_wall_s` = 全部 9 格的**真实端到端**跨度。
- **⚠ 墙钟口径**：`bin/summary.py` 原本用 `sum(agent_wall_s)` 算总耗时，对**并发** harness 会把重叠时段重复计算（MiniMax 两行会虚报成 29m20s / 21m04s）。已加法式修正：行内带 `end_to_end_wall_s` 时改用该值，现有文件行为不变。
- **真区分提醒**：与其它方一样，上游 `4d011b1` 的 make-ci-green / add-feature 是 dry-none 送分，**只有 misleading-error 3 格真测模型**（M3 与 M3.1-Flash 均 3/3）。
- **⚠ 作废记录**：早期几版（1-trial 演示、bash 单行替换的"抄答案"版、rough-est 版）已移入 [`results/_superseded/`](results/_superseded/)，**不要**喂给 `bin/report.py` / `bin/summary.py`（放子目录正是因为 `results/*.jsonl` 的 glob 不递归）。原因见该目录 README。

## 其他档位状态（截至 2026-10-19）

| 档 | 状态 |
|---|---|
| 低 | ✅ 已完成（本文件） |
| 中 | 任务已就位（3 题 TB 子集），尚未跑真实模型 |
| 高 | 数据/流程已验证（django 克隆 + patch 生成 ✅，见 `results/swe-mini-predictions.jsonl`）；`eval` 需 `pip install swebench` + docker 后跑 |
