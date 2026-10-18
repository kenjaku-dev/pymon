#!/usr/bin/env bash
# install.sh — install or update pymon
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="${PYMON_VENV:-$HOME/.local/share/pymon/venv}"
BIN_DIR="${PYMON_BIN:-$HOME/.local/bin}"

log() { printf '[pymon] %s\n' "$*"; }
die() { printf '[pymon] ERROR: %s\n' "$*" >&2; exit 1; }

command -v python3 >/dev/null 2>&1 || die "python3 not found"

# Resolve python version (prefer 3.12+)
PYTHON="$(command -v python3)"

MODE="${1:-install}"
case "$MODE" in
  install|update) ;;
  *) echo "Usage: $0 [install|update]"; exit 2 ;;
esac

log "Using Python: $PYTHON ($($PYTHON --version))"

# Create venv if missing
if [ ! -x "$VENV_DIR/bin/python" ]; then
  log "Creating virtual environment at $VENV_DIR"
  "$PYTHON" -m venv "$VENV_DIR"
fi

PIP="$VENV_DIR/bin/pip"
PY="$VENV_DIR/bin/python"

log "Upgrading pip"
"$PIP" install --upgrade pip >/dev/null

log "Installing/updating dependencies"
"$PIP" install --upgrade psutil textual

# Optional GPU support
if [ "${PYMON_GPU:-0}" = "1" ]; then
  log "Installing optional GPU support (nvidia-ml-py)"
  "$PIP" install --upgrade "nvidia-ml-py>=12.0" || log "GPU support install failed (optional)"
fi

log "Installing pymon (editable)"
"$PIP" install --upgrade -e "$SCRIPT_DIR"

# Dev tools (optional)
if [ "${PYMON_DEV:-0}" = "1" ]; then
  log "Installing dev tools (pytest, ruff, pyright)"
  "$PIP" install --upgrade pytest ruff pyright
fi

# Symlink into PATH
mkdir -p "$BIN_DIR"
ln -sf "$VENV_DIR/bin/pymon" "$BIN_DIR/pymon"
log "Symlinked $BIN_DIR/pymon -> $VENV_DIR/bin/pymon"

# Ensure config dir exists
mkdir -p "$HOME/.config/sysmon"
mkdir -p "$HOME/.local/share/pymon"

log "Done. Run: pymon   (ensure $BIN_DIR is on your PATH)"
"$PY" -m pymon --version