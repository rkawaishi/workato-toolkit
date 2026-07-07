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


def test_rules_use_no_at_path_references():
    """Rules ship inside the plugin: `@docs/...` / `@.claude/...` paths never
    resolve for users. Docs go through workato_docs_lookup; other rules are
    referenced by name ("the `workato-cli` rule (always-on)")."""
    offenders = []
    for p in sorted(RULES.glob("*.md")):
        for i, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
            if re.search(r"@(?:docs|org/docs)/|@\.claude/", line):
                offenders.append(f"{p.name}:{i}: {line.strip()}")
    assert not offenders, "@-path references in rules:\n" + "\n".join(offenders)


# The helper-command table in workato-cli.md must not silently lag the helper.
# Each entry here must exist in BOTH the helper source and the rule's table —
# extend this list when adding a helper subcommand.
HELPER_COMMANDS_DOCUMENTED = [
    "jobs list", "jobs get", "jobs tail",
    "recipes list", "recipes start", "recipes stop",
    "connectors list-platform", "connectors list-custom",
    "sdk push", "sdk pull", "sdk pull-project", "sdk diff-project",
    "sdk test", "sdk edit", "sdk decrypt", "sdk generate-schema",
    "oauth-profiles",
    "deploy", "api-clients", "profile show",
]


def test_helper_command_table_in_sync():
    from conftest import PLUGIN
    rule = (RULES / "workato-cli.md").read_text(encoding="utf-8")
    helper = (PLUGIN / "scripts" / "workato-api.py").read_text(encoding="utf-8")
    for cmd in HELPER_COMMANDS_DOCUMENTED:
        assert cmd in helper, f"{cmd!r} listed here but gone from the helper"
        assert cmd.split()[-1] in rule, (
            f"helper subcommand {cmd!r} missing from workato-cli.md's table"
        )
