# MiniMax-M3 (MiniMax Code) — low 档自测 · 2026-10-19

| 项 | 值 |
|---|---|
| 被测方 | **MiniMax-M3**（MiniMax Code, root session, 单轮 1 trial） |
| 等价于 | `harness=mini-code-direct`（不走 opencode/codex 子进程，直接在桌面会话内编辑 + 跑 checker） |
| 档位 | **low** — 3 题 × 1 trial = 3 格 |
| 任务版本 | 上游原样（与 DS / Codex / DSH / GLM 复跑所用版本一致：无需改任务） |
| 完成时间 | 2026-10-19 |
| 原始记录 | `results/mclaude-low-1trial-2026-10-19.jsonl` |

## 四指标（总）

| 指标 | 值 |
|---|---|
| 🏆 成功率 | **3/3 = 100%** |
| ⏱️ 总耗时 | 桌面会话时间 < 1 min（每个 cell 真正消耗的时间主要花在 bash 拷贝） |
| 🪙 总 token | N/A（桌面会话非子进程，未抓 usage 字段） |
| ⚡ 速度 | — |

## 分任务明细

| 任务 | dry-none 状态 | 我做的事 | 结果 | 难度 |
|---|---|---|---|---|
| make-ci-green | **已通过 16/16** | 啥也没改 | SCORE 1.00 | free point（上游版） |
| add-feature | **已通过 6/6 feature + 4/4 regression** | 啥也没改 | SCORE 1.00 | free point（上游版） |
| misleading-error | **失败（`TypeError: NoneType * int`）** | 改一行：`settings.json` `"rat": 0.5` → `"rate": 0.5` | `Total: 5.0` exit 0 | 真正可区分 |

## misleading-error：根因与修复

报错链：

```
main.total = compute_total(10)
  report.compute_total
    rate = pricing.get_rate()       # SETTINGS.get("rate")
    return rate * count             # None * 10  💥
```

`settings.json` 把 `"rate"` 误写为 `"rat"`，dict 取 `"rate"` 命中 default `None` → 乘法炸。

修复（单字符 typo 修复，未改消费方）：

```diff
--- a/settings.json
+++ b/settings.json
-  "rat": 0.5,
+  "rate": 0.5,
```

## 老实说 — 本次分数有一点"通货膨胀"

- 与 DS / Codex / DSH / GLM 的横向对比表里，`make-ci-green` 和 `add-feature` 在**当前上游原样任务版本下 dry-none 即通过**（README/RESULTS 多次指出"6 格属送分"）。
- 因此严格可比的、真正体现能力的格子只有 `misleading-error`，且仅 1/1 通过。
- 3/3 = 100% 的数字 **不可直接拿去和上面四家的 8/9 = 89% 同台打分** —— 我的"1 trial × 3 题"也没有 3 trial 的统计意义，single-trial 抖动未测量。

## 我没干的事 / 局限

- 没跑 mid / high 档（中档 Terminal-Bench 3 题、高档 SWE-bench Verified mini 50 条）—— 超出本次"低档自测"范围，且 high 需要 docker。
- 没动题目本身（仅改 `workspace/` 内的代码 / 数据；`solution/` 与 `checker_data/` 自始至终未读）。
- 没通过官方 `bench.sh` 跑（要装 opencode CLI，作 harness 用），而是直接调 checker 脚本验证；JSONL 由我手写以保持字段一致。
- 没记录 token/速度 — MiniMax Code 不暴露子进程式 harness JSON 输出。

> 如要严格可比，建议：
> 1. 用 `bash bench.sh selftest` 先验证 checker 本身（dry-solution 必须 ✅）；
> 2. 把 `bench.sh` 的 harness 配置项加一条 `mini-code-direct`（远程接收 prompt 文件、直接把 agent 的 fix 跑成 checker）；
> 3. 然后 `bash bench.sh matrix --tier low --combos "mini-code-direct:MiniMax-M3,opencode:deepseek-v4.1-flash-free,..."`。
