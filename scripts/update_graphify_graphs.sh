#!/usr/bin/env bash
set -euo pipefail

if ! command -v graphify >/dev/null 2>&1; then
  echo "graphify is not on PATH. Install it first or open a shell where ~/.local/bin is available." >&2
  exit 1
fi

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

if [[ "${1:-}" == "--clean" ]]; then
  rm -rf graphify-out Backend/graphify-out Frontend/nimrag-frontend/graphify-out
fi

graphify update .
graphify update Backend
graphify update Frontend/nimrag-frontend

"$repo_root/Backend/venv_py312/bin/python" "$repo_root/scripts/apply_graphify_labels.py"

printf '%s\n' \
  "Graphify reports refreshed:" \
  "  - graphify-out/GRAPH_REPORT.md" \
  "  - Backend/graphify-out/GRAPH_REPORT.md" \
  "  - Frontend/nimrag-frontend/graphify-out/GRAPH_REPORT.md"