# 低档基准对比（2026-10-19）

两次运行均为 low 档同一组 3 题、每题 3 轮。DS 数据取自本仓库 [RESULTS.md](../RESULTS.md)；Codex 为上游原样提示复跑，详情见本页。

| 任务 | DS V4.1 Flash（max） | Codex gpt-6-luna（xhigh） |
|---|---|---|
| make-ci-green | 成功 3/3 · 10m22s · 212,713 token · 342 tok/s | 成功 3/3 · 0m32s · 27,939 token · 882 tok/s |
| add-feature | 成功 2/3 · 5m42s · 169,081 token · 493 tok/s | 成功 3/3 · 3m23s · 110,120 token · 543 tok/s |
| misleading-error | 成功 2/3 · 6m38s · 175,925 token · 442 tok/s | 成功 3/3 · 1m01s · 44,131 token · 723 tok/s |
| **合计** | **成功 7/9 · 22m44s · 557,719 token · 409 tok/s** | **成功 9/9 · 4m56s · 182,190 token · 616 tok/s** |

## 上游与盲测审计

- Codex 跑分副本来自上游 `origin/main` commit `4d011b18320bbf5291338e3867ca0bf5f8531517`。low 档 59/59 个非答案任务文件哈希匹配；8 个 `solution` 文件未复制，副本内没有 solution 目录。
- `config/tiers.json` 与上游完全相同，使用原始任务提示。只调整 Codex harness 参数以运行 `gpt-6-luna`、`xhigh` 和 `workspace-write`。runner 仅对 `dry-solution` harness 叠加答案，本次使用 `codex`。
- 之前在 `812c1a1` 上加过防看答案提示后缀，那次结果已作废。本表只采用未改上游提示的复跑结果。未查看参考答案或 agent 生成内容。

## Token 口径与更正

总 token 按“非缓存输入 + 输出（含 reasoning）”统计，cache read 单独报告；tok/s 为总 token 除以 agent 墙钟。

- DS：输入 450,809 + 输出 106,910 = 557,719；cache read 5,214,336。输出中含 94,032 reasoning token。
- Codex：非缓存输入 146,613 + 输出 35,577 = 182,190；cache read 1,097,856。输出中含 14,284 reasoning token。
- Codex runner 原始合计 1,265,762 把 cache read 算进输入，漏加 reasoning 输出。按原始 usage 元数据重算：`1,265,762 - 1,097,856 + 14,284 = 182,190`。

## 有效性限制

独立 `dry-none` 对照显示 `make-ci-green` 和 `add-feature` 不做修改也能通过 checker；对应任务文件从对照版本 `b59bbdc` 到本次上游版本 `4d011b1` 没有变化。因此 Codex 的原始 checker 结果为 9/9，但只有 `misleading-error` 的 3/3 能证明 agent 做出了区分性修复。
