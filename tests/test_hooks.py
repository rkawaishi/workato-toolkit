"""Hook guards: scripts under plugin/bin/, hooks.json wiring (CC + frozen
per-editor variants), and stdin-driven behavior checks (fixture matrix)."""
import json
import os
import shutil
import subprocess

import pytest

from conftest import BIN, HOOKS, PLUGIN


def _run_hook(script, payload, env=None):
    e = dict(os.environ)
    if env:
        e.update(env)
    return subprocess.run(
        ["bash", str(BIN / script)],
        input=json.dumps(payload), capture_output=True, text=True, env=e,
    )

PATTERNS = PLUGIN / "credential-patterns.txt"

EXPECTED_HOOKS = {
    "block-credential-read.sh",
    "validate-before-push.sh",
    "sync-docs-after-sdk-push.sh",
}


def test_hook_scripts_present_and_executable():
    for name in EXPECTED_HOOKS:
        p = BIN / name
        assert p.is_file(), f"bin/{name} missing"
        assert os.access(p, os.X_OK), f"bin/{name} not executable"


def test_credential_patterns_present():
    assert PATTERNS.is_file(), "credential-patterns.txt missing at repo root"
    body = PATTERNS.read_text(encoding="utf-8")
    for pat in ("master.key", "settings.yaml", "*.key", "*.pem"):
        assert pat in body, f"pattern {pat} missing"


def test_block_hook_resolves_patterns_from_repo_root():
    src = (BIN / "block-credential-read.sh").read_text(encoding="utf-8")
    assert "/../credential-patterns.txt" in src, "patterns path not adjusted for bin/ layout"
    assert "/../../credential-patterns.txt" not in src, "old framework/ relative path still present"


# Credential-guard behavior matrix (issue #28). Encodes the SURFACING model
# documented in plugin/credential-patterns.txt: block only what would emit a
# credential file's CONTENT into context; naming/feeding-as-argument is allowed.
# Path-based checks (Read/Grep/Edit/Write) are default-deny.
CRED_GUARD_MATRIX = [
    # (tool_name, tool_input, expected_exit, why)
    ("Bash", {"command": "cat master.key"}, 2, "cat surfaces content"),
    ("Bash", {"command": "cat settings.yaml"}, 2, "cat surfaces content"),
    ("Bash", {"command": "head .env"}, 2, "head surfaces content"),
    ("Bash", {"command": "grep key master.key"}, 2, "grep surfaces content"),
    ("Bash", {"command": "base64 master.key"}, 2, "encode+emit surfaces content"),
    ("Bash", {"command": "echo master.key"}, 0, "names the file, no content"),
    ("Bash", {"command": "git add master.key"}, 0, "feeds as argument (surfacing model)"),
    ("Bash", {"command": "ls -la"}, 0, "unrelated command"),
    ("Bash", {"command": "workato push"}, 0, "unrelated command"),
    ("Read", {"file_path": "/w/master.key"}, 2, "path default-deny"),
    ("Read", {"file_path": "docs/readme.md"}, 0, "non-credential path"),
    ("Grep", {"path": ".env"}, 2, "path default-deny"),
    ("Write", {"file_path": "a/settings.yaml"}, 2, "path default-deny"),
]


@pytest.mark.parametrize(
    "tool_name,tool_input,expected,why",
    CRED_GUARD_MATRIX,
    ids=[f"{c[0]}:{next(iter(c[1].values()))}" for c in CRED_GUARD_MATRIX],
)
def test_credential_guard_matrix(tool_name, tool_input, expected, why):
    r = _run_hook("block-credential-read.sh",
                  {"tool_name": tool_name, "tool_input": tool_input})
    assert r.returncode == expected, (
        f"{tool_name} {tool_input}: expected exit {expected} ({why}), "
        f"got {r.returncode}: {r.stderr}"
    )


# validate-before-push behavior (issue #28): fixture project driven via
# CLAUDE_PROJECT_DIR; the workato-CLI validation step degrades gracefully
# when the CLI is absent, so these cover the hook's own checks.
def _project_fixture(tmp_path, recipe_json):
    proj = tmp_path / "projects" / "p1"
    proj.mkdir(parents=True)
    (proj / ".workatoenv").write_text("project_id=1\n", encoding="utf-8")
    (proj / "bad.recipe.json").write_text(recipe_json, encoding="utf-8")
    return tmp_path


def test_validate_hook_blocks_broken_recipe_json(tmp_path):
    ws = _project_fixture(tmp_path, "{broken")
    r = _run_hook("validate-before-push.sh",
                  {"tool_input": {"command": "workato push"}},
                  env={"CLAUDE_PROJECT_DIR": str(ws)})
    assert r.returncode == 2, f"broken recipe JSON must block push: {r.stderr}"


@pytest.mark.skipif(shutil.which("workato") is not None,
                    reason="workato CLI present — hook would call the real validator")
def test_validate_hook_passes_clean_project(tmp_path):
    ws = _project_fixture(tmp_path, '{"name": "r", "code": {}}')
    r = _run_hook("validate-before-push.sh",
                  {"tool_input": {"command": "workato push"}},
                  env={"CLAUDE_PROJECT_DIR": str(ws)})
    assert r.returncode == 0, f"clean project must pass: {r.stderr}"


def test_validate_hook_ignores_non_push_commands():
    r = _run_hook("validate-before-push.sh", {"tool_input": {"command": "ls"}})
    assert r.returncode == 0


# sync-docs-after-sdk-push behavior (issue #28).
def test_sync_docs_hook_reminds_after_successful_sdk_push():
    r = _run_hook("sync-docs-after-sdk-push.sh", {
        "tool_input": {"command":
                       "python3 scripts/workato-api.py sdk push --connector connectors/foo/connector.rb"},
        "tool_response": {"exitCode": 0},
    })
    assert r.returncode == 0
    assert "connectors/docs/foo.md" in r.stdout, "reminder must name the doc to update"


def test_sync_docs_hook_silent_on_failure_and_non_sdk():
    failed = _run_hook("sync-docs-after-sdk-push.sh", {
        "tool_input": {"command":
                       "python3 scripts/workato-api.py sdk push --connector connectors/foo/connector.rb"},
        "tool_response": {"exitCode": 1},
    })
    assert failed.returncode == 0 and failed.stdout.strip() == ""
    unrelated = _run_hook("sync-docs-after-sdk-push.sh",
                          {"tool_input": {"command": "workato push"},
                           "tool_response": {"exitCode": 0}})
    assert unrelated.returncode == 0 and unrelated.stdout.strip() == ""


def test_session_start_rules_emits_context():
    script = BIN / "session-start-rules"
    assert script.is_file() and os.access(script, os.X_OK), "bin/session-start-rules missing/!x"
    env = dict(os.environ, CLAUDE_PLUGIN_ROOT=str(PLUGIN))
    r = subprocess.run(["bash", str(script)], input="{}", capture_output=True, text=True, env=env)
    assert r.returncode == 0, f"script failed: {r.stderr}"
    out = json.loads(r.stdout)
    ctx = out["hookSpecificOutput"]["additionalContext"]
    assert "Workato Recipe JSON Format" in ctx, "rule content not injected"


def _load_hooks(name):
    return json.loads((HOOKS / name).read_text(encoding="utf-8"))


def test_cc_hooks_json():
    d = _load_hooks("hooks.json")
    blob = json.dumps(d)
    assert "${CLAUDE_PLUGIN_ROOT}" in blob, "CC must use ${CLAUDE_PLUGIN_ROOT}"
    # CC blob must not use the Codex variable
    assert "$PLUGIN_ROOT" not in blob.replace("${CLAUDE_PLUGIN_ROOT}", "")
    h = d["hooks"]
    assert "PreToolUse" in h and "PostToolUse" in h and "SessionStart" in h
    assert "block-credential-read.sh" in blob
    assert "validate-before-push.sh" in blob
    assert "sync-docs-after-sdk-push.sh" in blob
    assert "session-start-rules" in blob


def test_codex_hooks_json():
    d = _load_hooks("codex.hooks.json")
    blob = json.dumps(d)
    assert "$PLUGIN_ROOT" in blob, "Codex must use $PLUGIN_ROOT"
    assert "${CLAUDE_PLUGIN_ROOT}" not in blob
    assert "block-credential-read.sh" in blob


def test_cursor_hooks_json():
    d = _load_hooks("cursor.hooks.json")
    assert d.get("version") == 1
    h = d["hooks"]
    assert any(k in h for k in ("postToolUse", "preToolUse"))
    blob = json.dumps(d)
    assert "Shell" in blob  # Cursor matcher
    assert "${CLAUDE_PLUGIN_ROOT}" not in blob and "$PLUGIN_ROOT" not in blob


def test_all_hook_paths_resolve_to_real_scripts():
    for name in ("hooks.json", "codex.hooks.json", "cursor.hooks.json"):
        blob = json.dumps(_load_hooks(name))
        for script in ("block-credential-read.sh", "sync-docs-after-sdk-push.sh"):
            if script in blob:
                assert (BIN / script).is_file()


def test_per_editor_hook_script_set():
    """Lock the intended per-editor hook wiring so an accidental drop is caught."""
    expected = {
        "hooks.json": {
            "validate-before-push.sh", "block-credential-read.sh",
            "sync-docs-after-sdk-push.sh", "session-start-rules",
        },
        "codex.hooks.json": {"block-credential-read.sh", "session-start-rules"},
        "cursor.hooks.json": {"block-credential-read.sh", "sync-docs-after-sdk-push.sh"},
    }
    for name, want in expected.items():
        blob = json.dumps(_load_hooks(name))
        got = {s for s in (
            "validate-before-push.sh", "block-credential-read.sh",
            "sync-docs-after-sdk-push.sh", "session-start-rules",
        ) if s in blob}
        assert got == want, f"{name}: hook set {got} != expected {want}"
