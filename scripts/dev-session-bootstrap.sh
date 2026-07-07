#!/bin/bash
# dev-session-bootstrap.sh — SessionStart hook for DEVELOPMENT sessions of
# this repository (wired in .claude/settings.json; end users never run this —
# the shipped plugin has its own hooks under plugin/).
#
# Makes a fresh session (e.g. Claude Code on the web) able to run
# `python3 -m pytest tests/ -q` immediately. Idempotent and fast: a stamp file
# keyed on the hash of requirements-dev.txt skips the install once that exact
# requirements set has been satisfied on this machine, and the install itself
# is bounded (--retries/--timeout) so an offline session is not blocked.

cat >/dev/null  # drain hook stdin (unused; hook harness closes the pipe)

ROOT="${CLAUDE_PROJECT_DIR:-}"
if [ -z "$ROOT" ]; then
  ROOT="$(cd "$(dirname "$0")/.." && pwd)"
fi
REQS="$ROOT/requirements-dev.txt"

if [ -f "$REQS" ]; then
  STAMP="${TMPDIR:-/tmp}/workato-toolkit-dev-reqs-$(cksum "$REQS" | cut -d' ' -f1)"
  if [ ! -f "$STAMP" ]; then
    # python3 -m pip binds the install to the same interpreter the tests use.
    if python3 -m pip install -q --disable-pip-version-check \
         --retries 1 --timeout 10 -r "$REQS" >&2; then
      touch "$STAMP"
    else
      echo "workato-toolkit dev bootstrap: dependency install failed —" \
           "run: python3 -m pip install -r requirements-dev.txt" >&2
    fi
  fi
fi

echo '{}'
exit 0
