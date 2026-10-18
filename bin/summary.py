#!/usr/bin/env python3
"""Four-metric summary (the ONLY numbers we report from now on):

  1. 成功率       solved / graded cells
  2. 总耗时       sum of agent wall-clock seconds (and overall span)
  3. 总 token     sum of tokens_total (in / out / cache breakdown)
  4. token/s      total tokens / total agent wall-clock

Usage:
  python3 bin/summary.py                       # latest results/*.jsonl (graded tiers)
  python3 bin/summary.py --tier low
  python3 bin/summary.py --results results/low.jsonl
  python3 bin/summary.py --tier low --md results/summary-low.md
"""
from __future__ import annotations

import argparse
import glob
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS_DIR = os.path.join(ROOT, "results")


def load(paths: list[str]) -> list[dict]:
    rows = []
    for p in paths:
        if not os.path.exists(p) or "predictions" in os.path.basename(p):
            continue
        with open(p) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    r = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if r.get("harness") in ("dry-none", "dry-solution"):
                    continue
                rows.append(r)
    return rows


def hm(seconds: float) -> str:
    m, s = divmod(int(round(seconds)), 60)
    h, m = divmod(m, 60)
    return f"{h}h{m:02d}m{s:02d}s" if h else f"{m}m{s:02d}s"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tier", default=None)
    ap.add_argument("--results", default=None)
    ap.add_argument("--harness", default=None)
    ap.add_argument("--model", default=None)
    ap.add_argument("--md", default=None, help="also write the block to this file")
    a = ap.parse_args()

    if a.results:
        paths = [a.results]
    elif a.tier:
        paths = sorted(glob.glob(os.path.join(RESULTS_DIR, f"{a.tier}*.jsonl")))
    else:
        paths = sorted(glob.glob(os.path.join(RESULTS_DIR, "*.jsonl")))

    rows = load(paths)
    if a.harness:
        rows = [r for r in rows if r.get("harness") == a.harness]
    if a.model:
        rows = [r for r in rows if r.get("model") == a.model]
    if not rows:
        print("no results yet")
        return 1

    graded = [r for r in rows if r.get("solved") is not None]
    solved = [r for r in graded if r.get("solved")]
    walls = [r["agent_wall_s"] for r in rows if r.get("agent_wall_s")]
    total_wall = sum(walls)
    rows_with_tok = [r for r in rows if r.get("tokens_total")]
    tok_total = sum(r["tokens_total"] for r in rows_with_tok)
    tok_in = sum(r.get("tokens_input") or 0 for r in rows_with_tok)
    tok_out = sum(r.get("tokens_output") or 0 for r in rows_with_tok)
    tok_cache = sum(r.get("tokens_cache_read") or 0 for r in rows_with_tok)
    tps = tok_total / total_wall if total_wall > 0 else None

    scope = " / ".join(
        x for x in [a.tier or "all-tiers", a.harness, a.model] if x
    )
    rate = f"{len(solved)}/{len(graded)} = {100.0*len(solved)/len(graded):.0f}%" if graded else "-"
    lines = [
        f"📊 四指标汇总 — {scope}",
        f"🏆 成功率   {rate}",
        f"⏱️ 总耗时   {hm(total_wall)}（{len(walls)} 格，均 {total_wall/max(len(walls),1):.0f}s/格）",
        f"🪙 总 token {tok_total:,}（in {tok_in:,} / out {tok_out:,}"
        + (f" / cache {tok_cache:,}" if tok_cache else "")
        + "）",
        f"⚡ 速度     {tps:,.0f} tok/s（token 总量 ÷ 智能体墙钟）" if tps else "⚡ 速度     -",
    ]
    if len(rows_with_tok) != len(rows):
        lines.append(f"⚠️ {len(rows) - len(rows_with_tok)} 格缺 token 记录（未计入总量/速度）")
    block = "\n".join(lines)
    print(block)
    if a.md:
        with open(a.md, "w") as f:
            f.write(block + "\n")
        print(f"\n(written -> {a.md})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
