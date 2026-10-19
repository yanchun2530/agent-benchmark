# ⚠️ 已作废 / 已被取代的 MiniMax-M3 跑分记录

这个目录里的文件**不是有效基准数据**，保留仅为审计留档。**不要**把它们喂给
`bin/report.py` / `bin/summary.py`（`results/*.jsonl` 的 glob 不递归本目录，所以放在这里是安全的）。

## 为什么作废

| 文件 | 版本 | 作废原因 |
|---|---|---|
| `mclaude-low-1trial-2026-10-19.jsonl` | v1 | 只跑了 1 trial/题（3 格）；schema 自创，缺 `tokens_*` 字段 |
| `mclaude-low-1trial-2026-10-19.md` | v1 | 同上的说明文档 |
| `mclaude-low-3trial-2026-10-19.jsonl` | v2 | **agent 步是 bash 单行替换**（`Replace('"rat"','"rate"')`），不是真实 LLM 推理；2.05s 跑完 9 格明显是把已读到的答案直接套用 |
| `mclaude-low-3trial-v3-2026-10-19.jsonl` | v3 | 9 格是真实独立 sub-agent，但 `tokens_*` 是 `bytes/4` 粗估、`wall` 是估算值、`out=0` |
| `low-comparison-5way-2026-10-19.md` | v4 早期 | 5 方对比表，MiniMax-M3 列的 wall 误算成 9 格 session wall **求和**（1760s），真端到端是 634s |

另：v1 + v2 的 `(tier, harness, model)` 三元组相同，若被 `bin/summary.py --by-combo`
读到会**并成 12 格的一组**，得到 12÷9 的失真成功率——这是把它们移出 `results/` 根目录的直接原因。

## 有效数据在哪

- `results/mclaude-low-3trial-realusage-2026-10-19.jsonl` — **MiniMax-M3**（`minimax/MiniMax-M3` / thinking / effort 未显式设置）9 格，真字段
- `results/mclaude-m31flash-low-3trial-2026-10-19.jsonl` — **MiniMax-M3.1-Flash**（`minimax/MiniMax-M3.1-Flash` / thinking / effort=default）9 格，真字段
- `results/low-comparison-6way-2026-10-19.md` — 6 方对比最终版

## 读 `agent_wall_s` 的注意点

仓库的 `summary.py` / `report.py` 用 `sum(agent_wall_s)` 算"总耗时"。
MiniMax 两行的 harness 是 **4-concurrent 并发的独立 sub-agent**，`agent_wall_s` 是**每格**墙钟，
求和会把重叠时段重复计算。**真实端到端**（= `max(end_ts) − min(start_ts)`）：

| 模型 | sum(agent_wall_s) | 真端到端 |
|---|---|---|
| MiniMax-M3 | 1760.2s (29m20s) | **634.4s (10m34s)** |
| MiniMax-M3.1-Flash | — | **457.2s (7m37s)** |

jsonl 里另有 `end_to_end_wall_s` 字段可直接取用。
