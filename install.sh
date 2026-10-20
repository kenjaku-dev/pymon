#!/usr/bin/env bash
# install.sh — install or update pymon
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="${PYMON_VENV:-$HOME/.local/share/pymon/venv}"
BIN_DIR="${PYMON_BIN:-$HOME/.local/bin}"

log() { printf '[pymon] %s\n' "$*"; }
die() { printf '[pymon] ERROR: %s\n' "$*" >&2; exit 1; }

MODE="${1:-install}"
case "$MODE" in
  install|update) ;;
  *) echo "Usage: $0 [install|update]"; exit 2 ;;
esac

# Prefer a Python >= 3.12 when available.
PYTHON=""
for cand in python3.13 python3.12 python3; do
  if command -v "$cand" >/dev/null 2>&1; then
    PYTHON="$(command -v "$cand")"
    break
  fi
done
[ -n "$PYTHON" ] || die "python3 not found"
command -v "$PYTHON" >/dev/null 2>&1 || die "python3 not found"

PY_VER="$("$PYTHON" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
PY_MAJOR="$("$PYTHON" -c 'import sys; print(sys.version_info.major)')"
PY_MINOR="$("$PYTHON" -c 'import sys; print(sys.version_info.minor)')"
if [ "$PY_MAJOR" -lt 3 ] || { [ "$PY_MAJOR" -eq 3 ] && [ "$PY_MINOR" -lt 12 ]; }; then
  die "Python 3.12+ required (found $PY_VER)"
fi

log "Using Python: $PYTHON ($PY_VER)"

# Update mode: fast-forward the source tree when possible.
if [ "$MODE" = "update" ] && [ -d "$SCRIPT_DIR/.git" ]; then
  if command -v git >/dev/null 2>&1; then
    log "Updating source tree"
    git -C "$SCRIPT_DIR" pull --ff-only || log "git pull failed; continuing with current tree"
  fi
fi

# Create venv if missing.
if [ ! -x "$VENV_DIR/bin/python" ]; then
  log "Creating virtual environment at $VENV_DIR"
  "$PYTHON" -m venv "$VENV_DIR"
fi

PIP="$VENV_DIR/bin/pip"
PY="$VENV_DIR/bin/python"

# Upgrade pip only when requested (faster default installs).
if [ "${PYMON_UPGRADE_PIP:-0}" = "1" ]; then
  log "Upgrading pip"
  "$PIP" install --disable-pip-version-check --upgrade pip >/dev/null
fi

# Build the install spec, including optional extras.
EXTRAS=""
case "${PYMON_GPU:-0}" in
  1|nvidia) EXTRAS="gpu" ;;
  amd) EXTRAS="gpu-amd" ;;
  *) EXTRAS="" ;;
esac
if [ "${PYMON_DEV:-0}" = "1" ]; then
  if [ -n "$EXTRAS" ]; then
    EXTRAS="$EXTRAS,dev"
  else
    EXTRAS="dev"
  fi
fi

SPEC="$SCRIPT_DIR"
if [ -n "$EXTRAS" ]; then
  SPEC="$SCRIPT_DIR[$EXTRAS]"
fi

log "Installing/updating pymon ($MODE)"
"$PIP" install --disable-pip-version-check --upgrade -e "$SPEC"

# Symlink into PATH.
mkdir -p "$BIN_DIR"
ln -sf "$VENV_DIR/bin/pymon" "$BIN_DIR/pymon"
log "Symlinked $BIN_DIR/pymon -> $VENV_DIR/bin/pymon"

# Ensure config/runtime dirs exist.
mkdir -p "$HOME/.config/sysmon" "$HOME/.local/share/pymon"

log "Done. Run: pymon   (ensure $BIN_DIR is on your PATH)"
"$PY" -m pymon --version