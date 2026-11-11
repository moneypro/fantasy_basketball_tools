#!/usr/bin/env bash
set -euo pipefail
fantasy_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd -- "$fantasy_root"
if [[ ! -x .venv-mcp/bin/python ]]; then
  echo 'Run: python3 -m venv .venv-mcp && .venv-mcp/bin/python -m pip install -r requirements-mcp.txt' >&2
  exit 1
fi
exec .venv-mcp/bin/python -m fantasy_mcp.server
