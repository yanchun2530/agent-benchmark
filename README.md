# agent_benchmark — 低/中/高三档 模型+Agent 基准包

📌 **低档实测（2026-10-19）**：[DS V4.1 Flash 与 Codex gpt-6-luna xhigh 对比](results/low-comparison-2026-10-19.md)；DS 原始记录见 [`RESULTS.md`](RESULTS.md)。

📌 **三方交叉验证（2026-10-19）**：DS / Codex / DSH（deepseek-flash）三方对比与逐格数据 → [`results/low-comparison-3way-2026-10-19.md`](results/low-comparison-3way-2026-10-19.md)、[`results/dsh-low-2026-10-19.jsonl`](results/dsh-low-2026-10-19.jsonl)。

测 **模型 × harness（opencode / codex / …）** 的组合：正确率（checker 判分）+ 速度（墙钟、tokens-per-solve）+（高档）真实仓库修复率。全部本地跑、可缩到单任务。

## 三档一览

| 档 | 内容 | 默认规模 | 预计耗时 | LLM 成本 |
|---|---|---|---|---|
| **低** `low` | openbench core 迷你仓库 3 题：`make-ci-green`（修库让 unittest 全过）、`add-feature`（给 miniconf 加 `@include`）、`misleading-error`（追根因修崩溃） | 3 题 × 3 trial | 5–15 min | 几美分 |
| **中** `mid` | Terminal-Bench 子集 3 题：`db-wal-recovery`（修损坏 SQLite WAL 恢复 11 条记录）、`raman-fitting`（Raman 谱峰拟合→JSON）、`llm-inference-batching-scheduler`（写 shape-aware 批调度器） | 3 题 × 1 trial | 15–45 min | ~$0.1–1 |
| **高** `high` | **SWE-bench Verified mini**：50 条真实 GitHub issue（django+sphinx），默认取 5 条 | 5 条 | 1–3 h（+官方评测 docker） | 视模型 |
| 附加 `speed` | 任意 OpenAI 兼容端点：TTFT / TPOT / output tok-s | 3 提示 × N 轮 | < 5 min | 极小 |

## 对比不同模型 / 不同 harness（本包的主要用法）

```bash
# 一条命令跑多条组合（同一档位、同一 trial 数 → 严格可比），跑完自动出四指标对比表
bash bench.sh matrix --tier low \
  --combos "opencode:opencode/deepseek-v4.1-flash-free,opencode:opencode/glm-5.3-flash-free,codex:gpt-5.5" \
  --trials 3

# 只看对比表（随时可看，数据来自 results/<tier>.jsonl 累积）
bash bench.sh compare --tier low

# 组合格式: harness:model，逗号分隔；也可只跑部分任务加快：
bash bench.sh matrix --tier low --combos "opencode:m1,opencode:m2" --tasks make-ci-green --trials 3
```

输出即四指标对比表（每行 = 一个 模型×harness 组合）：

| 档 | harness | 模型 | 格数 | 成功率 | 总耗时 | 总token | tok/s |
|---|---|---|---|---|---|---|---|
| low | opencode | opencode/deepseek-v4.1-flash-free | 9 | 7/9 = 78% | 22m44s | 557,719 | 409 |

> 可比性约定：**同档位、同任务集、同 trial 数**才放在一张表里比；不同 harness 用同一 `--tasks/--trials`。
> 单组合复现只是特例（`--combos` 里只写一个即可）。
>
> 思考模式/变体：模型可写成 `provider/model#variant`（opencode CLI 语法），例如
> `--model opencode/deepseek-v4.1-flash-free#max`；不同思考档位（如 `#max` vs `#medium`）**属于不同组合**，请分开统计。

## 快速开始

```bash
cd ~/agent_benchmark
bash setup.sh                       # 体检 + 首次自动拉取低/中档任务

bash bench.sh selftest              # 零成本管道校验（未动→必失败；golden→必通过）

# 低档（把模型换成你的）
bash bench.sh low  --harness opencode --model opencode/deepseek-v4.1-flash-free --trials 1

# 中档
bash bench.sh mid  --harness codex --model gpt-5.5 --timeout-min 30

# 高档（SWE-bench Verified mini）
bash bench.sh high fetch --n 5
bash bench.sh high run   --harness opencode --model <provider/model> --n 5
bash bench.sh high eval  --harness opencode --model <m>     # 需 pip3 install --user swebench + docker

# 速度
bash bench.sh speed --base-url http://localhost:8000/v1 --model <local-model>

# 汇总（成功率 / 墙钟 / tok-per-solve / $per-solve）
bash bench.sh report --by-task

# ⭐ 标准汇报口径：四指标（成功率 / 总耗时 / 总token / token-per-second）
bash bench.sh summary --tier low
```

## 目录结构

```
agent_benchmark/
├── bench.sh              # 统一入口
├── setup.sh              # 体检 + 拉任务
├── bin/
│   ├── runner.py         # 低/中档: workspace→harness→checker→JSONL（含 selftest）
│   ├── swe_mini.py       # 高档: fetch/run(生成 patch)/eval(官方 SWE-bench harness)
│   ├── speed.py          # 端点速度: TTFT/TPOT/tok-s（纯标准库）
│   ├── report.py         # 汇总报告
│   └── fetch_tasks.py    # 从 openbench 拉取任务（MIT）
├── config/
│   ├── tiers.json        # 档位定义: 任务清单/trials/超时/提示后缀
│   └── harnesses.json    # harness 命令模板（改这里接新 CLI / 新参数）
├── tasks/{low,mid}/...   # 已落盘的任务（instruction.md + workspace + checker.sh + solution/）
├── tasks/high/           # SWE-bench Verified mini 数据快照（50 条 + 默认 5 条子集）
├── work/                 # 每次运行的工位（可 bench.sh clean）
├── results/              # *.jsonl 结果 + 报告
└── data/swe-mini/        # 高档数据集/仓库缓存（按需下载）
```

## 设计要点

- **判分不怕作弊**：checker 用 `TASK_DIR` 内的干净副本跑测试（如 `make-ci-green` 的测试不取自 agent 工作区），exit 0 = 解决，可打印 `SCORE: 0..1` 部分分。
- **隔离**：每题复制 `workspace/` 到独立工位目录跑，互不污染；超时按档位（`--timeout-min`）强杀进程组。
- **数据记录**：每格一行 JSONL（含墙钟、agent 退出码、超时标志、tokens/cost 尽力解析）。`codex --json` / `opencode --format json` 的用量字段会被自动提取。
- **白盒可复现**：`selftest` 用 gold solution 验证 checker；`config/*.json` 改任务集、trial 数、超时、命令模板。

## 已知限制 / 注意

- 高档 `high run` 阶段 agent 在**未安装依赖**的 repo 里盲改（评测在官方 docker 镜像内进行，结果独立可靠）；若想让 agent 能跑测试，可自行给它建 venv。
- 高档 `eval` 需要 `pip3 install --user swebench` + docker，镜像约 1–3 GB/实例；磁盘现在只剩 ~130 GB，注意清理（`docker system prune`）。
- `codex exec` 用 `-s danger-full-access`（匿名一次性工位目录，但仍建议别在含密钥的目录跑）；opencode 用 `--standalone --auto` 私有服务 + 自动批准。
- 任务来源：低/中档 vendored 自 [openbench](https://github.com/minghinmatthewlam/openbench)（MIT），中档上游为 Terminal-Bench（Apache-2.0），任务目录内保留 `PROVENANCE.md`；高档数据来自 `MariusHobbhahn/swe-bench-verified-mini`（HF）。
