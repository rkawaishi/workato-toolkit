"""docs-overlay MCP server (FastMCP).

- kit docs: resolved from this file's location (<plugin_root>/docs) — editor-agnostic.
- org docs: resolved from the user's project (cwd / git toplevel) at org/docs.
"""
import os
import subprocess
from pathlib import Path
from typing import Optional

from fastmcp import FastMCP

import assets  # same directory
import overlay  # same directory

HERE = Path(__file__).resolve()
PLUGIN_ROOT = HERE.parents[2]
KIT_DOCS = PLUGIN_ROOT / "docs"  # <plugin_root>/docs


def _find_org_docs() -> Optional[Path]:
    start = Path(os.getcwd())
    root = start
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=start, capture_output=True, text=True, timeout=5,
        )
        if out.returncode == 0 and out.stdout.strip():
            root = Path(out.stdout.strip())
    except Exception:
        pass
    candidate = root / "org" / "docs"
    return candidate if candidate.is_dir() else None


mcp = FastMCP("workato-docs")


@mcp.tool()
def workato_docs_lookup(path: str, section: str | None = None) -> str:
    """Look up a Workato knowledge-base doc by relative path (e.g. 'connectors/slack.md').

    Returns the kit doc merged with the organization overlay (org/docs) when present;
    the organization version overrides the kit baseline on conflict. Use this instead
    of reading docs files directly. Pass `section` (a heading substring, e.g.
    'Actions') to fetch only that section of a large doc — a miss lists the
    available headings.
    """
    return overlay.resolve_doc(KIT_DOCS, _find_org_docs(), path, section)


@mcp.tool()
def workato_docs_list(prefix: str = "") -> list:
    """List available Workato doc paths (kit + org overlay), optionally filtered by prefix
    (e.g. 'connectors/')."""
    return overlay.list_docs(KIT_DOCS, _find_org_docs(), prefix)


@mcp.tool()
def workato_docs_search(query: str, prefix: str = "") -> list:
    """Search the knowledge base (kit + org overlay) for a case-insensitive
    substring; returns 'path:line: text' matches (capped). Use to find which
    doc covers a keyword (e.g. 'pagination', 'human_review') before a lookup."""
    return overlay.search_docs(KIT_DOCS, _find_org_docs(), query, prefix)


@mcp.tool()
def workato_asset_path(name: str) -> str:
    """Absolute path of a plugin-bundled workspace asset (e.g. 'workato-api.py',
    'ensure-workatoignore.sh', 'workatoignore.template').

    Skills copy the file from this path into the user's workspace
    (see /setup-workspace). Returns the path only, never file content.
    """
    return assets.asset_path(PLUGIN_ROOT, name)


if __name__ == "__main__":
    mcp.run()
