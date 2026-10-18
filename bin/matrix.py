#!/usr/bin/env python3
"""Run one tier across MULTIPLE harness/model combos, then print the 4-metric
comparison table (成功率 / 总耗时 / 总token / tok-s).

Combos use `harness:model` syntax, comma-separated. Results from every combo
append to the same results/<tier>.jsonl, so the table (and
`bench.sh summary --tier <tier> --by-combo`) always compares like-for-like.

Usage:
  python3 bin/matrix.py --tier low --combos "opencode:opencode/glm-5.3-flash-free,opencode:opencode/deepseek-v4.1-flash-free" --trials 3
  python3 bin/matrix.py --tier low --combos "opencode:m,codex:gpt-5.5" --tasks make-ci-green --trials 1
  python3 bin/matrix.py --tier mid --combos "opencode:m" --timeout-min 30
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUNNER = os.path.join(ROOT, "bin", "runner.py")
SUMMARY = os.path.join(ROOT, "bin", "summary.py")


def parse_combos(spec: str) -> list[tuple[str, str]]:
    combos = []
    for item in spec.split(","):
        item = item.strip()
        if not item:
            continue
        if ":" not in item:
            raise SystemExit(f"bad combo '{item}' — expected harness:model")
        harness, model = item.split(":", 1)
        combos.append((harness.strip(), model.strip()))
    if not combos:
        raise SystemExit("no combos given")
    return combos


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tier", required=True, choices=["low", "mid"])
    ap.add_argument("--combos", required=True, help="harness:model[,harness:model...]")
    ap.add_argument("--trials", type=int, default=None)
    ap.add_argument("--tasks", default=None)
    ap.add_argument("--timeout-min", type=int, default=None)
    ap.add_argument("--results", default=None)
    ap.add_argument("--dry-run", action="store_true", help="print the run plan only")
    a = ap.parse_args()

    combos = parse_combos(a.combos)
    print(f"== matrix: tier={a.tier}, {len(combos)} combo(s) ==")
    for harness, model in combos:
        print(f"   · {harness} × {model}")

    if a.dry_run:
        return 0

    for harness, model in combos:
        cmd = [sys.executable, RUNNER, "--tier", a.tier, "--harness", harness, "--model", model]
        if a.trials:
            cmd += ["--trials", str(a.trials)]
        if a.tasks:
            cmd += ["--tasks", a.tasks]
        if a.timeout_min:
            cmd += ["--timeout-min", str(a.timeout_min)]
        if a.results:
            cmd += ["--results", a.results]
        print("\n" + "-" * 70)
        rc = subprocess.run(cmd).returncode
        if rc != 0:
            print(f"!! combo {harness}:{model} exited {rc}", file=sys.stderr)

    print("\n" + "=" * 70)
    print("四指标对比：")
    table_cmd = [sys.executable, SUMMARY, "--tier", a.tier, "--by-combo"]
    if a.results:
        table_cmd = [sys.executable, SUMMARY, "--results", a.results, "--by-combo"]
    subprocess.run(table_cmd)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
