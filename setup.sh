#!/usr/bin/env bash
# ESP-FC one-command setup (Linux / macOS).
#   curl -fsSL https://raw.githubusercontent.com/MahediIslamNadim/esp32/main/setup.sh | bash
# or, from a cloned repo:
#   ./setup.sh
set -e

# Resolve the directory this script lives in (works when piped or executed).
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" 2>/dev/null && pwd || pwd)"

# If run via curl|bash (no local repo), clone it first.
if [ ! -f "$SCRIPT_DIR/platformio.ini" ]; then
  echo "• Cloning ESP-FC..."
  command -v git >/dev/null 2>&1 || { echo "✗ git is required"; exit 1; }
  git clone https://github.com/MahediIslamNadim/esp32.git
  SCRIPT_DIR="$(pwd)/esp32"
fi

# Find Python 3.
PY=""
for c in python3 python; do
  if command -v "$c" >/dev/null 2>&1; then PY="$c"; break; fi
done
[ -z "$PY" ] && { echo "✗ Python 3 is required. Install it and re-run."; exit 1; }

cd "$SCRIPT_DIR"
exec "$PY" tools/espfc-setup.py "$@"
