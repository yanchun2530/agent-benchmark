# 低档基准对比（2026-10-19）

两次运行均为 low 档同一组 3 题、每题 3 轮。DS 数据取自本仓库 [RESULTS.md](../RESULTS.md)；Codex 数据来自盲测运行并按统一 token 口径重算。

| 任务 | DS V4.1 Flash（max） | Codex gpt-6-luna（xhigh） |
|---|---|---|
| make-ci-green | 成功 3/3 · 10m22s · 212,713 token · 342 tok/s | 成功 3/3 · 0m31s · 27,868 token · 892 tok/s |
| add-feature | 成功 2/3 · 5m42s · 169,081 token · 493 tok/s | 成功 3/3 · 3m11s · 107,002 token · 561 tok/s |
| misleading-error | 成功 2/3 · 6m38s · 175,925 token · 442 tok/s | 成功 3/3 · 0m51s · 41,029 token · 808 tok/s |
| **合计** | **成功 7/9 · 22m44s · 557,719 token · 409 tok/s** | **成功 9/9 · 4m33s · 175,899 token · 645 tok/s** |

## Token 口径与更正

总 token 按“非缓存输入 + 输出（含 reasoning）”统计，cache read 单独报告；tok/s 为总 token 除以 agent 墙钟。

- DS：输入 450,809 + 输出 106,910 = 557,719；cache read 5,214,336。输出中含 94,032 reasoning token。
- Codex：非缓存输入 142,022 + 输出 33,877 = 175,899；cache read 909,568。输出中含 13,447 reasoning token。
- 之前 Codex 报告的 1,072,020 有误：runner 把 cached input 算入输入总量，却漏加 reasoning 输出。根据 Codex 原始 usage 元数据重算：`1,072,020 - 909,568 + 13,447 = 175,899`。

## 运行条件与有效性

- Codex：`gpt-6-luna`，`model_reasoning_effort="xhigh"`，`workspace-write`；基准代码为 commit `812c1a1`。
- 盲测在独立副本运行，移除了参考解答目录；未查看参考解答或 agent 生成内容。
- 成功率按 checker exit 0 统计。`dry-none` 对照显示，`make-ci-green` 与 `add-feature` 不做任何修改也能通过 checker，因此 Codex 的这 6 格不能证明模型解题。具有区分度的 `misleading-error` 为 3/3。Codex 9/9 是原始 checker 成绩。
