"""Guards for the dev-session bootstrap (issue #24).

A fresh development session (especially Claude Code on the web) must be able
to run the test suite and the derived-file sync without manual setup:
- dev dependencies are declared once in requirements-dev.txt,
- CI installs from that same file (no inline ad-hoc pip installs),
- a committed .claude/settings.json bootstraps the session via a
  SessionStart hook and allowlists the routine dev commands,
- CLAUDE.md documents the prerequisites (including the superpowers plugin
  expectation for executing dev/plans/).
"""
import json
import os
import re
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
REQS = REPO / "requirements-dev.txt"
SETTINGS = REPO / ".claude" / "settings.json"
BOOTSTRAP = REPO / "scripts" / "dev-session-bootstrap.sh"
WORKFLOWS = sorted((REPO / ".github" / "workflows").glob("*.yml"))


def test_requirements_dev_declares_pytest():
    assert REQS.is_file(), "requirements-dev.txt must declare dev dependencies"
    lines = [
        ln.strip()
        for ln in REQS.read_text(encoding="utf-8").splitlines()
        if ln.strip() and not ln.strip().startswith("#")
    ]
    assert any(re.match(r"^pytest\b", ln) for ln in lines), (
        "requirements-dev.txt must include pytest"
    )


def test_ci_installs_from_requirements_dev():
    assert WORKFLOWS, "expected workflow files under .github/workflows/"
    for wf in WORKFLOWS:
        text = wf.read_text(encoding="utf-8")
        if "pytest" not in text:
            continue  # workflow that doesn't run tests
        assert "requirements-dev.txt" in text, (
            f"{wf.name}: install test deps via requirements-dev.txt, "
            "not an inline package list"
        )
        assert not re.search(r"pip install (?!-r requirements-dev\.txt)", text), (
            f"{wf.name}: found an inline pip install; declare deps in "
            "requirements-dev.txt instead"
        )


def test_claude_settings_bootstrap_hook():
    assert SETTINGS.is_file(), ".claude/settings.json (project dev settings) missing"
    data = json.loads(SETTINGS.read_text(encoding="utf-8"))

    hooks = data.get("hooks", {}).get("SessionStart", [])
    commands = [
        h.get("command", "")
        for entry in hooks
        for h in entry.get("hooks", [])
        if h.get("type") == "command"
    ]
    assert any("dev-session-bootstrap.sh" in c for c in commands), (
        "SessionStart hook must run scripts/dev-session-bootstrap.sh"
    )

    allow = data.get("permissions", {}).get("allow", [])
    assert any("pytest" in entry for entry in allow), (
        "permissions.allow should cover the routine pytest invocation"
    )
    assert any("sync_derived" in entry for entry in allow), (
        "permissions.allow should cover scripts/sync_derived.py"
    )


def test_bootstrap_script_is_idempotent_and_executable():
    assert BOOTSTRAP.is_file(), "scripts/dev-session-bootstrap.sh missing"
    assert os.access(BOOTSTRAP, os.X_OK), "bootstrap script must be executable"
    text = BOOTSTRAP.read_text(encoding="utf-8")
    assert "requirements-dev.txt" in text, (
        "bootstrap must install from requirements-dev.txt"
    )
    assert "import pytest" in text, (
        "bootstrap must probe before installing (idempotent / fast path)"
    )


def test_claude_md_documents_dev_prerequisites():
    text = (REPO / "CLAUDE.md").read_text(encoding="utf-8")
    for needle, why in [
        ("requirements-dev.txt", "dependency file"),
        ("superpowers", "plan-execution plugin expectation + fallback"),
        ("dev-session-bootstrap", "SessionStart bootstrap"),
    ]:
        assert needle in text, f"CLAUDE.md must document the {why} ({needle!r})"
