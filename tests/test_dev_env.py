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
WORKFLOWS = sorted(
    p
    for pattern in ("*.yml", "*.yaml")  # GitHub Actions honors both extensions
    for p in (REPO / ".github" / "workflows").glob(pattern)
)

# Any way of invoking pip in a workflow step: pip / pip3 / python -m pip.
_PIP_INSTALL = re.compile(r"\b(?:pip3?|python3?\s+-m\s+pip)\b[^\n]*\binstall\b[^\n]*")


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
    """Every pip install in EVERY workflow must come from requirements-dev.txt.

    Applies to all workflows (not just test-running ones) so a future
    lint-only workflow can't reintroduce inline ad-hoc installs. Allowed
    exceptions: upgrading pip itself. Flags/quoting/order don't matter —
    the line just has to reference the requirements file.
    """
    assert WORKFLOWS, "expected workflow files under .github/workflows/"
    pytest_workflows = []
    for wf in WORKFLOWS:
        text = wf.read_text(encoding="utf-8")
        if "pytest" in text:
            pytest_workflows.append(wf)
            assert "requirements-dev.txt" in text, (
                f"{wf.name}: install test deps via requirements-dev.txt, "
                "not an inline package list"
            )
        for m in _PIP_INSTALL.finditer(text):
            line = m.group(0)
            if "requirements-dev.txt" in line:
                continue
            if re.search(r"install\s+(-\S+\s+)*--upgrade\s+pip\b", line):
                continue  # pip self-upgrade is fine
            raise AssertionError(
                f"{wf.name}: inline pip install found ({line.strip()!r}); "
                "declare deps in requirements-dev.txt instead"
            )
    assert pytest_workflows, "expected at least one workflow running pytest"


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
    assert "python3 -m pip" in text, (
        "bootstrap must install via python3 -m pip so the install targets the "
        "same interpreter the tests run with (bare pip can point elsewhere)"
    )
    assert "STAMP" in text and "cksum" in text, (
        "bootstrap must have a fast path keyed on the requirements content "
        "(stamp file) so unchanged requirements skip pip entirely"
    )
    assert re.search(r"--retries\s+\d+", text) and re.search(r"--timeout\s+\d+", text), (
        "bootstrap's pip install must be time-bounded so an offline session "
        "isn't blocked by pip's default retry behavior"
    )
    assert "CLAUDE_PROJECT_DIR" in text, (
        "bootstrap must prefer $CLAUDE_PROJECT_DIR for root resolution "
        "(mirrors plugin/bin/session-start-rules' env-var-first idiom)"
    )


def test_claude_md_documents_dev_prerequisites():
    text = (REPO / "CLAUDE.md").read_text(encoding="utf-8")
    for needle, why in [
        ("requirements-dev.txt", "dependency file"),
        ("superpowers", "plan-execution plugin expectation + fallback"),
        ("dev-session-bootstrap", "SessionStart bootstrap"),
    ]:
        assert needle in text, f"CLAUDE.md must document the {why} ({needle!r})"
