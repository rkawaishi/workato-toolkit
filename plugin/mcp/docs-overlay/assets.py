"""Workspace-asset resolution for the docs-overlay MCP server.

The plugin bundles a few files that skills materialize into the user's
workspace (`/setup-workspace`). This module maps a flat allowlisted name to
the bundled file's absolute path — names only, no traversal, no content.
"""
from pathlib import Path

# name -> path relative to the plugin root
ASSETS = {
    "workato-api.py": "scripts/workato-api.py",
    "ensure-workatoignore.sh": "scripts/ensure-workatoignore.sh",
    "workatoignore.template": "templates/workatoignore.template",
    # Generation references for the workato-builder subagent: a subagent has
    # neither the always-on context nor a skill-file path, so it resolves its
    # per-asset-type procedure through this tool (issues #18/#22).
    "workato-create/references/recipe.md": "skills/workato-create/references/recipe.md",
    "workato-create/references/genie.md": "skills/workato-create/references/genie.md",
    "workato-create/references/mcp-server.md": "skills/workato-create/references/mcp-server.md",
    "workato-create/references/workflow-app.md": "skills/workato-create/references/workflow-app.md",
    "workato-create/references/connector.md": "skills/workato-create/references/connector.md",
    # Format-spec rules the builder needs to generate valid JSON / Ruby. These
    # are always-on rules for the main session, but a subagent gets no always-on
    # injection — it fetches the same source-of-truth files through this tool
    # (issue #22). asset_path (not docs_lookup) on purpose: format specs are
    # kit-canonical and must not be silently altered by an org overlay.
    "rules/workato-recipe-format.md": "rules/workato-recipe-format.md",
    "rules/workato-agentic-format.md": "rules/workato-agentic-format.md",
    "rules/workato-connector-sdk.md": "rules/workato-connector-sdk.md",
    "rules/workato-project-structure.md": "rules/workato-project-structure.md",
    # lcap_page.json has its OWN format spec (agentic-format covers lcap_app /
    # workato_db_table only) — the workflow-app page lane needs it too (#22).
    "rules/workato-page-components.md": "rules/workato-page-components.md",
}


def asset_path(plugin_root: Path, name: str) -> str:
    """Return the absolute path of a bundled asset, or an UNKNOWN ASSET error."""
    rel = ASSETS.get(name)
    if rel is None:
        return f"UNKNOWN ASSET: {name!r}. Valid names: {', '.join(sorted(ASSETS))}"
    return str((Path(plugin_root) / rel).resolve())
