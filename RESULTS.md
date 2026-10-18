# 实测结果 — DS V4.1 Flash（2026-10-19）

| 项 | 值 |
|---|---|
| 被测模型 | **DeepSeek V4.1 Flash**（`opencode/deepseek-v4.1-flash-free`） |
| Agent harness | **opencode v2.0.32**（`opencode run --standalone --auto --format json`） |
| 机器 | AI-3090（4× RTX 3090，24GB；本基准为 API 模型，不占 GPU） |
| 档位 | **低（low）**：3 题 × 3 trial = 9 格 |
| 完成日期 | **2026-10-19** |
| 原始记录 | `results/low.jsonl`；四指标快照 `results/summary-low.md`；冒烟/其他档见 `results/` 其余文件 |

## 四指标（总）

| 指标 | 值 |
|---|---|
| 🏆 成功率 | **7/9 = 78%** |
| ⏱️ 总耗时 | **22m44s**（9 格，均 152s/格） |
| 🪙 总 token | **557,719**（in 450,809 / out 106,910；cache 读 5,214,336） |
| ⚡ 速度 | **409 tok/s**（token 总量 ÷ 智能体墙钟） |

> 口径：token 计 in+out（不含 cache 读）；速度分母为 agent 墙钟（含工具调用与文件操作时间）；
> 成功率 = checker 判分 exit 0 的格数（非 agent 自述）；成本 $0（免费档模型）。

## 逐格明细

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
- 复现：`bash bench.sh low --harness opencode --model opencode/deepseek-v4.1-flash-free --trials 3`，随后 `bash bench.sh summary --tier low`。

## 其他档位状态（截至 2026-10-19）

| 档 | 状态 |
|---|---|
| 低 | ✅ 已完成（本文件） |
| 中 | 任务已就位（3 题 TB 子集），尚未跑真实模型 |
| 高 | 数据/流程已验证（django 克隆 + patch 生成 ✅，见 `results/swe-mini-predictions.jsonl`）；`eval` 需 `pip install swebench` + docker 后跑 |
