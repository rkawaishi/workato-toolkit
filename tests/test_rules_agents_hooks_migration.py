import re
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
RULES = REPO / "rules"

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

BIN = REPO / "bin"
PATTERNS = REPO / "credential-patterns.txt"

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

AGENTS = REPO / "agents"

def test_agent_md_present():
    md = AGENTS / "workato-builder.md"
    assert md.is_file(), "agents/workato-builder.md missing"
    text = md.read_text(encoding="utf-8")
    assert text.startswith("---"), "agent md missing frontmatter"
    assert re.search(r"^name: workato-builder\s*$", text, re.MULTILINE)
    assert re.search(r"^description: ", text, re.MULTILINE)
