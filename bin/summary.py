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


def metrics(rows: list[dict], accounting: str = "main") -> dict:
    """The four headline numbers for a set of result rows.

    accounting="main"  -> the parent session only (the historical 口径: what
                          `opencode --format json` prints).
    accounting="all"   -> parent session + every subagent child session
                          (fields written by runner --session-accounting).
    """
    graded = [r for r in rows if r.get("solved") is not None]
    solved = [r for r in graded if r.get("solved")]
    walls = [r["agent_wall_s"] for r in rows if r.get("agent_wall_s")]
    total_wall = sum(walls)
    # Harnesses that run cells CONCURRENTLY (e.g. one independent sub-agent per
    # cell) record the real span of the whole run in `end_to_end_wall_s`.
    # Summing per-cell walls there would double-count the overlapping time, so
    # prefer the recorded span when it is present. Rows without the field keep
    # the original sum-of-walls behaviour.
    e2e = [r["end_to_end_wall_s"] for r in rows if r.get("end_to_end_wall_s")]
    if e2e:
        total_wall = max(e2e)

    def tokens(r: dict):
        if accounting == "all" and r.get("all_tokens_total"):
            return (
                r.get("all_tokens_input") or 0,
                r.get("all_tokens_output") or 0,
                r.get("all_tokens_cache_read") or 0,
                r.get("all_tokens_total") or 0,
            )
        if r.get("tokens_total"):
            return (
                r.get("tokens_input") or 0,
                r.get("tokens_output") or 0,
                r.get("tokens_cache_read") or 0,
                r.get("tokens_total") or 0,
            )
        return None

    with_tok = [(r, tokens(r)) for r in rows]
    with_tok = [(r, t) for r, t in with_tok if t]
    tok_total = sum(t[3] for _, t in with_tok)
    return {
        "cells": len(rows),
        "graded": len(graded),
        "solved": len(solved),
        "rate": (len(solved) / len(graded)) if graded else None,
        "wall_s": total_wall,
        "tok_total": tok_total,
        "tok_in": sum(t[0] for _, t in with_tok),
        "tok_out": sum(t[1] for _, t in with_tok),
        "tok_cache": sum(t[2] for _, t in with_tok),
        "tps": (tok_total / total_wall) if total_wall > 0 else None,
        "missing_tok": len(rows) - len(with_tok),
        "sub_tok": sum(r.get("subagent_tokens_total") or 0 for r in rows),
        "sub_sessions": sum(r.get("sessions_subagent") or 0 for r in rows),
        "cells_with_sub": sum(1 for r in rows if (r.get("sessions_subagent") or 0) > 0),
        "has_all": any(r.get("all_tokens_total") for r in rows),
    }


def print_table(rows: list[dict], accounting: str = "main") -> None:
    """Four-metric comparison table, one row per (tier, harness, model) combo."""
    groups: dict[tuple, list[dict]] = {}
    for r in rows:
        groups.setdefault(
            (r.get("tier") or "-", r.get("harness") or "-", r.get("model") or "-"), []
        ).append(r)
    print("| 档 | harness | 模型 | 格数 | 成功率 | 总耗时 | 总token | tok/s |")
    print("|---|---|---|---|---|---|---|---|")
    for (tier, harness, model), rs in sorted(groups.items()):
        m = metrics(rs, accounting)
        rate = "-" if m["rate"] is None else f"{m['solved']}/{m['graded']} = {m['rate']*100:.0f}%"
        tps = "-" if m["tps"] is None else f"{m['tps']:,.0f}"
        print(
            f"| {tier} | {harness} | {model} | {m['cells']} | {rate} "
            f"| {hm(m['wall_s'])} | {m['tok_total']:,} | {tps} |"
        )


def print_task_table(rows: list[dict], accounting: str = "main") -> None:
    """Four metrics per task + total (same-口径 comparability within a tier)."""
    groups: dict[tuple, list[dict]] = {}
    for r in rows:
        groups.setdefault((r.get("tier") or "-", r.get("task") or "-"), []).append(r)
    print("| 任务 | 成功率 | 总耗时 | 总token | tok/s |")
    print("|---|---|---|---|---|")
    for (tier, task), rs in sorted(groups.items()):
        m = metrics(rs, accounting)
        rate = "-" if m["rate"] is None else f"{m['solved']}/{m['graded']} = {m['rate']*100:.0f}%"
        tps = "-" if m["tps"] is None else f"{m['tps']:,.0f}"
        print(f"| {task} | {rate} | {hm(m['wall_s'])} | {m['tok_total']:,} | {tps} |")
    t = metrics(rows, accounting)
    rate = "-" if t["rate"] is None else f"{t['solved']}/{t['graded']} = {t['rate']*100:.0f}%"
    tps = "-" if t["tps"] is None else f"{t['tps']:,.0f}"
    print(f"| **合计** | **{rate}** | **{hm(t['wall_s'])}** | **{t['tok_total']:,}** | **{tps}** |")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tier", default=None)
    ap.add_argument("--results", default=None)
    ap.add_argument("--harness", default=None)
    ap.add_argument("--model", default=None)
    ap.add_argument("--md", default=None, help="also write the block to this file")
    ap.add_argument("--by-combo", action="store_true",
                    help="comparison table: one row per (tier, harness, model)")
    ap.add_argument("--by-task", action="store_true",
                    help="four metrics per task + total")
    ap.add_argument("--all-sessions", action="store_true",
                    help="count subagent child sessions too (needs runner --session-accounting)")
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

    if a.by_task or a.by_combo:
        import contextlib
        import io

        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            if a.by_task:
                print_task_table(rows, "all" if a.all_sessions else "main")
            else:
                print_table(rows, "all" if a.all_sessions else "main")
        block = buf.getvalue().rstrip("\n")
        print(block)
        if a.md:
            with open(a.md, "w") as f:
                f.write(block + "\n")
            print(f"\n(written -> {a.md})")
        return 0

    m_main = metrics(rows, "main")
    m_all = metrics(rows, "all")
    m = m_all if m_all["has_all"] and m_all["tok_total"] > m_main["tok_total"] else m_main
    total_wall = m["wall_s"]
    scope = " / ".join(x for x in [a.tier or "all-tiers", a.harness, a.model] if x)
    rate = f"{m['solved']}/{m['graded']} = {100.0*m['rate']:.0f}%" if m["rate"] is not None else "-"
    lines = [
        f"📊 四指标汇总 — {scope}",
        f"🏆 成功率   {rate}",
        f"⏱️ 总耗时   {hm(total_wall)}（{m['cells']} 格，均 {total_wall/max(m['cells'],1):.0f}s/格）",
    ]
    if m is m_all:
        lines += [
            f"🪙 总 token {m_all['tok_total']:,}（全量：主 session {m_main['tok_total']:,} + 子 agent {m_all['sub_tok']:,}；"
            f"in {m_all['tok_in']:,} / out {m_all['tok_out']:,}"
            + (f" / cache {m_all['tok_cache']:,}" if m_all["tok_cache"] else "")
            + "）",
            f"🔎 子 agent {m_all['sub_sessions']} 个子 session，{m_all['cells_with_sub']}/{m['cells']} 格发生委派",
            f"🧮 主 session 口径 {m_main['tok_total']:,}（in {m_main['tok_in']:,} / out {m_main['tok_out']:,}"
            + (f" / cache {m_main['tok_cache']:,}" if m_main["tok_cache"] else "")
            + "；与旧记录同口径）",
            f"⚡ 速度     {m_all['tps']:,.0f} tok/s（全量 token ÷ 智能体墙钟）；主 session 口径 {m_main['tps']:,.0f} tok/s",
        ]
    else:
        lines += [
            f"🪙 总 token {m['tok_total']:,}（in {m['tok_in']:,} / out {m['tok_out']:,}"
            + (f" / cache {m['tok_cache']:,}" if m["tok_cache"] else "")
            + "）",
            f"⚡ 速度     {m['tps']:,.0f} tok/s（token 总量 ÷ 智能体墙钟）" if m["tps"] else "⚡ 速度     -",
        ]
    if m["missing_tok"]:
        lines.append(f"⚠️ {m['missing_tok']} 格缺 token 记录（未计入总量/速度）")
    block = "\n".join(lines)
    print(block)
    if a.md:
        with open(a.md, "w") as f:
            f.write(block + "\n")
        print(f"\n(written -> {a.md})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
