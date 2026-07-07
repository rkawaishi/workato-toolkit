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
# when the CLI is absent, so these cover the hook's own checks. HOME is
# isolated per test so a real ~/.workato/profiles never leaks in.
def _project_fixture(tmp_path, recipe_json, filename="a.recipe.json", workatoenv=None):
    proj = tmp_path / "projects" / "p1"
    proj.mkdir(parents=True)
    (proj / ".workatoenv").write_text(
        json.dumps(workatoenv if workatoenv is not None else {"project_id": 1}),
        encoding="utf-8",
    )
    (proj / filename).write_text(recipe_json, encoding="utf-8")
    return tmp_path


def _home_with_profiles(tmp_path, current, profiles):
    """profiles: {name: workspace_id_or_None} — mirrors ~/.workato/profiles."""
    home = tmp_path / "home"
    (home / ".workato").mkdir(parents=True)
    (home / ".workato" / "profiles").write_text(json.dumps({
        "current_profile": current,
        "profiles": {n: {"workspace_id": ws} for n, ws in profiles.items()},
    }), encoding="utf-8")
    return home


def _empty_home(tmp_path):
    home = tmp_path / "home"
    home.mkdir(exist_ok=True)
    return home


def test_validate_hook_blocks_broken_recipe_json(tmp_path):
    ws = _project_fixture(tmp_path, "{broken", filename="broken.recipe.json")
    r = _run_hook("validate-before-push.sh",
                  {"tool_input": {"command": "workato push"}},
                  env={"CLAUDE_PROJECT_DIR": str(ws), "HOME": str(_empty_home(tmp_path))})
    assert r.returncode == 2, f"broken recipe JSON must block push: {r.stderr}"


@pytest.mark.skipif(shutil.which("workato") is not None,
                    reason="workato CLI present — hook would call the real validator")
def test_validate_hook_passes_clean_project(tmp_path):
    ws = _project_fixture(tmp_path, '{"name": "r", "code": {}}')
    r = _run_hook("validate-before-push.sh",
                  {"tool_input": {"command": "workato push"}},
                  env={"CLAUDE_PROJECT_DIR": str(ws), "HOME": str(_empty_home(tmp_path))})
    assert r.returncode == 0, f"clean project must pass: {r.stderr}"


def test_validate_hook_ignores_non_push_commands():
    r = _run_hook("validate-before-push.sh", {"tool_input": {"command": "ls"}})
    assert r.returncode == 0


# Environment guard (issue #10): workato push / recipes start|stop must be
# refused unless the RESOLVED profile is a -dev profile. Resolution mirrors
# the helper's resolve_profile(): --profile flag > .workatoenv workspace_id
# match > current_profile. No profiles file -> fail open (the CLI itself
# cannot run without one). This is the deterministic layer under the
# workato-deployment-flow rule.
def test_env_guard_blocks_push_on_non_dev_profile(tmp_path):
    home = _home_with_profiles(tmp_path, "acme-prod",
                               {"acme-prod": 1, "acme-dev": 2})
    ws = _project_fixture(tmp_path, '{"name": "r"}')
    r = _run_hook("validate-before-push.sh",
                  {"tool_input": {"command": "workato push"}},
                  env={"CLAUDE_PROJECT_DIR": str(ws), "HOME": str(home)})
    assert r.returncode == 2, "push on acme-prod must be blocked"
    assert "-dev" in r.stderr and "acme-prod" in r.stderr, r.stderr


def test_env_guard_blocks_explicit_profile_flag(tmp_path):
    home = _home_with_profiles(tmp_path, "acme-dev",
                               {"acme-dev": 1, "acme-test": 2})
    ws = _project_fixture(tmp_path, '{"name": "r"}')
    r = _run_hook("validate-before-push.sh",
                  {"tool_input": {"command": "workato push --profile acme-test"}},
                  env={"CLAUDE_PROJECT_DIR": str(ws), "HOME": str(home)})
    assert r.returncode == 2, "--profile acme-test must override current and block"


@pytest.mark.skipif(shutil.which("workato") is not None,
                    reason="workato CLI present — hook would call the real validator")
def test_env_guard_workspace_id_resolves_to_dev(tmp_path):
    """.workatoenv binding to the dev workspace wins over a prod current_profile."""
    home = _home_with_profiles(tmp_path, "acme-prod",
                               {"acme-prod": 1, "acme-dev": 2})
    ws = _project_fixture(tmp_path, '{"name": "r", "code": {}}',
                          workatoenv={"project_id": 9, "workspace_id": 2})
    r = _run_hook("validate-before-push.sh",
                  {"tool_input": {"command": "workato push"}},
                  env={"CLAUDE_PROJECT_DIR": str(ws), "HOME": str(home)})
    assert r.returncode == 0, f"workspace-bound dev profile must pass: {r.stderr}"


def test_env_guard_blocks_raw_recipes_start(tmp_path):
    """The raw-CLI recipes start path (used by /push-project --start) is guarded
    too — previously only the helper-mediated path checked the profile."""
    home = _home_with_profiles(tmp_path, "acme-prod", {"acme-prod": 1})
    ws = _project_fixture(tmp_path, '{"name": "r"}')
    r = _run_hook("validate-before-push.sh",
                  {"tool_input": {"command": "workato recipes start --all"}},
                  env={"CLAUDE_PROJECT_DIR": str(ws), "HOME": str(home)})
    assert r.returncode == 2, "recipes start on prod profile must be blocked"


def _multi_project_fixture(tmp_path, bindings):
    """bindings: {project_dir_name: workatoenv_dict}"""
    for pname, envd in bindings.items():
        proj = tmp_path / "projects" / pname
        proj.mkdir(parents=True)
        (proj / ".workatoenv").write_text(json.dumps(envd), encoding="utf-8")
        (proj / "a.recipe.json").write_text('{"name": "r"}', encoding="utf-8")
    return tmp_path


def test_env_guard_blocks_whitespace_variant(tmp_path):
    """The fast-exit gate must never be stricter than the guard regex —
    'workato  push' (two spaces) still runs and must still be guarded."""
    home = _home_with_profiles(tmp_path, "acme-prod", {"acme-prod": 1})
    ws = _project_fixture(tmp_path, '{"name": "r"}')
    r = _run_hook("validate-before-push.sh",
                  {"tool_input": {"command": "workato  push"}},
                  env={"CLAUDE_PROJECT_DIR": str(ws), "HOME": str(home)})
    assert r.returncode == 2, "double-space variant must not bypass the guard"


def test_env_guard_blocks_chained_profile_switch(tmp_path):
    """TOCTOU: `profiles use <prod>` in the same command rewrites
    current_profile BEFORE the push runs — the guard must judge the
    switched-to profile, not the stale file state."""
    home = _home_with_profiles(tmp_path, "acme-dev",
                               {"acme-dev": 1, "acme-prod": 2})
    ws = _project_fixture(tmp_path, '{"name": "r"}')
    r = _run_hook("validate-before-push.sh",
                  {"tool_input": {"command":
                                  "workato profiles use acme-prod && workato push"}},
                  env={"CLAUDE_PROJECT_DIR": str(ws), "HOME": str(home)})
    assert r.returncode == 2, "chained profile switch to prod must be blocked"


def test_env_guard_blocks_sdk_push_on_non_dev(tmp_path):
    """`workato sdk push` releases connector code into the profile's
    workspace — guarded like push (the helper route already self-guards)."""
    home = _home_with_profiles(tmp_path, "acme-prod", {"acme-prod": 1})
    ws = _project_fixture(tmp_path, '{"name": "r"}')
    r = _run_hook("validate-before-push.sh",
                  {"tool_input": {"command":
                                  "workato sdk push --connector connectors/foo/connector.rb"}},
                  env={"CLAUDE_PROJECT_DIR": str(ws), "HOME": str(home)})
    assert r.returncode == 2, "raw-CLI sdk push on prod profile must be blocked"


def test_env_guard_ignores_sdk_gem_push(tmp_path):
    """`bundle exec workato push` (SDK gem) authenticates via the connector's
    own settings, not CLI profiles — profile guarding must not block it."""
    home = _home_with_profiles(tmp_path, "acme-prod", {"acme-prod": 1})
    ws = _project_fixture(tmp_path, '{"name": "r"}')
    r = _run_hook("validate-before-push.sh",
                  {"tool_input": {"command": "bundle exec workato push"}},
                  env={"CLAUDE_PROJECT_DIR": str(ws), "HOME": str(home)})
    assert r.returncode == 0, f"SDK gem push uses different auth: {r.stderr}"


def test_env_guard_short_profile_flag(tmp_path):
    home = _home_with_profiles(tmp_path, "acme-dev",
                               {"acme-dev": 1, "acme-test": 2})
    ws = _project_fixture(tmp_path, '{"name": "r"}')
    r = _run_hook("validate-before-push.sh",
                  {"tool_input": {"command": "workato push -p acme-test"}},
                  env={"CLAUDE_PROJECT_DIR": str(ws), "HOME": str(home)})
    assert r.returncode == 2, "-p short form must be recognized like --profile"


def test_env_guard_projects_use_overrides_first_match(tmp_path):
    """`projects use <name>` decides which workspace the push targets — the
    guard must resolve THAT project's binding, not the alphabetically first."""
    home = _home_with_profiles(tmp_path, "acme-dev",
                               {"acme-dev": 1, "acme-prod": 2})
    ws = _multi_project_fixture(tmp_path, {
        "a-dev-app": {"workspace_id": 1},
        "zprod-app": {"workspace_id": 2},
    })
    r = _run_hook("validate-before-push.sh",
                  {"tool_input": {"command":
                                  'workato projects use "zprod-app" && workato push'}},
                  env={"CLAUDE_PROJECT_DIR": str(ws), "HOME": str(home)})
    assert r.returncode == 2, "push into the prod-bound project must be blocked"


def test_env_guard_ambiguous_bindings_fall_to_current(tmp_path):
    """Multiple projects bound to different workspaces: first-match is wrong,
    so resolution falls to current_profile (prod here) and blocks."""
    home = _home_with_profiles(tmp_path, "acme-prod",
                               {"acme-dev": 1, "acme-prod": 2})
    ws = _multi_project_fixture(tmp_path, {
        "a-app": {"workspace_id": 1},
        "b-app": {"workspace_id": 2},
    })
    r = _run_hook("validate-before-push.sh",
                  {"tool_input": {"command": "workato push"}},
                  env={"CLAUDE_PROJECT_DIR": str(ws), "HOME": str(home)})
    assert r.returncode == 2, "ambiguous bindings must not resolve via first-match"


@pytest.mark.skipif(shutil.which("workato") is not None,
                    reason="workato CLI present — hook would call the real validator")
def test_env_guard_fails_open_without_profiles(tmp_path):
    ws = _project_fixture(tmp_path, '{"name": "r", "code": {}}')
    r = _run_hook("validate-before-push.sh",
                  {"tool_input": {"command": "workato push"}},
                  env={"CLAUDE_PROJECT_DIR": str(ws), "HOME": str(_empty_home(tmp_path))})
    assert r.returncode == 0, "no profiles configured -> the CLI itself will fail; allow"


# sync-docs-after-sdk-push behavior (issue #28).
def test_sync_docs_hook_reminds_after_successful_sdk_push():
    r = _run_hook("sync-docs-after-sdk-push.sh", {
        "tool_input": {"command":
                       "python3 scripts/workato-api.py sdk push --connector connectors/foo/connector.rb"},
        "tool_response": {"exitCode": 0},
    })
    assert r.returncode == 0
    assert "connectors/docs/foo.md" in r.stdout, "reminder must name the doc to update"


def test_sync_docs_hook_covers_all_sdk_push_routes():
    """Issue #10: the reminder must fire for the raw Platform CLI form and the
    SDK gem form too, not only the helper-mediated route."""
    raw_cli = _run_hook("sync-docs-after-sdk-push.sh", {
        "tool_input": {"command": "workato sdk push --connector connectors/bar/connector.rb"},
        "tool_response": {"exitCode": 0},
    })
    assert "connectors/docs/bar.md" in raw_cli.stdout, "raw CLI route must remind"
    gem_form = _run_hook("sync-docs-after-sdk-push.sh", {
        "tool_input": {"command": "bundle exec workato push"},
        "tool_response": {"exitCode": 0},
    })
    assert "connectors/docs/" in gem_form.stdout, (
        "sdk push without --connector must emit the generic reminder"
    )


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
