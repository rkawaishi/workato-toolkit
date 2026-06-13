import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GUIDES = ROOT / "docs" / "guides"
README = ROOT / "README.md"

# S4 legacy distribution tokens — must be gone from user-facing docs. Covers the
# old submodule/setup.sh model AND old per-editor workspace paths (rules/skills
# lived under .claude/ .cursor/ .gemini/ .agents/ via symlink/copy); under the
# plugin model those live inside the plugin, reached via always-on rules / the MCP.
_LEGACY = re.compile(
    r"submodule|setup\.sh|sync_agents\.py|framework/|@local"
    r"|@\.claude/|\.claude/(?:rules|skills|CLAUDE\.md)|\.cursor/(?:rules|skills)/"
    r"|\.gemini/skills/|\.agents/skills/"
)

EXPECTED_VERSION = "0.1.0"


def _doc_files():
    return [README] + sorted(GUIDES.glob("*.md"))


def test_no_legacy_distribution_refs_in_docs():
    offenders = []
    for p in _doc_files():
        for i, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
            if _LEGACY.search(line):
                offenders.append(f"{p.relative_to(ROOT)}:{i}: {line.strip()}")
    assert not offenders, "legacy submodule/setup.sh refs remain:\n" + "\n".join(offenders)


def _load(rel):
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


def test_manifest_versions_bumped_and_consistent():
    cc = _load(".claude-plugin/plugin.json")["version"]
    codex = _load(".codex-plugin/plugin.json")["version"]
    cursor = _load(".cursor-plugin/plugin.json")["version"]
    assert cc == EXPECTED_VERSION, f"CC version {cc} != {EXPECTED_VERSION}"
    assert codex == EXPECTED_VERSION, f"Codex version {codex} != {EXPECTED_VERSION}"
    assert cursor == EXPECTED_VERSION, f"Cursor version {cursor} != {EXPECTED_VERSION}"


def test_release_workflow_shape():
    wf = (ROOT / ".github" / "workflows" / "release.yml").read_text(encoding="utf-8")
    assert "on:" in wf and "tags:" in wf, "release.yml must trigger on tags"
    assert "scripts/sync_derived.py" in wf, "release.yml must verify derived sync"
    assert "pytest" in wf, "release.yml must run the test suite"
    assert "release" in wf.lower(), "release.yml must publish a release"


def test_readme_covers_plugin_install():
    text = README.read_text(encoding="utf-8")
    # the three official editors' marketplace/install entry points
    assert "/plugin marketplace add rkawaishi/workato-toolkit" in text
    assert "codex plugin marketplace add rkawaishi/workato-toolkit" in text
    assert "Cursor" in text
    # Gemini is deferred, not dropped
    assert "Gemini" in text and "soon" in text.lower()
    # security defense-in-depth is documented
    assert "permissions" in text and "deny" in text
    assert ".codexignore" in text
