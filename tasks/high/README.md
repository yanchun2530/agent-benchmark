# 高档任务数据 — SWE-bench Verified mini（快照）

- `instances.jsonl` — 全量 **50 条真实 GitHub issue**（仅 django/django 与 sphinx-doc/sphinx 两个仓库；上游为 SWE-bench Verified 的 500 条子集，官方称难度与通过率分布一致，磁盘需求 5GB 而非 130GB）。字段：`instance_id / repo / base_commit / problem_statement / test_patch / FAIL_TO_PASS / PASS_TO_PASS / ...`。
- `subset-5.jsonl` — 默认 5 条子集（评测时的起始集合）。

## 测试流

```bash
bash bench.sh high fetch --n 5      # 刷新数据（HF datasets-server API，走 data/swe-mini/）
bash bench.sh high run --harness opencode --model <m> --n 5
                                    # git clone(blob 过滤) → git worktree @ base_commit
                                    # → agent 盲改 → git diff → SWE-bench predictions.jsonl
bash bench.sh high eval --harness opencode --model <m>
                                    # 官方 swebench harness + docker：应用 test_patch 跑
                                    # FAIL_TO_PASS/PASS_TO_PASS → 解析 resolved 结果
```

数据来源：HuggingFace `MariusHobbhahn/swe-bench-verified-mini`（快照日期 2026-10-19）。
注意：本仓库内 `instances.jsonl` 为公开数据快照；`bin/swe_mini.py` 优先读 `data/swe-mini/instances.jsonl`，缺失时回退到本目录。
