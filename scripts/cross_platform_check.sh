#!/usr/bin/env bash
# Cross-platform check for the H2 path: builds .venv and .venv-le, runs both suites and the slow LE
# validation, and writes data/xplat_<hostname>.txt (platform, Python, pass/skip/fail counts, frozen
# hashes, timings). Idempotent. No network except pip; nothing touches Nexus or spends HQC.
#   bash scripts/cross_platform_check.sh            # needs python3.12 (or uv) and ~4 GB free
set -u
cd "$(dirname "$0")/.."
HOST="$(hostname -s)"
OUT="data/xplat_${HOST}.txt"
PY="${PYTHON:-$(command -v python3.12 || command -v python3)}"
mk() { # mk <dir> <requirements>
  [ -x "$1/bin/python" ] && return 0
  if command -v uv >/dev/null 2>&1; then uv venv --python "$PY" "$1" -q && uv pip install --python "$1/bin/python" -r "$2" -q
  else "$PY" -m venv "$1" && "$1/bin/pip" install -q -r "$2"; fi
}
mk .venv requirements.txt || { echo "building .venv failed"; exit 1; }
mk .venv-le requirements-le.txt || { echo "building .venv-le failed"; exit 1; }
{
  echo "# cross-platform check -- $(date '+%Y-%m-%d %H:%M') -- scripts/cross_platform_check.sh"
  echo "# host: $HOST  platform: $(uname -sm)  python: $(.venv/bin/python -V 2>&1)  cores: $(nproc 2>/dev/null || sysctl -n hw.ncpu)"
  echo "# commit: $(git rev-parse --short HEAD 2>/dev/null)   (classical/offline only; no Nexus, no HQC)"
  echo "# frozen test hashes (sha256):"
  sha256sum tests/test_h2_circuits.py tests/test_h2_backend.py tests/test_h2_driver.py tests/test_h2_hardening.py tests/test_h2_q3.py 2>/dev/null | sed 's/^/#   /'
  echo "# --- main suite (.venv) ---"
  t0=$(date +%s); .venv/bin/python -m pytest tests/ -q -p no:cacheprovider 2>&1 | tail -3; echo "# seconds: $(( $(date +%s) - t0 ))"
  echo "# --- H2 tests in .venv-le ---"
  t0=$(date +%s); .venv-le/bin/python -m pytest tests/test_h2_circuits.py tests/test_h2_backend.py tests/test_h2_hosted.py tests/test_h2_review_fixes.py tests/test_h2_driver.py tests/test_h2_hardening.py tests/test_h2_q3.py -q -p no:cacheprovider 2>&1 | tail -3; echo "# seconds: $(( $(date +%s) - t0 ))"
  echo "# --- slow LE validation (Steane, concatenated) ---"
  t0=$(date +%s); .venv-le/bin/python -I scripts/run_h2_le.py --slow --out "data/xplat_${HOST}_le_slow.txt" 2>&1 | tail -5; echo "# seconds: $(( $(date +%s) - t0 ))"
} 2>&1 | tee "$OUT"
echo "wrote $OUT -- commit/push it or paste it back"
