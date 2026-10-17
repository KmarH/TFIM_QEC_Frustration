#!/usr/bin/env bash
# One-command setup: builds the two virtual environments this project needs.
#   .venv     main environment   (requirements.txt)     -> everything except the H2 local emulator
#   .venv-le  emulator environment (requirements-le.txt) -> H2 local emulator (pytket-quantinuum[pecos]);
#             it cannot share an environment with selene-sim 0.3.x (docs/quantinuum_issues.md, QI-1)
# Idempotent: an existing environment is left alone. Needs Python 3.12 (or `uv`, which can fetch it).
#   bash scripts/setup_env.sh
set -eu
cd "$(dirname "$0")/.."
PY="${PYTHON:-$(command -v python3.12 || true)}"
if command -v uv >/dev/null 2>&1; then
  mk() { [ -x "$1/bin/python" ] || { uv venv --python "${PY:-3.12}" "$1" -q && uv pip install --python "$1/bin/python" -r "$2" -q; }; }
elif [ -n "$PY" ]; then
  mk() { [ -x "$1/bin/python" ] || { "$PY" -m venv "$1" && "$1/bin/pip" install -q -r "$2"; }; }
else
  echo "Python 3.12 not found. Install python3.12 (or uv: https://docs.astral.sh/uv/) and rerun, or set PYTHON=/path/to/python3.12" >&2
  exit 1
fi
echo "== building .venv (main) ==";  mk .venv requirements.txt
echo "== building .venv-le (H2 local emulator) =="; mk .venv-le requirements-le.txt
echo
echo "Done. Next:"
echo "  .venv/bin/python -m pytest tests/ -q                      # main suite"
echo "  .venv-le/bin/python -m pytest tests/test_h2_*.py -q       # H2 emulator tests"
echo "  .venv/bin/python -I scripts/run_h2_nexus.py --group bare-2x2-step1   # dry run, sends nothing"
