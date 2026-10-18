#!/usr/bin/env python3
"""Aggregate benchmark results (results/*.jsonl) into a compact table.

Usage:
  python3 bin/report.py                       # all tiers in results/
  python3 bin/report.py --tier low --results results/low.jsonl
  python3 bin/report.py --by-task
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import statistics as st

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
                if line:
                    try:
                        rows.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
    return [r for r in rows if r.get("harness") not in ("dry-none", "dry-solution")]


def agg(rows: list[dict]) -> dict:
    graded = [r for r in rows if r.get("solved") is not None]
    solved = [r for r in graded if r.get("solved")]
    walls = [r["agent_wall_s"] for r in rows if r.get("agent_wall_s")]
    toks = [r["tokens_total"] for r in rows if r.get("tokens_total")]
    costs = [r["cost_usd"] for r in rows if r.get("cost_usd") is not None]
    out = {
        "n": len(rows),
        "graded": len(graded),
        "solved": len(solved),
        "rate": (len(solved) / len(graded)) if graded else None,
        "wall_mean": st.mean(walls) if walls else None,
        "wall_p50": st.median(walls) if walls else None,
        "wall_max": max(walls) if walls else None,
        "tok_per_solve": (sum(toks) / len(solved)) if (toks and solved) else None,
        "usd_per_solve": (sum(costs) / len(solved)) if (costs and solved) else None,
    }
    return out


def fmt(v, nd=1, suffix=""):
    return "-" if v is None else f"{v:.{nd}f}{suffix}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tier", default=None)
    ap.add_argument("--results", default=None)
    ap.add_argument("--by-task", action="store_true")
    a = ap.parse_args()

    if a.results:
        paths = [a.results]
    elif a.tier:
        paths = [os.path.join(RESULTS_DIR, f"{a.tier}.jsonl")]
    else:
        paths = sorted(glob.glob(os.path.join(RESULTS_DIR, "*.jsonl")))

    rows = load(paths)
    if not rows:
        print("no results yet — run: bash bench.sh low --harness opencode --model <m>")
        return 1

    groups: dict[tuple, list[dict]] = {}
    for r in rows:
        groups.setdefault(
            (r.get("tier") or "-", r.get("harness") or "-", r.get("model") or "-"), []
        ).append(r)

    print("| tier | harness | model | cells | graded | solved | rate | wall mean | wall p50 | tok/solve | $/solve |")
    print("|---|---|---|---|---|---|---|---|---|---|---|")
    for (tier, harness, model), rs in sorted(groups.items()):
        s = agg(rs)
        rate = "-" if s["rate"] is None else f"{s['rate']*100:.0f}%"
        print(
            f"| {tier} | {harness} | {model} | {s['n']} | {s['graded']} | {s['solved']} | {rate} "
            f"| {fmt(s['wall_mean'],0,'s')} | {fmt(s['wall_p50'],0,'s')} | {fmt(s['tok_per_solve'],0)} "
            f"| {fmt(s['usd_per_solve'],3)} |"
        )

    if a.by_task:
        print()
        print("| tier | task | cells | graded | solved | rate | wall mean |")
        print("|---|---|---|---|---|---|---|")
        tgroups: dict[tuple, list[dict]] = {}
        for r in rows:
            tgroups.setdefault((r.get("tier") or "-", r.get("task") or "-"), []).append(r)
        for (tier, task), rs in sorted(tgroups.items()):
            s = agg(rs)
            rate = "-" if s["rate"] is None else f"{s['rate']*100:.0f}%"
            print(f"| {tier} | {task} | {s['n']} | {s['graded']} | {s['solved']} | {rate} | {fmt(s['wall_mean'],0,'s')} |")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
