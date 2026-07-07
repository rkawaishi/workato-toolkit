"""Always-on rule guards (plugin/rules/*.md) — presence and content."""
import re

from conftest import RULES

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
