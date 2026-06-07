#!/usr/bin/env python3
"""sync_derived.py — Generate per-editor derived files from canonical shared source.

Canonical source (hand-edited):
    rules/*.md   -> rules/*.mdc  (Cursor; per-rule alwaysApply:false)
                 -> rules/workato-project.mdc  (Cursor aggregate, alwaysApply:true)
    agents/*.md  -> agents/*.toml  (Codex)
    rules/*.md   -> CLAUDE.md / AGENTS.md / GEMINI.md  (always-on context)

Reduced from the legacy scripts/sync_agents.py: skills are a single shared
tree here (migrated in P3b), so per-editor skill generation is gone — only
rules, the agent, and context files are derived.

Run from repo root:  python3 scripts/sync_derived.py
CI (sync-check.yml) runs this then `git diff --exit-code` to detect drift.
"""
from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
RULES_DIR = REPO_ROOT / "rules"
AGENTS_DIR = REPO_ROOT / "agents"
SKILLS_DIR = REPO_ROOT / "skills"


# ---- pure helpers: copied verbatim from
#      /Users/ryotaro/workspace/workato-dev-kit/scripts/sync_agents.py ----

def split_frontmatter(text: str) -> tuple[str, str]:
    """Return (frontmatter, body) where both exclude the '---' delimiters.

    The first '---' line opens the frontmatter; the next '---' line closes it.
    If the file does not start with '---', or no closing '---' is found, the
    entire text is treated as body.
    """
    lines = text.splitlines()
    if not lines or lines[0] != "---":
        return "", text
    for i in range(1, len(lines)):
        if lines[i] == "---":
            return "\n".join(lines[1:i]), "\n".join(lines[i + 1 :])
    return "", text


def first_heading(body: str) -> str | None:
    """Return the first '# ...' heading text (without '# '), or None.

    Lines inside fenced code blocks (``` ... ```) are skipped so example
    headings inside code blocks do not match.
    """
    fence = False
    for line in body.splitlines():
        if line.startswith("```"):
            fence = not fence
            continue
        if not fence and line.startswith("# "):
            return line[2:]
    return None


_PATH_LINE_RE = re.compile(r'^  - "(.*)"$')


def extract_paths(fm: str) -> list[str]:
    """Extract glob entries from a Claude rule frontmatter.

    Only lines matching exactly ``  - "..."`` (two leading spaces) are
    considered, which mirrors the legacy bash script.
    """
    out: list[str] = []
    for line in fm.splitlines():
        m = _PATH_LINE_RE.match(line)
        if m:
            out.append(m.group(1))
    return out


def extract_field(fm: str, key: str) -> str | None:
    """Return the first value of ``key: ...`` in *fm*, or None."""
    pattern = re.compile(rf"^{re.escape(key)}: *(.*)$")
    for line in fm.splitlines():
        m = pattern.match(line)
        if m:
            return m.group(1)
    return None


def trim_trailing_newlines(text: str) -> str:
    """Mimic bash command-substitution: strip trailing newlines."""
    return text.rstrip("\n")


_HEADING_RE = re.compile(r"^(#+) ")


def demote_headings(text: str, levels: int = 1) -> str:
    """Increase the heading depth of every Markdown heading by *levels*.

    Lines inside fenced code blocks are left untouched.
    """
    out: list[str] = []
    fence = False
    for line in text.split("\n"):
        if line.startswith("```"):
            fence = not fence
            out.append(line)
            continue
        if not fence:
            m = _HEADING_RE.match(line)
            if m:
                line = ("#" * levels) + line
        out.append(line)
    return "\n".join(out)


def _toml_str(s: str) -> str:
    """Encode *s* as a TOML basic (single-line) string."""
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _known_skill_names() -> set[str]:
    """Return the set of skill directory names under skills/."""
    if not SKILLS_DIR.is_dir():
        return set()
    return {p.name for p in SKILLS_DIR.iterdir() if p.is_dir()}


def _build_codex_slash_pattern(names: set[str]) -> "re.Pattern[str] | None":
    """Build a regex matching ``/<skill>`` references to rewrite to ``$<skill>``.

    Negative lookbehind/lookahead avoid rewriting path-like fragments
    (``<slug>/spec.md`` etc.) — mirrors the legacy sync_agents.py logic.
    """
    if not names:
        return None
    alts = "|".join(re.escape(n) for n in sorted(names, key=len, reverse=True))
    return re.compile(rf"(?<![\w>])/({alts})(?![/.\w])\b")


# ---- rules -> per-rule .mdc (Cursor) ----

def sync_rules_mdc() -> None:
    for src in sorted(RULES_DIR.glob("*.md")):
        text = src.read_text(encoding="utf-8")
        fm, body = split_frontmatter(text)
        desc = first_heading(body)
        if not desc:
            print(f"WARN: no heading in {src.stem}, skipping")
            continue
        globs = ",".join(extract_paths(fm))
        body_trimmed = trim_trailing_newlines(body)
        out = (
            "---\n"
            f"description: {desc}\n"
            f'globs: "{globs}"\n'
            "alwaysApply: false\n"
            "---\n"
            f"{body_trimmed}\n"
        )
        (RULES_DIR / f"{src.stem}.mdc").write_text(out, encoding="utf-8")
        print(f"  ok rules/{src.stem}.mdc")


# ---- rules -> aggregate workato-project.mdc (Cursor always-on) ----

AGGREGATE_DESC = (
    "Project-wide context for the Workato toolkit. "
    "Applies whenever Workato-related files are being edited."
)


def sync_aggregate_mdc() -> None:
    parts = [
        "---",
        f"description: {AGGREGATE_DESC}",
        'globs: ""',
        "alwaysApply: true",
        "---",
        "",
        "<!-- AUTO-GENERATED by scripts/sync_derived.py — DO NOT EDIT MANUALLY.",
        "     Source: rules/*.md -->",
        "",
        "# Workato Toolkit — Always-On Rules",
        "",
    ]
    for src in sorted(RULES_DIR.glob("*.md")):
        _, body = split_frontmatter(src.read_text(encoding="utf-8"))
        parts.append(demote_headings(trim_trailing_newlines(body), levels=1))
        parts.append("")
    (RULES_DIR / "workato-project.mdc").write_text(
        "\n".join(parts) + "\n", encoding="utf-8"
    )
    print("  ok rules/workato-project.mdc (aggregate)")


# ---- agents/*.md -> agents/*.toml (Codex) ----

def sync_agent_toml() -> None:
    slash = _build_codex_slash_pattern(_known_skill_names())
    for src in sorted(AGENTS_DIR.glob("*.md")):
        text = src.read_text(encoding="utf-8")
        fm, body = split_frontmatter(text)
        name = extract_field(fm, "name") or src.stem
        desc = extract_field(fm, "description") or ""
        body_trimmed = trim_trailing_newlines(body)
        if slash is not None:
            desc = slash.sub(r"$\1", desc)
            body_trimmed = slash.sub(r"$\1", body_trimmed)
        # developer_instructions is a TOML literal (single-quote) multiline
        # string, which cannot contain a ''' sequence. No current agent body
        # does, but fail loudly rather than emit malformed TOML if one ever does.
        if "'''" in body_trimmed:
            raise ValueError(
                f"{src.name}: body contains ''' which breaks the TOML literal "
                "string; switch to a basic (\"\"\") string with escaping."
            )
        out = (
            f"name = {_toml_str(name)}\n"
            f"description = {_toml_str(desc)}\n"
            f"developer_instructions = '''\n"
            f"{body_trimmed}\n"
            f"'''\n"
        )
        (AGENTS_DIR / f"{src.stem}.toml").write_text(out, encoding="utf-8")
        print(f"  ok agents/{src.stem}.toml")


# ---- rules -> CLAUDE.md / AGENTS.md / GEMINI.md (always-on context) ----

CONTEXT_INTRO = """\
Workato development toolkit for AI coding agents. The rules below are the
always-on knowledge base for building on Workato (recipes, Workflow Apps,
AI agents, custom connectors). They are delivered automatically: Cursor via
alwaysApply .mdc, Gemini via this GEMINI.md (contextFileName), Claude Code /
Codex via the SessionStart hook (bin/session-start-rules).

Knowledge-base documents (connectors, logic, platform, patterns) are NOT in
this file — fetch them through the docs-overlay MCP tools
`workato_docs_lookup(path)` / `workato_docs_list(prefix)` (org overrides win).
"""


def _context_body() -> str:
    parts = [
        "<!-- AUTO-GENERATED by scripts/sync_derived.py — DO NOT EDIT MANUALLY.",
        "     Source: rules/*.md -->",
        "",
        CONTEXT_INTRO,
    ]
    for src in sorted(RULES_DIR.glob("*.md")):
        _, body = split_frontmatter(src.read_text(encoding="utf-8"))
        parts.append(demote_headings(trim_trailing_newlines(body), levels=1))
        parts.append("")
    return "\n".join(parts)


def sync_context() -> None:
    body = _context_body()
    titles = {
        "CLAUDE.md": "# Workato Toolkit — Claude Code Context",
        "AGENTS.md": "# Workato Toolkit — Agent Context",
        "GEMINI.md": "# Workato Toolkit — Gemini Context",
    }
    for fname, title in titles.items():
        (REPO_ROOT / fname).write_text(title + "\n\n" + body + "\n", encoding="utf-8")
        print(f"  ok {fname}")


def main() -> None:
    sync_rules_mdc()
    sync_aggregate_mdc()
    sync_agent_toml()
    sync_context()


if __name__ == "__main__":
    main()
