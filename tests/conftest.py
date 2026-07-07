"""Shared path constants for the test suite.

Import with `from conftest import REPO, PLUGIN` — pytest puts this directory
on sys.path. Add shared fixtures here rather than duplicating them per file.
See tests/README.md for which guard belongs in which file.
"""
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PLUGIN = REPO / "plugin"
SKILLS = PLUGIN / "skills"
RULES = PLUGIN / "rules"
DOCS = PLUGIN / "docs"
BIN = PLUGIN / "bin"
HOOKS = PLUGIN / "hooks"
AGENTS = PLUGIN / "agents"
WORKFLOWS = REPO / ".github" / "workflows"
