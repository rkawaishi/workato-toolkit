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
}


def asset_path(plugin_root: Path, name: str) -> str:
    """Return the absolute path of a bundled asset, or an UNKNOWN ASSET error."""
    rel = ASSETS.get(name)
    if rel is None:
        return f"UNKNOWN ASSET: {name!r}. Valid names: {', '.join(sorted(ASSETS))}"
    return str((Path(plugin_root) / rel).resolve())
