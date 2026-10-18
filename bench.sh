#!/usr/bin/env bash
# Agent benchmark entry point.
#   bash bench.sh selftest [-v]                        # validate pipeline, zero LLM cost
#   bash bench.sh low   --harness opencode --model M [--trials 3]
#   bash bench.sh mid   --harness opencode --model M [--trials 1]
#   bash bench.sh high  fetch|run|eval [--n 5 ...]     # SWE-bench Verified mini
#   bash bench.sh speed --base-url ... --model ...     # TTFT / TPOT / tok-s
#   bash bench.sh summary [--tier low]                 # 四指标: 成功率/总耗时/总token/tok-s
#   bash bench.sh report [--tier low] [--results path]
#   bash bench.sh clean
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cmd="${1:-help}"
[[ $# -gt 0 ]] && shift

case "$cmd" in
  low|mid)  exec python3 "$ROOT/bin/runner.py" --tier "$cmd" "$@" ;;
  high)     exec python3 "$ROOT/bin/swe_mini.py" "$@" ;;
  speed)    exec python3 "$ROOT/bin/speed.py" "$@" ;;
  summary|4) exec python3 "$ROOT/bin/summary.py" "$@" ;;
  report)   exec python3 "$ROOT/bin/report.py" "$@" ;;
  selftest) exec python3 "$ROOT/bin/runner.py" --selftest "$@" ;;
  fetch)    exec python3 "$ROOT/bin/fetch_tasks.py" "$@" ;;
  clean)
    rm -rf "$ROOT/work"
    echo "cleaned $ROOT/work"
    ;;
  help|*)
    sed -n '2,12p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
    ;;
esac
