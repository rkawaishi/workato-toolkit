#!/bin/bash
# Pre-push validation hook
# 1. Environment guard: refuses `workato push` / `workato recipes start|stop`
#    unless the resolved profile is a -dev profile (the deterministic layer
#    under the workato-deployment-flow rule — promotion goes via Deploy).
# 2. Validates JSON syntax and checks for common issues before workato push.

INPUT=$(cat)

# Fast exit: skip unless a guarded workato command (avoids python3 overhead)
case "$INPUT" in
  *"workato push"*|*"workato recipes start"*|*"workato recipes stop"*) ;;
  *) exit 0 ;;
esac

# Use CLAUDE_PROJECT_DIR (set by Claude Code) or fall back to pwd
CWD="${CLAUDE_PROJECT_DIR:-$(pwd)}"

# Extract command to find cd target (e.g., cd "projects/[App] Foo" && workato push)
COMMAND=$(echo "$INPUT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('tool_input',{}).get('command',''))" 2>/dev/null)

# Detect project directory from command or current active project
PROJECT_DIR=""

# 1. Check if command contains cd to a project directory
CD_TARGET=$(echo "$COMMAND" | python3 -c "
import sys, re
cmd = sys.stdin.read()
m = re.search(r'cd\s+[\"\\x27](.*?)[\"\\x27]\s*&&', cmd) or re.search(r'cd\s+(\S+)\s*&&', cmd)
print(m.group(1) if m else '')
")

if [ -n "$CD_TARGET" ] && [ -f "$CD_TARGET/.workatoenv" ]; then
  PROJECT_DIR="$CD_TARGET"
elif [ -n "$CD_TARGET" ] && [ -f "$CWD/$CD_TARGET/.workatoenv" ]; then
  PROJECT_DIR="$CWD/$CD_TARGET"
fi

# 2. Fall back to finding the active project via workato CLI state
if [ -z "$PROJECT_DIR" ]; then
  # Check each project for .workatoenv and find the one matching current CLI state
  for env_file in "$CWD"/projects/*/.workatoenv; do
    if [ -f "$env_file" ]; then
      PROJECT_DIR="$(dirname "$env_file")"
      break
    fi
  done
fi

# --- Environment guard (runs even when no project dir was found) ---
# Resolution mirrors the helper's resolve_profile():
#   --profile flag > .workatoenv workspace_id match > current_profile.
# Fails open only when no profiles file exists (the CLI can't run either).
VERDICT=$(COMMAND="$COMMAND" PROJECT_DIR="$PROJECT_DIR" python3 <<'PY'
import json, os, re, sys
from pathlib import Path

cmd = os.environ.get("COMMAND", "")
if not re.search(r"\bworkato\s+(push\b|recipes\s+(start|stop)\b)", cmd):
    print("SKIP")
    sys.exit(0)

try:
    data = json.loads((Path.home() / ".workato" / "profiles").read_text(encoding="utf-8"))
    profiles = data.get("profiles") or {}
except Exception:
    data, profiles = {}, {}
if not profiles:
    print("ALLOW")  # no profiles configured — the CLI itself cannot push
    sys.exit(0)

name = None
m = re.search(r"--profile[=\s]+['\"]?([\w.-]+)", cmd)
if m:
    name = m.group(1)

if name is None:
    proj = os.environ.get("PROJECT_DIR", "")
    envfile = Path(proj) / ".workatoenv" if proj else None
    if envfile and envfile.is_file():
        try:
            ws = json.loads(envfile.read_text(encoding="utf-8")).get("workspace_id")
        except Exception:
            ws = None
        if ws is not None:
            for pname, prof in profiles.items():
                if prof.get("workspace_id") is not None and str(prof["workspace_id"]) == str(ws):
                    name = pname
                    break

if name is None:
    current = data.get("current_profile", "")
    name = current if current in profiles else next(iter(profiles))

if name.endswith("-dev"):
    print("ALLOW")
else:
    print(f"BLOCK {name}")
PY
)

case "$VERDICT" in
  BLOCK*)
    BLOCKED_PROFILE="${VERDICT#BLOCK }"
    {
      echo "Blocked by the workato deployment-flow guard: resolved profile"
      echo "  '$BLOCKED_PROFILE' is not a dev profile (name must end in '-dev')."
      echo "Direct push / recipe start / recipe stop against test or prod is"
      echo "forbidden — promote through the Deploy feature (/deploy-project)."
      echo "Switch to your '<org>-dev' profile, or rename your dev profile to"
      echo "follow the '<org>-dev' convention. This guard has no override."
    } >&2
    exit 2
    ;;
esac

# recipes start/stop only needed the environment guard — no JSON validation.
case "$COMMAND" in
  *"workato push"*) ;;
  *) exit 0 ;;
esac

if [ -z "$PROJECT_DIR" ] || [ ! -d "$PROJECT_DIR" ]; then
  exit 0  # Can't determine project, allow push
fi

ERRORS=()
ERROR_DETAILS=()
WARNINGS=()

# 1. Validate JSON syntax (blocking)
while IFS= read -r -d '' file; do
  if ! VALIDATE_FILE="$file" python3 -c "import json,os; json.load(open(os.environ['VALIDATE_FILE']))" 2>/dev/null; then
    ERRORS+=("JSON syntax error: $(basename "$file")")
  fi
done < <(find "$PROJECT_DIR" -type f \( -name "*.recipe.json" -o -name "*.lcap_app.json" -o -name "*.lcap_page.json" -o -name "*.workato_db_table.json" -o -name "*.agentic_skill.json" -o -name "*.agentic_genie.json" -o -name "*.mcp_server.json" -o -name "*.connection.json" \) -print0 2>/dev/null)

# 2. Check for missing extended_output_schema on triggers (warning only)
while IFS= read -r -d '' file; do
  HAS_EOS=$(VALIDATE_FILE="$file" python3 -c "
import json,os
with open(os.environ['VALIDATE_FILE']) as f:
    d = json.load(f)
print('yes' if d.get('code',{}).get('extended_output_schema') else 'no')
" 2>/dev/null)
  if [ "$HAS_EOS" = "no" ]; then
    WARNINGS+=("Missing extended_output_schema on trigger: $(basename "$file")")
  fi
done < <(find "$PROJECT_DIR" -type f -name "*.recipe.json" -print0 2>/dev/null)

# 3. Check for dropdown with null dataSource in pages (warning only)
while IFS= read -r -d '' file; do
  NULL_DS=$(VALIDATE_FILE="$file" python3 -c "
import json,os
def find_dropdowns(obj):
    if isinstance(obj, dict):
        if obj.get('type') == 'dropdown' and obj.get('dataSource') is None:
            print(obj.get('name', 'unknown'))
        for v in obj.values():
            find_dropdowns(v)
    elif isinstance(obj, list):
        for item in obj:
            find_dropdowns(item)
with open(os.environ['VALIDATE_FILE']) as f:
    find_dropdowns(json.load(f))
" 2>/dev/null)
  if [ -n "$NULL_DS" ]; then
    while IFS= read -r name; do
      WARNINGS+=("Dropdown \"$name\" has null dataSource (value won't be saved): $(basename "$file")")
    done <<< "$NULL_DS"
  fi
done < <(find "$PROJECT_DIR" -type f -name "*.lcap_page.json" -print0 2>/dev/null)

# 4. Run `workato recipes validate` per recipe (blocking, ~2s/file, with noise filter)
if command -v workato >/dev/null 2>&1; then
  RECIPE_FILES=()
  while IFS= read -r -d '' file; do
    # Skip files that already failed syntax check (exact match on the known
    # error message produced by step 1 to avoid basename substring collisions
    # like "broken.recipe.json" vs "really-broken.recipe.json").
    base=$(basename "$file")
    skip=0
    for err in "${ERRORS[@]}"; do
      [ "$err" = "JSON syntax error: $base" ] && skip=1 && break
    done
    [ $skip -eq 0 ] && RECIPE_FILES+=("$file")
  done < <(find "$PROJECT_DIR" -type f -name "*.recipe.json" -print0 2>/dev/null)

  if [ ${#RECIPE_FILES[@]} -gt 0 ]; then
    echo "" >&2
    echo "Running 'workato recipes validate' on ${#RECIPE_FILES[@]} recipe(s) (~2s each)..." >&2

    NOISE_COUNT=0
    for file in "${RECIPE_FILES[@]}"; do
      base=$(basename "$file")
      rel=$(VALIDATE_FILE="$file" VALIDATE_ROOT="$PROJECT_DIR" python3 -c "import os; print(os.path.relpath(os.environ['VALIDATE_FILE'], os.environ['VALIDATE_ROOT']))" 2>/dev/null)
      [ -z "$rel" ] && rel="$file"

      raw=$(cd "$PROJECT_DIR" && workato recipes validate --path "$rel" < /dev/null 2>&1)
      clean=$(printf '%s' "$raw" | tr '\r' '\n' | sed 's/\x1b\[[0-9;]*[a-zA-Z]//g' | grep -v "^[[:space:]]*$" | grep -v "^[[:space:]]*⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏" | grep -Ev "Validating recipe:.*\([0-9.]+s\)")

      # Explicit success marker — anything else needs classification below.
      if printf '%s' "$clean" | grep -qE "Validation passed|✅"; then
        continue
      fi

      if printf '%s' "$clean" | grep -q "Validation failed"; then
        # Noise filter: workspace-level pre-check fails when any custom connector
        # in the workspace has `latest_released_version = null` (not yet released).
        # This short-circuits recipe-level validation regardless of the recipe's own
        # contents, so we can't extract real format errors. Aggregate into a single
        # warning rather than spamming one per recipe.
        if printf '%s' "$clean" | grep -q "CustomConnector" && printf '%s' "$clean" | grep -q "latest_released_version"; then
          NOISE_COUNT=$((NOISE_COUNT + 1))
          continue
        fi
        ERRORS+=("CLI validation failed: $base")
        ERROR_DETAILS+=("$clean")
        continue
      fi

      # Unexpected output — neither pass nor fail marker. Likely auth/network
      # failure, CLI version change, or empty output. Surface as a warning so
      # the user can investigate instead of silently treating as success.
      snippet=$(printf '%s' "$clean" | tr '\n' ' ' | tail -c 200)
      WARNINGS+=("CLI validate inconclusive for $base (no pass/fail marker). Tail: ${snippet:-<empty>}")
    done

    if [ $NOISE_COUNT -gt 0 ]; then
      WARNINGS+=("CLI validate skipped for $NOISE_COUNT recipe(s): workspace has unreleased custom connector(s). Release with 'workato sdk push' to enable deeper validation.")
    fi
  fi
fi

# Show warnings (non-blocking)
if [ ${#WARNINGS[@]} -gt 0 ]; then
  echo "" >&2
  echo "=== Pre-push warnings ===" >&2
  for warn in "${WARNINGS[@]}"; do
    echo "  ⚠️  $warn" >&2
  done
fi

# Block on errors
if [ ${#ERRORS[@]} -gt 0 ]; then
  echo "" >&2
  echo "=== Pre-push validation FAILED ===" >&2
  for i in "${!ERRORS[@]}"; do
    echo "  ❌ ${ERRORS[$i]}" >&2
    if [ -n "${ERROR_DETAILS[$i]:-}" ]; then
      printf '%s\n' "${ERROR_DETAILS[$i]}" | sed 's/^/      /' >&2
    fi
  done
  echo "" >&2
  echo "Fix errors above before pushing." >&2
  exit 2
fi

exit 0
