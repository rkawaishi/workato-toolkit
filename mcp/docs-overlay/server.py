"""docs-overlay MCP server (FastMCP).

- kit docs: resolved from this file's location (<plugin_root>/docs) — editor-agnostic.
- org docs: resolved from the user's project (cwd / git toplevel) at org/docs.
"""
import os
import subprocess
from pathlib import Path
from typing import Optional

from fastmcp import FastMCP

import overlay  # same directory

HERE = Path(__file__).resolve()
KIT_DOCS = HERE.parents[2] / "docs"  # <plugin_root>/docs


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
def workato_docs_lookup(path: str) -> str:
    """Look up a Workato knowledge-base doc by relative path (e.g. 'connectors/slack.md').

    Returns the kit doc merged with the organization overlay (org/docs) when present;
    the organization version overrides the kit baseline on conflict. Use this instead
    of reading docs files directly.
    """
    return overlay.resolve_doc(KIT_DOCS, _find_org_docs(), path)


@mcp.tool()
def workato_docs_list(prefix: str = "") -> list:
    """List available Workato doc paths (kit + org overlay), optionally filtered by prefix
    (e.g. 'connectors/')."""
    return overlay.list_docs(KIT_DOCS, _find_org_docs(), prefix)


if __name__ == "__main__":
    mcp.run()
