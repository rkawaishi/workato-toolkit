#!/bin/bash
# PostToolUse hook: after sdk push, remind AI to sync connector docs
#
# Claude Code: tool_name="Bash", tool_response={exitCode,stdout,stderr}.
# (The tool_output branch below parses the frozen Cursor variant's format —
#  kept for a future revival, not verified.)
#
# When `sdk push` completes successfully, this hook detects the connector path
# from the command and outputs a message to update connectors/docs/.

INPUT=$(cat)

# Fast exit: skip if not an sdk push command (any invocation route)
case "$INPUT" in
  *"sdk push"*|*"bundle exec workato push"*) ;;
  *) exit 0 ;;
esac

# Parse tool input and check exit code (handles both Claude Code and Cursor formats)
RESULT=$(echo "$INPUT" | python3 -c "
import sys, json, re

data = json.load(sys.stdin)
command = data.get('tool_input', {}).get('command', '')

# Verify it's an sdk push command — helper-mediated or the raw Platform CLI
# form. (The SDK gem's 'bundle exec workato push' runs inside the connector
# dir with no --connector arg; it gets the generic fallback below.)
if ('workato-api.py sdk push' not in command
        and not re.search(r'\bworkato\s+sdk\s+push\b', command)
        and not re.search(r'\bbundle\s+exec\s+workato\s+push\b', command)):
    sys.exit(0)

# Get exit code: Claude Code uses tool_response (dict), Cursor uses tool_output (JSON string)
exit_code = 1
resp = data.get('tool_response')
if isinstance(resp, dict):
    exit_code = resp.get('exitCode', 1)
else:
    raw = data.get('tool_output', '')
    if isinstance(raw, str) and raw:
        try:
            exit_code = json.loads(raw).get('exitCode', 1)
        except (json.JSONDecodeError, AttributeError):
            pass

if exit_code != 0:
    sys.exit(0)

# Extract connector path from --connector argument (supports both --connector path and --connector=path)
q = chr(39)  # single quote (avoids bash escaping issues)
m = re.search(r'--connector[\s=]+[\"' + q + r'](.*?)[\"' + q + r']', command) or re.search(r'--connector[\s=]+(\S+)', command)
if not m:
    print('__GENERIC__')  # sdk push without --connector (e.g. bundle exec form)
    sys.exit(0)

from pathlib import Path
p = Path(m.group(1))
name = p.parent.name if p.name == 'connector.rb' else p.stem
print(name)
" 2>/dev/null)

if [ -z "$RESULT" ]; then
  exit 0
fi

# Output feedback (stdout is shown to the AI as hook feedback)
if [ "$RESULT" = "__GENERIC__" ]; then
  echo "sdk push completed. Please update the connector's docs: read its connector.rb and generate/update connectors/docs/<name>.md following the custom connector doc format defined in the /sync-connectors skill."
else
  CONNECTOR_NAME="$RESULT"
  echo "sdk push completed. Please update connector docs: read connectors/${CONNECTOR_NAME}/connector.rb and generate/update connectors/docs/${CONNECTOR_NAME}.md following the custom connector doc format defined in the /sync-connectors skill."
fi

exit 0
