#!/usr/bin/env bash
# Agent benchmark entry point.
#   bash bench.sh selftest [-v]                        # validate pipeline, zero LLM cost
#   bash bench.sh low   --harness opencode --model M [--trials 3]
#   bash bench.sh mid   --harness opencode --model M [--trials 1]
#   bash bench.sh matrix --tier low --combos "opencode:m1,codex:m2" --trials 3   # 多模型/harness 对比
#   bash bench.sh high  fetch|run|eval [--n 5 ...]     # SWE-bench Verified mini
#   bash bench.sh speed --base-url ... --model ...     # TTFT / TPOT / tok-s
#   bash bench.sh summary [--tier low] [--by-combo]    # 四指标: 成功率/总耗时/总token/tok-s
#   bash bench.sh compare --tier low                   # 四指标对比表（按模型×harness）
#   bash bench.sh report [--tier low] [--results path]
#   bash bench.sh clean
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cmd="${1:-help}"
[[ $# -gt 0 ]] && shift

case "$cmd" in
  low|mid)  exec python3 "$ROOT/bin/runner.py" --tier "$cmd" "$@" ;;
  matrix)   exec python3 "$ROOT/bin/matrix.py" "$@" ;;
  high)     exec python3 "$ROOT/bin/swe_mini.py" "$@" ;;
  speed)    exec python3 "$ROOT/bin/speed.py" "$@" ;;
  summary|4) exec python3 "$ROOT/bin/summary.py" "$@" ;;
  compare)  exec python3 "$ROOT/bin/summary.py" --by-combo "$@" ;;
  report)   exec python3 "$ROOT/bin/report.py" "$@" ;;
  selftest) exec python3 "$ROOT/bin/runner.py" --selftest "$@" ;;
  fetch)    exec python3 "$ROOT/bin/fetch_tasks.py" "$@" ;;
  clean)
    rm -rf "$ROOT/work"
    echo "cleaned $ROOT/work"
    ;;
  help|*)
    sed -n '2,14p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
    ;;
esac
