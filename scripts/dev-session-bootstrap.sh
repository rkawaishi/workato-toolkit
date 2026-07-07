#!/bin/bash
# dev-session-bootstrap.sh — SessionStart hook for DEVELOPMENT sessions of
# this repository (wired in .claude/settings.json; end users never run this —
# the shipped plugin has its own hooks under plugin/).
#
# Makes a fresh session (e.g. Claude Code on the web) able to run
# `python3 -m pytest tests/ -q` immediately. Idempotent and fast: probes for
# pytest first and only then installs from requirements-dev.txt.

cat >/dev/null  # drain hook stdin (unused)

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

if ! python3 -c "import pytest" >/dev/null 2>&1; then
  if ! pip install -q -r "$REPO_ROOT/requirements-dev.txt" >&2; then
    echo "workato-toolkit dev bootstrap: pip install failed —" \
         "run: pip install -r requirements-dev.txt" >&2
  fi
fi

echo '{}'
exit 0
