import re
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
RULES = REPO / "plugin" / "rules"

EXPECTED_RULES = {
    "org-knowledge-overlay",
    "workato-agentic-format",
    "workato-cli-autonomy",
    "workato-cli",
    "workato-connector-sdk",
    "workato-deployment-flow",
    "workato-page-components",
    "workato-project-structure",
    "workato-recipe-format",
}

def test_all_rules_present():
    found = {p.stem for p in RULES.glob("*.md")}
    assert found == EXPECTED_RULES, f"missing/extra: {EXPECTED_RULES ^ found}"

def test_rules_nonempty_with_heading():
    for stem in EXPECTED_RULES:
        text = (RULES / f"{stem}.md").read_text(encoding="utf-8")
        assert len(text) > 200, f"{stem}.md too short"
        assert re.search(r"^# .+", text, re.MULTILINE), f"{stem}.md has no top heading"

import os, subprocess, json

BIN = REPO / "plugin" / "bin"
PATTERNS = REPO / "plugin" / "credential-patterns.txt"

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

def test_block_hook_blocks_cat_master_key():
    payload = json.dumps({"tool_name": "Bash", "tool_input": {"command": "cat master.key"}})
    r = subprocess.run(["bash", str(BIN / "block-credential-read.sh")],
                       input=payload, capture_output=True, text=True)
    assert r.returncode == 2, f"expected block (exit 2), got {r.returncode}: {r.stderr}"

def test_block_hook_allows_plain_command():
    payload = json.dumps({"tool_name": "Bash", "tool_input": {"command": "ls -la"}})
    r = subprocess.run(["bash", str(BIN / "block-credential-read.sh")],
                       input=payload, capture_output=True, text=True)
    assert r.returncode == 0, f"expected allow (exit 0), got {r.returncode}: {r.stderr}"

AGENTS = REPO / "plugin" / "agents"

def test_agent_md_present():
    md = AGENTS / "workato-builder.md"
    assert md.is_file(), "agents/workato-builder.md missing"
    text = md.read_text(encoding="utf-8")
    assert text.startswith("---"), "agent md missing frontmatter"
    assert re.search(r"^name: workato-builder\s*$", text, re.MULTILINE)
    assert re.search(r"^description: ", text, re.MULTILINE)


def test_session_start_rules_emits_context():
    script = BIN / "session-start-rules"
    assert script.is_file() and os.access(script, os.X_OK), "bin/session-start-rules missing/!x"
    env = dict(os.environ, CLAUDE_PLUGIN_ROOT=str(REPO / "plugin"))
    r = subprocess.run(["bash", str(script)], input="{}", capture_output=True, text=True, env=env)
    assert r.returncode == 0, f"script failed: {r.stderr}"
    out = json.loads(r.stdout)
    ctx = out["hookSpecificOutput"]["additionalContext"]
    assert "Workato Recipe JSON Format" in ctx, "rule content not injected"


HOOKS = REPO / "plugin" / "hooks"

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


def test_agent_has_no_stale_rule_paths():
    """Agent md/toml must not reference @.claude/rules or .claude/rules paths
    (rules are always-on; paths don't resolve under plugin distribution)."""
    for f in ("workato-builder.md", "workato-builder.toml"):
        text = (AGENTS / f).read_text(encoding="utf-8")
        assert ".claude/rules/" not in text, f"agents/{f} has stale .claude/rules path"


def test_overlay_rule_reflects_plugin_distribution():
    text = (RULES / "org-knowledge-overlay.md").read_text(encoding="utf-8")
    # Reads go through the docs-overlay MCP, not @docs/@org/docs file reads.
    assert "workato_docs_lookup" in text, "overlay rule must describe the MCP read tool"
    # Submodule / symlink era wording must be gone.
    assert "submodule" not in text, "overlay rule still mentions a kit submodule"
    assert "symlink to kit/docs" not in text, "overlay rule still describes the docs/ symlink"
    # The official-spec write target is now org/docs (not the read-only bundled docs/).
    assert "`docs/` (kit) | `/sync-connectors`" not in text, \
        "overlay rule still routes sync skills to the read-only kit docs/"
