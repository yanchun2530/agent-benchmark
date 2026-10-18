#!/usr/bin/env bash
# One-time setup / doctor for the agent benchmark package.
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "== agent_benchmark setup =="
echo "root: $ROOT"
echo

mkdir -p "$ROOT/work" "$ROOT/results" "$ROOT/data/swe-mini"

echo "-- toolchain --"
for c in git docker python3 curl; do
  printf '%-10s %s\n' "$c" "$(command -v "$c" || echo 'MISSING')"
done

oc="$(command -v opencode || true)"
if [[ -z "$oc" ]]; then
  oc="$(ls -t "$HOME"/.opencode/desktop-ssh/*/opencode 2>/dev/null | head -1 || true)"
fi
printf '%-10s %s\n' "opencode" "${oc:-MISSING (set OPENCODE_BIN)}"
printf '%-10s %s\n' "codex" "$(command -v codex || echo 'MISSING')"

echo
echo "-- disk --"
df -h "$ROOT" | tail -1

echo
echo "-- tasks --"
if [[ -d "$ROOT/tasks/low" && -d "$ROOT/tasks/mid" ]]; then
  find "$ROOT/tasks" -maxdepth 2 -mindepth 2 -type d | sort | sed "s|$ROOT/||"
else
  echo "fetching vendored tasks from openbench (MIT) ..."
  python3 "$ROOT/bin/fetch_tasks.py"
fi

echo
echo "-- python3 --"
python3 --version

cat <<'EOF'

Next steps:
  bash bench.sh selftest                       # zero-cost pipeline validation
  bash bench.sh low  --harness opencode --model <provider/model>
  bash bench.sh mid  --harness opencode --model <provider/model>
  bash bench.sh high fetch --n 5               # then: high run / high eval (needs docker)
  bash bench.sh report
EOF
