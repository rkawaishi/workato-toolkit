#!/bin/bash
# self-install-smoke.sh — semi-automated self-install smoke for the plugin.
#
# Runs everything that can be checked without an interactive Claude Code
# session, then prints the short manual checklist for the rest (issue #32
# Phase A). Record results in dev/verifications/YYYY-MM-DD-<topic>.md.
#
# Usage: bash scripts/self-install-smoke.sh
set -u

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT" || exit 1

PASS=0
FAIL=0
report() { # report <label> <exit-code>
  if [ "$2" -eq 0 ]; then
    echo "  PASS  $1"; PASS=$((PASS + 1))
  else
    echo "  FAIL  $1"; FAIL=$((FAIL + 1))
  fi
}

echo "== 1. Structural preflight (no editor needed) =="

python3 - <<'PY' >/dev/null 2>&1
import json
json.load(open('plugin/.claude-plugin/plugin.json'))
m = json.load(open('.claude-plugin/marketplace.json'))
assert any(p.get('source') == './plugin' for p in m['plugins'])
PY
report "manifests parse; marketplace points at ./plugin" $?

python3 - <<'PY' >/dev/null 2>&1
import json, os, re
blob = json.dumps(json.load(open('plugin/hooks/hooks.json')))
rels = re.findall(r'\$\{CLAUDE_PLUGIN_ROOT\}/([^"\s]+)', blob)
assert rels, "no hook script references found"
for rel in rels:
    path = os.path.join('plugin', rel)
    assert os.path.isfile(path), path
    assert os.access(path, os.X_OK), path + " not executable"
PY
report "hooks.json references only existing executable scripts" $?

echo '{}' | CLAUDE_PLUGIN_ROOT="$REPO_ROOT/plugin" \
  bash plugin/bin/session-start-rules 2>/dev/null | grep -q additionalContext
report "session-start-rules emits rule context" $?

echo '{"tool_name":"Bash","tool_input":{"command":"cat master.key"}}' \
  | bash plugin/bin/block-credential-read.sh >/dev/null 2>&1
[ $? -eq 2 ]; report "credential guard blocks cat master.key (exit 2)" $?

if command -v uv >/dev/null 2>&1; then
  # --no-project mirrors the .mcp.json launch: without it, uv tries to adopt
  # whatever pyproject.toml it finds in the cwd (repo or user workspace) and
  # fails or syncs the wrong environment.
  timeout 120 uv run --no-project --with fastmcp python - <<'PY' >/dev/null 2>&1
import sys
sys.path.insert(0, 'plugin/mcp/docs-overlay')
import assets, overlay, server  # noqa: F401
PY
  report "docs-overlay MCP server imports (uv + fastmcp)" $?
else
  echo "  SKIP  docs-overlay MCP import (uv not installed)"
fi

echo ""
echo "== 2. Claude Code CLI install cycle =="
if command -v claude >/dev/null 2>&1; then
  claude plugin marketplace add "$REPO_ROOT" >/dev/null 2>&1
  report "claude plugin marketplace add (local path)" $?
  claude plugin install workato-toolkit@workato-toolkit >/dev/null 2>&1
  report "claude plugin install workato-toolkit@workato-toolkit" $?
  echo "  (cleanup: claude plugin uninstall workato-toolkit;"
  echo "            claude plugin marketplace remove workato-toolkit)"
else
  echo "  SKIP  claude CLI not on PATH — run this section on a machine with Claude Code"
fi

echo ""
echo "== 3. Manual checklist (interactive session; see issue #32 Phase A) =="
cat <<'CHECKLIST'
  [ ] /ping responds and reports the plugin root
  [ ] SessionStart injection: always-on Workato rules visible in context
  [ ] workato_docs_lookup("connectors/clearbit.md") returns kit content
  [ ] a skill's allowed-tools does not block the MCP tools (record which)
  [ ] credential guard fires inside the session (ask to cat master.key)
  [ ] workato-builder subagent can see rules / generation refs (issue #22)
  -> record results in dev/verifications/YYYY-MM-DD-<topic>.md
CHECKLIST

echo ""
echo "== Summary: $PASS passed, $FAIL failed =="
[ "$FAIL" -eq 0 ]
