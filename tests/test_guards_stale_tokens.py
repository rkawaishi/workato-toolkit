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


# --- CC-only support-claim sweep (issue #11) ---
# Editor names may appear in shipped content ONLY as freeze/constraint
# statements ("frozen", "on hold", "Claude Code only", ...), never as active
# support claims ("works the same in every editor", per-editor how-tos).
# Also catch token-free multi-editor phrasings ("per editor", "your
# editor's", ...) — review found claims that name no editor at all.
# Editor names are matched case-sensitively ("cursor management" is SDK
# pagination vocabulary); the phrase patterns are case-insensitive.
EDITOR_TOKEN = re.compile(
    r"\b(Cursor|Codex|Gemini)\b"
    r"|(?i:\b(?:every|per|each|any) editor\b|your editor'?s?\b)"
)
ALLOWED_CONTEXT = re.compile(
    r"frozen|on hold|only (officially )?support|Claude Code only"
    r"|Claude Code is the only|cannot run|no Chrome MCP|not maintained"
    r"|revival|not verified|do(es)? not have",
    re.IGNORECASE,
)
EXCEPTIONS = {
    # Workato MCP servers are consumed BY these AI clients — a product fact
    # about Workato's MCP feature, not an editor-support claim for this plugin.
    ("plugin/skills/workato-create/references/genie.md", "Claude Desktop, Cursor, ChatGPT"),
    ("plugin/skills/workato-create/references/mcp-server.md", "Claude Desktop, Cursor, ChatGPT"),
}


def _shipped_prose_files():
    return (
        sorted((REPO / "plugin" / "skills").rglob("*.md"))  # incl. references/
        + sorted((REPO / "plugin" / "docs" / "guides").glob("*.md"))
        + sorted((REPO / "plugin" / "rules").glob("*.md"))
        + [REPO / "plugin" / "agents" / "workato-builder.md"]
    )


def test_no_multi_editor_support_claims_in_shipped_content():
    offenders = []
    for p in _shipped_prose_files():
        rel = str(p.relative_to(REPO))
        for i, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
            if not EDITOR_TOKEN.search(line):
                continue
            if ALLOWED_CONTEXT.search(line):
                continue
            if any(rel == f and s in line for f, s in EXCEPTIONS):
                continue
            offenders.append(f"{rel}:{i}: {line.strip()}")
    assert not offenders, (
        "multi-editor support claims in shipped content (rephrase as a "
        "freeze/constraint statement, or add an EXCEPTIONS entry with a "
        "reason):\n" + "\n".join(offenders)
    )


def test_no_per_editor_quickstarts_shipped():
    quickstarts = {p.name for p in (REPO / "plugin" / "docs" / "guides").glob("quickstart-*.md")}
    assert quickstarts == {"quickstart-claude-code.md"}, (
        f"only the Claude Code quickstart ships; found {quickstarts}"
    )


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


def test_no_bare_learned_patterns_path_in_guides():
    """learned-patterns.md lives in the workspace overlay (org/docs/) — a bare
    docs/learned-patterns.md reference points at the read-only bundle (#21)."""
    offenders = []
    for p in sorted(GUIDES.glob("*.md")):
        for i, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
            if re.search(r"(?<!org/)\bdocs/learned-patterns\.md", line):
                offenders.append(f"{p.name}:{i}: {line.strip()}")
    assert not offenders, "bare docs/learned-patterns.md refs:\n" + "\n".join(offenders)
