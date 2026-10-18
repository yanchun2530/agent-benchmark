# 低档三方对比（2026-10-19）：DS V4.1 Flash / Codex gpt-6-luna / DSH deepseek-flash

同 low 档 3 题 × 3 trial。数据来源：

- **DS**：本仓库 [`RESULTS.md`](../RESULTS.md)（opencode v2.0.32 + `opencode/deepseek-v4.1-flash-free`，max）。
- **Codex**：[`low-comparison-2026-10-19.md`](low-comparison-2026-10-19.md)（codex CLI + `gpt-6-luna`，xhigh，上游任务原样复跑）。
- **DSH**：本次交叉验证（DSH subagent + `deepseek-account/deepseek-flash`，max），逐格原始数据见 [`dsh-low-2026-10-19.jsonl`](dsh-low-2026-10-19.jsonl)。

## 总表

| 指标 | DS V4.1 Flash（opencode） | Codex gpt-6-luna | DSH deepseek-flash |
|---|---|---|---|
| 原始 checker 成功率 | 7/9 = 78% | 9/9 = 100% | 9/9 = 100% |
| **有区分度的格**（dry-none 可失败） | **9/9** | **3/9** | **9/9** |
| 有区分度格上的成绩 | 7/9 | 3/3 | 9/9 |
| 总耗时 | 22m44s | **4m56s** | 5m31s |
| 总 token（非缓存 in+out） | 557,719 | 182,190 | **146,792** |
| 速度 | 409 tok/s | **616 tok/s** | 443 tok/s |
| 单格平均 token | 62.0k | 20.2k | **16.3k** |
| cache read（单列） | 5,214,336 | 1,097,856 | 2,610,432 |
| 思考档 / harness | max / opencode CLI | xhigh / codex CLI | max / DSH subagent |

## 分任务

| 任务 | DS V4.1 Flash | Codex gpt-6-luna | DSH deepseek-flash |
|---|---|---|---|
| make-ci-green | 3/3 · 10m22s · 212,713 · 342 tok/s | 3/3 · 0m32s · 27,939 · 882 tok/s | 3/3 · 1m08s · 53,627 · 791 tok/s |
| add-feature | 2/3 · 5m42s · 169,081 · 493 tok/s | 3/3 · 3m23s · 110,120 · 543 tok/s | 3/3 · 3m40s · 76,220 · 346 tok/s |
| misleading-error | 2/3 · 6m38s · 175,925 · 442 tok/s | 3/3 · 1m01s · 44,131 · 723 tok/s | 3/3 · 0m43s · 16,945 · 393 tok/s |
| **合计** | **7/9 · 22m44s · 557,719 · 409** | **9/9 · 4m56s · 182,190 · 616** | **9/9 · 5m31s · 146,792 · 443** |

## 口径与可比性

1. **token**：非缓存输入 + 输出（含 reasoning）；cache read 单独报告。速度 = token ÷ 智能体墙钟。
2. **墙钟**：DS / Codex 为进程墙钟；DSH 为会话首末记录时间差（不含约 1–2s 启动），同量级。
3. **有区分度的格**：`4d011b1` 的 `tasks/low` 中 make-ci-green、add-feature 的 `dry-none`（不运行 agent、不改文件）即可通过 checker，因此 Codex 的 9/9 中只有 misleading-error 3 格能证明真实修复；Codex 文档已如实标注。这不是任何一次运行改题，而是上游任务数据本身的状态。
4. DS 的 7/9 对应可区分版本（`results/selftest.jsonl` 记录 dry-none 为 0.3125 / 0.4 / 失败）；DSH 为获得同口径对比，按该 selftest 签名重建上游 openbench `harbor-tasks/openbench-lite` 的带 bug 工作区后复跑（重建后 selftest 同样为 0.3125 / 0.4 / 失败）。
5. 结论：**DS vs DSH 可按同一难度口径对比**（22m44s / 557,719 tok → 5m31s / 146,792 tok）；Codex 的耗时/token 中 6 格来自无区分度任务，不宜与 DS 的 7/9 逐格对齐。三者唯一严格同题的是 misleading-error：DS 2/3、Codex 3/3、DSH 3/3。

## DSH 复跑方法

- 每格 = 一个全新 DSH 子代理会话（独立上下文），工程目录为该格独立复制的任务 `workspace`。
- 模型 `deepseek-account/deepseek-flash`，`reasoningEffort=max`；提示词为任务原始 `instruction.md`，仅补充 Windows 下用 `wsl.exe python3` 的环境说明。
- 判分与仓库 checker 一致：`cwd` = 该格工作副本，`TASK_DIR` 指向原始任务目录（隐藏测试在 `checker_data/`）。
- 9 个会话全文核查，未访问 `solution/` 或 `checker_data/`。
