"""Cross-tree stale-token sweeps over user-facing docs.

Add here: full-scan guards that keep legacy wording / dead install surfaces
out of README, root CLAUDE.md, and plugin/docs/guides/. Skill-scoped sweeps
live in test_skills.py; rule-scoped ones in test_rules.py.
"""
import re

from conftest import DOCS, REPO

GUIDES = DOCS / "guides"
README = REPO / "README.md"

# S4 legacy distribution tokens — must be gone from user-facing docs. Covers the
# old submodule/setup.sh model AND old per-editor workspace paths (rules/skills
# lived under .claude/ .cursor/ .gemini/ .agents/ via symlink/copy); under the
# plugin model those live inside the plugin, reached via always-on rules / the MCP.
_LEGACY = re.compile(
    r"submodule|setup\.sh|sync_agents\.py|framework/|@local"
    r"|@\.claude/|\.claude/(?:rules|skills|CLAUDE\.md)|\.cursor/(?:rules|skills)/"
    r"|\.gemini/skills/|\.agents/skills/"
)


def _doc_files():
    # root CLAUDE.md（手書き開発コンテキスト）も走査対象に含める — 開発文書にも
    # stale パスは混入しうる（spec §7）。plugin/AGENTS.md は rules 真ソース由来の
    # 既存 stale 参照を含むため対象外（rules 内容の再編は issue #6 / スコープ外）。
    return [README, REPO / "CLAUDE.md"] + sorted(GUIDES.glob("*.md"))


def test_no_legacy_distribution_refs_in_docs():
    offenders = []
    for p in _doc_files():
        for i, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
            if _LEGACY.search(line):
                offenders.append(f"{p.relative_to(REPO)}:{i}: {line.strip()}")
    assert not offenders, "legacy submodule/setup.sh refs remain:\n" + "\n".join(offenders)


def test_readme_covers_cc_install_and_freeze():
    text = README.read_text(encoding="utf-8")
    # Claude Code is the (only) supported install path
    assert "/plugin marketplace add rkawaishi/workato-toolkit" in text
    assert "/plugin install workato-toolkit@workato-toolkit" in text
    # non-CC editors are explicitly on hold, with no active install steps advertised
    assert "on hold" in text.lower()
    assert "codex plugin marketplace add" not in text
    # security defense-in-depth is documented (editor-agnostic hardening stays)
    assert "permissions" in text and "deny" in text
    assert ".codexignore" in text
