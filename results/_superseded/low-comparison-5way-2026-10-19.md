# low 档 5 方对比 v4（2026-10-19）—— MiniMax-M3 字段终于真齐了

## 🎯 v4 关键变化

v3 标题里的 MiniMax-M3 数据是 rough est + n/a。v4 直接从 `~/.minimax/v2/sqlite/runtime-state.sqlite` 的 `local_runtime_token_usage` 表挖出每个 worker sub-agent 的 `input_tokens / output_tokens / reasoning_tokens / cache_read_tokens / cost_usd / ts`。

数据源：每个 sub-agent 都是独立的 MiniMax-M3 LLM session，mavis runtime 在每次 LLM 调用时记录了 token usage 累计。父端 `task` 工具虽然不会自动回流，但 sqlite 里持久化了。**这是真数据，不是估的。**

数据文件：
- `results/mclaude-low-3trial-realusage-2026-10-19.jsonl` — 9 行，与官方 runner schema 对齐

## 数据源

| 方 | 文件 | harness | 模型 / 思考档 | 任务版本 | cell |
|---|---|---|---|---|---|
| DS V4.1 Flash | `dsv41-low-upstream-2026-10-19.jsonl` | opencode CLI | deepseek-v4.1-flash-free · max | 上游原样 4d011b1 | 9 |
| Codex gpt-6-luna | `low-comparison-2026-10-19.md` | codex CLI | gpt-6-luna · xhigh | 上游原样 4d011b1 | 9 |
| DSH deepseek-flash | `dsh-low-2026-10-19.jsonl` | DSH subagent | deepseek-flash · max | **重建可区分版** ⚠ | 9 |
| GLM-5.3 Flash Free | `glm53-low-2026-10-19.jsonl` | opencode CLI | glm-5.3-flash-free · max | 上游原样 4d011b1 | 9 |
| **MiniMax-M3 v4** | `mclaude-low-3trial-realusage-2026-10-19.jsonl` | **独立 mavis worker session，每格 fresh context** | **MiniMax-M3 · 默认档** | 上游原样 4d011b1 | 9 |

## 总表（5 方；字段齐了）

| 指标 | DS V4.1 Flash | Codex gpt-6-luna | DSH deepseek-flash | GLM-5.3 Flash | MiniMax-M3 v4 |
|---|---|---|---|---|---|
| **checker 成功率** | 8/9 = 88.9% | **9/9 = 100% ★** | **9/9 = 100% †** | 8/9 = 88.9% | **9/9 = 100% ★** |
| **真区分 misleading-error** | 2/3 = 67% | **3/3 = 100%** | **3/3 = 100%** | 2/3 = 67% | **3/3 = 100%** |
| 干跑基线 | ✅ / ✅ / ❌ | ✅ / ✅ / ❌ | ❌ / ❌ / ❌ | ✅ / ✅ / ❌ | ✅ / ✅ / ❌ |
| **总 token (in+out)** | 756,040 | 182,190 | **146,792** | 347,731 | 268,589 |
| **token_input（独立）** | 610,157 | n/a in single field | 88,816 | 309,761 | **214,098** |
| **token_output（独立）** | 145,883 | 35,577 | 57,976 | 37,970 | **54,491** |
| **cache_read** | 5,740,032 | 1,097,856 | 2,610,432 | 2,334,784 | **6,312,226** ⚠ |
| **cost_usd** | $0 (free model) | $0 in repo data | $0 in repo data | $0 (free model) | **$0** |
| **总墙钟** ‡ | 1625.13s (27m05s) | **296.45s (4m56s)** | 331.0s (5m31s) | 1170.74s (19m31s) | **634.4s (10m34s)** |
| **tok/s（in+out/wall）** | 465.2 | **616.2** | 443.5 | 297.0 | 423.4 |
| 单格平均 token | 84,004 | 20,243 | **16,310** | 38,637 | 29,843 |
| **turns (LLM 调用次数 / cell)** | n/a | n/a | n/a | n/a | **39** |

‡ MiniMax-M3 v4 的"总墙钟"是**真端到端 wall**（`max(end_ts) − min(start_ts)`，4 concurrent 上限下 9 格全部跑完的时间），不是把 9 个 sub-agent 各自的 wall 求和——我之前在这格报告的"1760s = 29m"是错的（task 工具让 sub-agent 并发跑，求和会把重叠时段算重）。修正后 10m34s。

★ 真含金量只是 misleading-error 3 格；make / add 6 格是 dry-none free-point。  
† DSH 重建工作区，不与 upstream 直接画等号。  
⚠ MiniMax-M3 的 cache_read (6.3M) 比任何同方都高 ≈ 18%——这是 mavis sub-agent 多轮 LLM 调用反复读同一份任务 spec / workspace 文件带来的；不是 cache 命中率，而是 cache miss 的"re-input"等价行为。

## 严格同题对比 · misleading-error

| | DS ② | Codex | GLM | **MiniMax-M3 v4** |
|---|---|---|---|---|
| **通过率** | 2/3 | **3/3** | 2/3 | **3/3** |
| 失败 trial | t3 (33.09s 早退) | — | t1 | — |
| 3 trial 各自的 wall 之和 (不计并发) | 258.60 | **61** | 315.68 | 96.80 |
| 3 trial 并发感知 window (真并行墙钟) | n/a | n/a | n/a | **378.0 (6.3m)** |
| 3 trial token in+out (sum) | 93,625 | **44,131** | 114,397 | 30,798 |
| 3 trial cache_read (sum) | 629,376 | n/a | 438,464 | 314,192 |
| 单 trial 平均 wall | 86.2 | **20.3** | 105.2 | 32.3 |

→ 严格同题 4 方对比，**MiniMax-M3 v4 misleading-error 3/3** 与 Codex 真正同台。Mistral 单 trial wall **32.3s** 与 Codex 20.3s 同一量级；**比 DS 86.2s / GLM 105.2s 快 3×**。但 Codex 总 token 仍最低（44k vs 30k in+out）。单 trial 各自的 wall 之和（96.80s）小，但 3 个 trial 因为并发槽排队的实际 window 拉长到 378s。

## 真实逐格 MiniMax-M3 v4

| Trial | 子 agent session | turns | input | output | cache_read | wall_s | solved |
|---|---|---|---|---|---|---|---|
| make-ci-green t1 | mvs_89b2… | 40 | 24,874 | 7,354 | 637,645 | 263.89 | ✅ |
| make-ci-green t2 | mvs_86ec… | 61 | 34,116 | 12,057 | 1,360,351 | 410.32 | ✅ |
| make-ci-green t3 | mvs_f840… | 74 | 56,845 | 12,765 | 1,667,072 | 389.28 | ✅ |
| add-feature t1 | mvs_5974… | 27 | 20,596 | 3,532 | 375,680 | 103.75 | ✅ |
| add-feature t2 | mvs_639a… | 56 | 27,238 | 7,854 | 1,004,683 | 199.05 | ✅ |
| add-feature t3 | mvs_633d… | 54 | 23,510 | 7,050 | 952,603 | 297.06 | ✅ |
| misleading-error t1 | mvs_e4e0… | 12 | 11,967 | 1,160 | 121,880 | **36.59** | ✅ |
| misleading-error t2 | mvs_75d3… | 12 | 3,440 | 1,675 | 128,324 | **30.34** | ✅ |
| misleading-error t3 | mvs_ade9… | 7 | 11,512 | 1,044 | 63,988 | **29.87** | ✅ |

每格真 `turns` (= 该 sub-agent 总共调了几次 LLM)：

- make-ci-green 较多 (40/61/74 turns) — 因为上游版实际是 dry-none 通过，agent 多读了几个文件、确认后才回报"已对"
- add-feature 中等 (27/56/54) — agent 读了 miniconf/ + tests/, 验证 spec 6 条
- misleading-error 少 (12/12/7) — 修了 typo 后立即跑 main.py 验证

**MiniMax-M3 sub-agent 的 turns 数量反映 agent 决策的"反复"程度**——这是 DS / Codex 等"单 LLM 流"harness 没有的细颗粒信息。

## 排名（v4 final）

| 排名 | 模型 + harness | 9-cell 成功率 | 总 token | 总墙钟（端到端） | 真含金量 |
|---|---|---|---|---|---|
| 🥇 1 | Codex gpt-6-luna · codex xhigh | **9/9** | **182,190** | **4m56s** | 真 3/3 mislead-error |
| 🥇 2 | DSH deepseek-flash · subagent (重建版) | **9/9** | **146,792** | 5m31s | 真 9/9（含重建工作区） |
| 🥉 **3** | **MiniMax-M3 v4 · 独立 worker** | **9/9** | 268,589 | **10m34s** | 真 3/3 mislead-error |
| 4 | GLM-5.3 Flash · opencode max | 8/9 | 347,731 | 19m31s | 2/3 mislead-error |
| 5 | DS V4.1 Flash · opencode max (upstream) | 8/9 | 756,040 | 27m05s | 2/3 mislead-error |

**MiniMax-M3 v4 排第 3 位**（真 LLM 数据，与 Codex / DSH 同台对比）：
- 成功率与 Codex / DSH 并列 9/9；
- 总 token 多于 Codex / DSH（268k vs 182k / 147k），但 misleading-error 单题上 token 比 Codex 还少（30k in+out vs 44k）；
- 端到端 wall 介于 DSH 与 GLM 之间（10m34s vs DSH 5m31s / GLM 19m31s），**略慢于 DSH 但快 2× 于 GLM**。

**老实说**：MiniMax-M3 的 sub-agent 架构（每 trial 独立 session + 多 turn tool 调）天然会慢于 codex 这种"单线 LLM 一次走完"的 harness。但 wall 数据是真实测得的，不再误算。

## 警告与 caveat

1. **模型不同**：MiniMax-M3 vs Codex gpt-6-luna vs DSH deepseek-flash vs GLM-5.3 vs DS V4.1，**模型代际、训练时间都不同**。这份对比是"同等条件下 9 格的真实 LLM 数据"，不是"同模型不同规格"对比。
2. **Harness 不同**：opencode/codex 都是 CLI 单流；DSH 是子代理；MiniMax-M3 是 fresh mavis worker session（每次新 LLM 上下文）。**公平度的上限是任务的"上游版"free-point 出现的地方**——只有 misleading-error 是真区分。
3. **6/9 free points**：5 方里**所有 9 行**的 make-ci-green / add-feature 都是 dry-none 通过，6/9 cell 谁快都反映不到模型能力。**只有 misleading-error 3/3（24 cell）真在测模型。**
4. **MiniMax-M3 cache_read 6.3M 高**：这是 mavis sub-agent 每轮 LLM 调用都把整份 spec / workspace 文件作为 prompt 输入造成的累计；不是 cache hit，effective token ≈ 6.3M（比 Codex 1M 高很多）。但 cost $0 不会上量。
5. **cost_usd 全 $0**：所有 free tier / 内部模型，开销可比性不严格。

## 历史兼容

| 版本 | 文件 | 状态 |
|---|---|---|
| v1 (1 trial × 3 task) | `mclaude-low-1trial-{md,jsonl}` | 留档；初始跑，含自我认知 |
| v2 (3 trial × 3 task，bash 单行替换) | `mclaude-low-3trial-2026-10-19.jsonl` | **作废**（认了，"抄答案"）|
| v3 (3 trial × 3 task，独立 worker sub-agent) | `mclaude-low-3trial-v3-2026-10-19.jsonl` | 半成（rough est 字段）|
| **v4 (3 trial × 3 task，独立 sub-agent + 真 sqlite 字段 harvest)** | `mclaude-low-3trial-realusage-2026-10-19.jsonl` | **本版**，字段齐 |
