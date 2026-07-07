"""Subagent definition guards (plugin/agents/)."""
import re

from conftest import AGENTS


def test_agent_md_present():
    md = AGENTS / "workato-builder.md"
    assert md.is_file(), "agents/workato-builder.md missing"
    text = md.read_text(encoding="utf-8")
    assert text.startswith("---"), "agent md missing frontmatter"
    assert re.search(r"^name: workato-builder\s*$", text, re.MULTILINE)
    assert re.search(r"^description: ", text, re.MULTILINE)


def test_agent_has_no_stale_rule_paths():
    """Agent md/toml must not reference @.claude/rules or .claude/rules paths
    (rules are always-on; paths don't resolve under plugin distribution)."""
    for f in ("workato-builder.md", "workato-builder.toml"):
        text = (AGENTS / f).read_text(encoding="utf-8")
        assert ".claude/rules/" not in text, f"agents/{f} has stale .claude/rules path"
