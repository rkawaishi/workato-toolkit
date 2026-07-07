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
import subprocess

from conftest import REPO
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


# --- CI quality gates (issue #25) ---

def test_sync_check_has_lint_job():
    text = (REPO / ".github" / "workflows" / "sync-check.yml").read_text(encoding="utf-8")
    assert "ruff check ." in text, (
        "sync-check.yml must run ruff over the whole tree (opt-out coverage: "
        "a new python directory is linted without editing the workflow)"
    )
    assert "shellcheck" in text and "git ls-files" in text, (
        "shellcheck step must discover bash scripts by shebang via git ls-files "
        "(opt-out coverage incl. extensionless hooks), not a hardcoded path list"
    )


def test_ruff_config_pins_target_version():
    pyproject = REPO / "pyproject.toml"
    assert pyproject.is_file(), "pyproject.toml with [tool.ruff] config missing"
    text = pyproject.read_text(encoding="utf-8")
    assert "[tool.ruff]" in text
    assert re.search(r'target-version\s*=\s*"py311"', text), (
        "ruff target-version must match the documented Python floor (3.11)"
    )


def test_requirements_dev_declares_ruff():
    lines = [
        ln.strip()
        for ln in REQS.read_text(encoding="utf-8").splitlines()
        if ln.strip() and not ln.strip().startswith("#")
    ]
    assert any(re.match(r"^ruff\b", ln) for ln in lines), (
        "requirements-dev.txt must include ruff (CI lint job installs from it)"
    )


GATE_STEP_NAME = "Verify tag matches plugin manifest version"


def test_release_gates_tag_on_manifest_version():
    text = (REPO / ".github" / "workflows" / "release.yml").read_text(encoding="utf-8")
    assert GATE_STEP_NAME in text, (
        "release.yml must have the tag/manifest version-gate step"
    )
    # Bind the checks to the gate step's own block (from its name to the next
    # step), not to first occurrences anywhere in the file.
    gate_block = text.split(GATE_STEP_NAME, 1)[1].split("- name:", 1)[0]
    assert "GITHUB_REF_NAME" in gate_block and "plugin.json" in gate_block, (
        "the gate step must compare the pushed tag against plugin/.claude-plugin/"
        "plugin.json's version"
    )
    assert "CHANGELOG.md" in gate_block, (
        "the gate step must also require a matching '## [x.y.z]' CHANGELOG section"
    )
    assert text.index(GATE_STEP_NAME) < text.index("action-gh-release"), (
        "version gate must run before the release publish step"
    )


def test_changelog_exists_with_unreleased_section():
    changelog = REPO / "CHANGELOG.md"
    assert changelog.is_file(), "CHANGELOG.md missing (release notes need a curated home)"
    text = changelog.read_text(encoding="utf-8")
    assert "## [Unreleased]" in text, "CHANGELOG.md must keep an [Unreleased] section"


# sync-check.yml 側(tests/test_derived_sync.py の DRIFT_SCOPE)と同一の
# スコープ全文。substring ではリストの一部欠落を検知できない。
_DRIFT_SCOPE = (
    "git diff --exit-code -- "
    "plugin/rules/ plugin/agents/ plugin/AGENTS.md plugin/GEMINI.md CLAUDE.md"
)


def test_release_workflow_shape():
    wf = (REPO / ".github" / "workflows" / "release.yml").read_text(encoding="utf-8")
    assert "on:" in wf and "tags:" in wf, "release.yml must trigger on tags"
    assert "scripts/sync_derived.py" in wf, "release.yml must verify derived sync"
    assert "pytest" in wf, "release.yml must run the test suite"
    assert "release" in wf.lower(), "release.yml must publish a release"
    assert _DRIFT_SCOPE in wf, "drift scope must pin the full derived+frozen path list"


def test_python_floor_documented():
    claude_md = (REPO / "CLAUDE.md").read_text(encoding="utf-8")
    assert "Python 3.11" in claude_md, "CLAUDE.md must state the Python floor"
    helper_head = "\n".join(
        (REPO / "plugin" / "scripts" / "workato-api.py")
        .read_text(encoding="utf-8")
        .splitlines()[:40]
    )
    assert "Python 3.11" in helper_head, (
        "the shipped helper must declare its Python floor in the module docstring "
        "(it runs on the user's python3, not CI's)"
    )


# --- Verification harness (issue #28) ---

def test_self_install_smoke_script():
    p = REPO / "scripts" / "self-install-smoke.sh"
    assert p.is_file(), "scripts/self-install-smoke.sh missing (semi-automated smoke)"
    assert os.access(p, os.X_OK), "smoke script must be executable"
    r = subprocess.run(["bash", "-n", str(p)], capture_output=True, text=True)
    assert r.returncode == 0, f"smoke script has syntax errors: {r.stderr}"
    text = p.read_text(encoding="utf-8")
    for needle, why in [
        ("marketplace add", "claude-CLI install section"),
        ("plugin install", "claude-CLI install section"),
        ("session-start-rules", "structural preflight"),
        ("block-credential-read", "credential-guard preflight"),
        ("dev/verifications", "tells the runner where to record results"),
    ]:
        assert needle in text, f"smoke script must cover: {why} ({needle!r})"


def test_verifications_convention_documented():
    readme = REPO / "dev" / "verifications" / "README.md"
    assert readme.is_file(), "dev/verifications/README.md (recording convention) missing"
    text = readme.read_text(encoding="utf-8")
    assert "YYYY-MM-DD" in text, "must state the file-naming convention"
    dev_readme = (REPO / "dev" / "README.md").read_text(encoding="utf-8")
    assert "verifications" in dev_readme, "dev/README.md must mention verifications/"
    claude_md = (REPO / "CLAUDE.md").read_text(encoding="utf-8")
    assert "self-install-smoke.sh" in claude_md, (
        "CLAUDE.md's verification section must point at the smoke script"
    )
    assert "dev/verifications" in claude_md, (
        "CLAUDE.md must say where verification results are recorded"
    )
