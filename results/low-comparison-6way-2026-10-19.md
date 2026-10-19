# low 档 6 方对比 v5（2026-10-19）—— 加了 MiniMax-M3.1-Flash

## 🎯 v5 变化

1. **模型标注改成实测值**（不再猜）：从 `local_runtime_sessions.extra_data_json` 读 `effectiveModel / effectiveModelVariant / effectiveModelThinking.effort`。
2. **新增第 6 行 MiniMax-M3.1-Flash**：9 格全新独立 worker session（同 harness、同协议、同任务版本），真字段齐。
3. **MiniMax-M3.1-Flash 全面优于 MiniMax-M3**（详见下方对比）。

## 数据源

| 方 | 文件 | harness | 模型 / variant / effort | 任务版本 | cell |
|---|---|---|---|---|---|
| DS V4.1 Flash | `dsv41-low-upstream-2026-10-19.jsonl` | opencode CLI | deepseek-v4.1-flash-free · — · max | 上游原样 4d011b1 | 9 |
| Codex gpt-6-luna | `low-comparison-2026-10-19.md` | codex CLI | gpt-6-luna · — · xhigh | 上游原样 4d011b1 | 9 |
| DSH deepseek-flash | `dsh-low-2026-10-19.jsonl` | DSH subagent | deepseek-flash · — · max | **重建可区分版** ⚠ | 9 |
| GLM-5.3 Flash Free | `glm53-low-2026-10-19.jsonl` | opencode CLI | glm-5.3-flash-free · — · max | 上游原样 4d011b1 | 9 |
| **MiniMax-M3** | `mclaude-low-3trial-realusage-2026-10-19.jsonl` | 独立 mavis worker | `minimax/MiniMax-M3` · thinking · *未显式设置* | 上游原样 4d011b1 | 9 |
| **MiniMax-M3.1-Flash** | `mclaude-m31flash-low-3trial-2026-10-19.jsonl` | 独立 mavis worker | `minimax/MiniMax-M3.1-Flash` · thinking · **default** | 上游原样 4d011b1 | 9 |

## 总表（6 方）

| 指标 | DS V4.1 Flash | Codex gpt-6-luna | DSH deepseek-flash | GLM-5.3 Flash | MiniMax-M3 | **MiniMax-M3.1-Flash** |
|---|---|---|---|---|---|---|
| **checker 成功率** | 8/9 = 88.9% | **9/9**★ | **9/9**† | 8/9 = 88.9% | **9/9**★ | **9/9**★ |
| **真区分 misleading-error** | 2/3 | **3/3** | **3/3** | 2/3 | **3/3** | **3/3** |
| 干跑基线 | ✅/✅/❌ | ✅/✅/❌ | ❌/❌/❌ | ✅/✅/❌ | ✅/✅/❌ | ✅/✅/❌ |
| **端到端 wall** ‡ | 1625.1s (27m05s) | **296.5s (4m56s)** | 331.0s (5m31s) | 1170.7s (19m31s) | 634.4s (10m34s) | **457.2s (7m37s)** |
| **总 token (in+out)** | 756,040 | 182,190 | **146,792** | 347,731 | 268,589 | 226,090 |
| **token_input** | 610,157 | n/a single | 88,816 | 309,761 | 214,098 | **94,967** |
| **token_output** | 145,883 | 35,577 | 57,976 | 37,970 | 54,491 | **131,123** |
| **cache_read** | 5,740,032 | 1,097,856 | 2,610,432 | 2,334,784 | 6,312,226 | **3,693,746** |
| **cost_usd** | $0 | $0 | $0 | $0 | $0 | $0 |
| **tok/s（in+out/wall）** | 465.2 | **616.2** | 443.5 | 297.0 | 423.4 | **494.5** |
| 单格平均 token | 84,004 | 20,243 | **16,310** | 38,637 | 29,843 | 25,121 |
| **turns / cell** | n/a | n/a | n/a | n/a | 39 | **29** |

‡ **wall = 真端到端**（`max(end_ts) − min(start_ts)`，并发感知）。不是 9 个 session 各自 wall 的求和——求和会把 4-concurrent 的重叠时段重复计算，MiniMax-M3 那版曾经因此错报成 29m20s（真值 10m34s）。

## MiniMax-M3 vs MiniMax-M3.1-Flash（同 harness 同协议，唯一变量=模型）

| 指标 | MiniMax-M3 | **MiniMax-M3.1-Flash** | 变化 |
|---|---|---|---|
| 成功率 | 9/9 | **9/9** | 持平 |
| 真区分 misleading-error | 3/3 | **3/3** | 持平 |
| 端到端 wall | 634.4s | **457.2s** | **-28%** |
| 总 token (in+out) | 268,589 | **226,090** | **-16%** |
| token_input | 214,098 | **94,967** | **-56%** |
| token_output | 54,491 | 131,123 | +141% |
| cache_read | 6,312,226 | **3,693,746** | **-41%** |
| turns 总数 | 214 | **159** | **-26%** |
| tok/s | 423.4 | **494.5** | +17% |
| misleading-error token | 30,798 | **23,960** | **-22%** |

**M3.1-Flash 更省 token、更快、turns 更少**；代价是 output token 暴涨（M3.1-Flash 把更多推理写进了 output，M3 大量 reasoning 计在 input/cache）。

## 严格同题对比 · misleading-error（唯一真区分）

| | DS ② | Codex | GLM | MiniMax-M3 | **MiniMax-M3.1-Flash** |
|---|---|---|---|---|---|
| **通过率** | 2/3 | **3/3** | 2/3 | **3/3** | **3/3** |
| 失败 trial | t3 (33.09s 早退) | — | t1 | — | — |
| 3 trial 各自 wall 之和 | 258.6 | **61** | 315.7 | 96.8 | **156.1** |
| 3 trial 并发感知 window | n/a | n/a | n/a | 378.0 | **183.2** |
| 3 trial token in+out | 93,625 | **44,131** | 114,397 | 30,798 | **23,960** |
| 3 trial cache_read | 629,376 | n/a | 438,464 | 314,192 | 479,181 |
| 单 trial 平均 wall | 86.2 | **20.3** | 105.2 | 32.3 | **52.1** |
| 单 trial 平均 turns | n/a | n/a | n/a | ~10 | **~13** |

→ **在这唯一严格同题的 3/3 阵营里，MiniMax-M3.1-Flash 的 token 消耗最低（23,960，比 Codex 少 46%）**，但 wall 是 Codex 的 2.6 倍。DS ② / GLM 都只 2/3。

## 逐格 · MiniMax-M3.1-Flash

| Trial | turns | input | output | cache_read | wall_s | solved | agent 实际行为 |
|---|---|---|---|---|---|---|---|
| make-ci-green t1 | 20 | 17,142 | 17,221 | 435,171 | 160.7 | ✅ | 发现并修 `recent(0)` 的 `[-0:]` 边界 bug；**临时把 `DAILY_FEE` 改 0.99 反证 checker 真的 import 自己的工作副本**（score 掉到 0.875 后还原） |
| make-ci-green t2 | 26 | 21,174 | 27,218 | 917,166 | 266.5 | ✅ | **独立收敛到与 t1 相同的 `recent(0)` 修复**；复刻 `sys.path` 验证 `catalog.__file__`；`PYTHONPYCACHEPREFIX` 强制重编译排除陈旧 .pyc |
| make-ci-green t3 | 15 | 10,049 | 17,179 | 302,880 | 158.2 | ✅ | 逐模块对规格，判定 seed 已绿，**不改已通过的代码**；SHA-256 逐文件核对 |
| add-feature t1 | 22 | 11,475 | 22,592 | 632,700 | 223.1 | ✅ | 重写 loader.py（+32/-11），加**引号路径支持**与 **realpath 软链环检测**；自写 14 项语义校验；保持 CRLF |
| add-feature t2 | 17 | 9,836 | 12,843 | 370,552 | 124.9 | ✅ | 从别的 cwd 跑 checker 得 0/4 反证评估对象；自写 16 项语义校验（含"cwd 同名诱饵文件"反证相对路径不漂移、"菱形引用不应误报环"） |
| add-feature t3 | 21 | 15,252 | 20,149 | 556,096 | 175.0 | ✅ | 在临时目录**破坏 include 展开**跑 checker 得 0.4 反证；自写 12 项语义 + 6 项边界探测 |
| misleading-error t1 | 14 | 3,798 | 4,293 | 181,422 | 54.2 | ✅ | 完整 trace 5 层调用链，定位 `settings.json` key typo；hex dump 验证无 BOM/隐藏字符；**先复现原 traceback 再改** |
| misleading-error t2 | 15 | 3,469 | 5,783 | 190,884 | 61.5 | ✅ | grep 确认无其他模块读 `"rat"`；运行时打印 dict 验证 key 缺失返回 None；subprocess 严格校验 stdout 精确匹配 |
| misleading-error t3 | 9 | 2,772 | 3,845 | 106,875 | 40.4 | ✅ | 同 t1/t2 路径；字节级校验 stdout；清理 `__pycache__` |

## 排名（v5 final）

| 排名 | 模型 + harness | 9-cell | 端到端 wall | 总 token | 真含金量 |
|---|---|---|---|---|---|
| 🥇 1 | Codex gpt-6-luna · codex xhigh | **9/9** | **4m56s** | 182,190 | 真 3/3 mislead-error |
| 🥈 2 | DSH deepseek-flash · subagent (重建版) | **9/9** | 5m31s | **146,792** | 真 9/9（含重建工作区） |
| 🥉 **3** | **MiniMax-M3.1-Flash · 独立 worker** | **9/9** | **7m37s** | 226,090 | **真 3/3 mislead-error，token 最低** |
| 4 | MiniMax-M3 · 独立 worker | 9/9 | 10m34s | 268,589 | 真 3/3 mislead-error |
| 5 | GLM-5.3 Flash · opencode max | 8/9 | 19m31s | 347,731 | 2/3 mislead-error |
| 6 | DS V4.1 Flash · opencode max (upstream) | 8/9 | 27m05s | 756,040 | 2/3 mislead-error |

**MiniMax-M3.1-Flash 排第 3**：成功率与 Codex / DSH 并列 9/9；wall 介于 DSH 与 MiniMax-M3 之间；token 排在 DSH / Codex 之后、M3 之前；在唯一严格同题（misleading-error）上 **token 消耗是 3/3 阵营里最低的**。

**M3.1-Flash vs M3 差在哪（不只是分数）**：
- M3 在 6/9 格**没做任何改动**就报"已通过"；M3.1-Flash 在 make-ci-green 里**两个独立 trial 各自收敛到同一个真 bug**（`recent(0)` → `[-0:]` 返回全量历史），在 add-feature 里做了引号路径 + realpath 环检测的实质加固。
- M3.1-Flash 9 格里有 **5 格主动做了自证**（破坏 checker 目标反证 / 复刻 sys.path / 强制重编译 / 16 项独立语义校验）；M3 的对应描述只是"读代码 + 跑 checker"。
- M3.1-Flash turns 更少（159 vs 214）但 output token 更多——更少来回读文件，更多直接产出结论。

## Caveat（老话重说，但重要）

1. **6/9 cell 是 dry-none free-point**：所有 6 方的 make-ci-green / add-feature 在上游 4d011b1 下不改动也能通过。**只有 misleading-error 3/3（6 方 × 3 = 18 格）真在测模型。**
2. **DSH 9/9 跑在重建的带 bug 工作区**（与 DS ① 同口径），与 upstream 版不是同一难度，不能直接与 Codex / GLM / MiniMax 并排。
3. **模型代际不同**：MiniMax-M3 vs M3.1-Flash vs DS V4.1 Flash vs GLM-5.3 vs deepseek-flash vs gpt-6-luna，训练时间/规模都不同。这份表是"同协议下的真实 LLM 数据"，不是"同模型不同档位"的消融。
4. **harness 不同**：opencode / codex 是单流 CLI；DSH 是子代理；MiniMax 是 fresh mavis worker session（每次新 LLM 上下文）。turns 一列只有 MiniMax 两行有。
5. **cost_usd 全 $0**：free 模型 / 内部模型，$/solve 不可比。
6. **MiniMax 两行的 output/in 结构差异大**（M3 偏 input+cache，M3.1-Flash 偏 output），跨模型比 token 总量时要注意口径。
