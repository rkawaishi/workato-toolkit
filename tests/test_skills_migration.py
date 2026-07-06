import re
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SKILLS = REPO / "skills"

EXPECTED_SKILLS = {
    "analyze", "auto-learn", "catalog", "clarify", "create-connector",
    "create-genie", "create-recipe", "create-workflow-app", "deploy-project",
    "design", "implement", "issue-api-keys", "learn-pattern", "learn-recipe",
    "onboard", "ping", "plan", "pull-project", "push-project",
    "setup-workspace", "spec", "sync-connectors", "tasks", "validate-recipe",
}

# @-prefixed doc references that must be gone after the rewrite (READ refs → MCP).
FORBIDDEN = re.compile(r"@(?:docs|org/docs|projects/docs)/")

# Skills that DO consult the docs knowledge base and therefore must mention the MCP tool.
SKILLS_WITH_DOC_REFS = {
    "analyze", "auto-learn", "create-connector", "create-genie", "create-recipe",
    "create-workflow-app", "deploy-project", "issue-api-keys", "learn-recipe",
    "plan", "push-project", "tasks",
}


def _skill_files():
    return {p.parent.name: p for p in SKILLS.rglob("SKILL.md")}


def test_all_skills_present():
    found = set(_skill_files().keys())
    assert found == EXPECTED_SKILLS, f"missing/extra: {EXPECTED_SKILLS ^ found}"


def test_each_skill_has_frontmatter():
    for name, p in _skill_files().items():
        text = p.read_text(encoding="utf-8")
        assert text.startswith("---\n"), f"{name}: no frontmatter start"
        assert "description:" in text.split("---", 2)[1], f"{name}: no description"


def test_no_at_prefixed_doc_refs_remain():
    offenders = []
    for name, p in _skill_files().items():
        for i, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
            if FORBIDDEN.search(line):
                offenders.append(f"{name}/SKILL.md:{i}: {line.strip()}")
    assert not offenders, "remaining @doc refs:\n" + "\n".join(offenders)


def test_no_plain_docs_read_refs_in_learn_recipe():
    # learn-recipe's READ instructions must be converted; its WRITE targets (org/docs) may remain.
    text = (SKILLS / "learn-recipe" / "SKILL.md").read_text(encoding="utf-8")
    assert "consult both `docs/connectors/" not in text, "learn-recipe L93 read not converted"
    assert "Read the kit's `docs/" not in text, "learn-recipe L21 read not converted"
    assert "Read the kit-side `docs/" not in text, "learn-recipe L98 read not converted"
    # positive guard: the 3 converted reads must invoke the MCP lookup tool
    assert text.count("workato_docs_lookup") >= 3, "learn-recipe should call workato_docs_lookup for its 3 converted reads"


def test_doc_consuming_skills_mention_mcp_tool():
    files = _skill_files()
    for name in SKILLS_WITH_DOC_REFS:
        text = files[name].read_text(encoding="utf-8")
        assert "workato_docs_lookup" in text or "workato_docs_list" in text, \
            f"{name}: rewritten skill must reference an MCP docs tool"


# ---- P3c T9: rules are delivered always-on and docs via MCP, so skills must
#      not reference any @.claude/ path (rules, CLAUDE.md, skills) — none of
#      those resolve under plugin distribution.
_CLAUDE_PATH_REF = re.compile(r"@\.claude/")


def test_no_claude_rules_path_refs():
    offenders = []
    for name, p in _skill_files().items():
        for i, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
            if _CLAUDE_PATH_REF.search(line):
                offenders.append(f"{name}/SKILL.md:{i}: {line.strip()}")
    assert not offenders, "remaining @.claude/ refs:\n" + "\n".join(offenders)


def test_rules_referenced_by_name():
    text = (SKILLS / "create-recipe" / "SKILL.md").read_text(encoding="utf-8")
    assert "`workato-recipe-format`" in text
    assert "always-on" in text


# ---- P4: learning-WRITE redesign ----
# Skills must never instruct writing into the plugin's bundled (read-only) kit
# `docs/connectors/`. Allowed connector write targets are the workspace repo:
#   org/docs/connectors/   (pre-built + org knowledge)
#   connectors/docs/       (custom connectors)
# A bare `docs/connectors/` (not prefixed by `org/`) is a regression.
_BARE_KIT_CONNECTOR_PATH = re.compile(r"(?<!org/)docs/connectors/")

_WRITE_REDESIGNED_SKILLS = {"sync-connectors", "auto-learn"}


def test_sync_skills_write_to_org_docs():
    files = _skill_files()
    for name in _WRITE_REDESIGNED_SKILLS:
        text = files[name].read_text(encoding="utf-8")
        offenders = [
            f"{name}/SKILL.md:{i}: {line.strip()}"
            for i, line in enumerate(text.splitlines(), 1)
            if _BARE_KIT_CONNECTOR_PATH.search(line)
        ]
        assert not offenders, "bare kit docs/connectors/ refs:\n" + "\n".join(offenders)
        assert "org/docs/connectors/" in text, f"{name}: must write to org/docs/connectors/"


# These learning skills consult the kit knowledge base and must do so via the MCP tool.
_MCP_REQUIRED_LEARNING_SKILLS = {
    "learn-recipe", "learn-pattern", "sync-connectors", "auto-learn",
}


def test_no_bare_kit_connector_path_in_any_skill():
    # No skill (read OR write) may name a bare kit `docs/connectors/` path — those
    # resolve to the read-only bundled docs and must go through the MCP lookup or
    # the workspace org/docs/ overlay instead. Repo-wide: /create-recipe and
    # /onboard also encode connector-knowledge writes, so guard every skill.
    offenders = []
    for name, p in _skill_files().items():
        for i, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
            if _BARE_KIT_CONNECTOR_PATH.search(line):
                offenders.append(f"{name}/SKILL.md:{i}: {line.strip()}")
    assert not offenders, "bare kit docs/connectors/ refs:\n" + "\n".join(offenders)


# A bundled doc tree is reached via the docs-overlay MCP (paths have NO `docs/`
# prefix, e.g. workato_docs_lookup("patterns/recipe-patterns/_index.md")). A bare
# `docs/<tree>/` in a skill is a local read of the read-only plugin docs, which do
# not exist in the workspace under plugin distribution. `org/docs/` (overlay) and
# `projects/docs/` (legacy, read-only) are the allowed local locations.
_BARE_KIT_DOC_PATH = re.compile(
    r"(?<!org/)(?<!projects/)docs/(?:connectors|patterns|logic|platform|guides)/"
)


def test_no_bare_kit_doc_read_in_any_skill():
    # Generalizes test_no_bare_kit_connector_path_in_any_skill to every bundled
    # doc tree (patterns/logic/platform/guides), so a local read of e.g.
    # `docs/patterns/recipe-patterns/` is caught the same way as `docs/connectors/`.
    offenders = []
    for name, p in _skill_files().items():
        for i, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
            if _BARE_KIT_DOC_PATH.search(line):
                offenders.append(f"{name}/SKILL.md:{i}: {line.strip()}")
    assert not offenders, (
        "bare kit docs/<tree>/ refs (read via workato_docs_lookup instead):\n"
        + "\n".join(offenders)
    )


def test_learning_skills_reference_mcp_tool():
    files = _skill_files()
    for name in _MCP_REQUIRED_LEARNING_SKILLS:
        text = files[name].read_text(encoding="utf-8")
        assert "workato_docs_lookup" in text or "workato_docs_list" in text, \
            f"{name}: must read kit docs via the docs-overlay MCP tool"


def test_learning_skills_have_no_submodule_language():
    files = _skill_files()
    for name in _MCP_REQUIRED_LEARNING_SKILLS:
        text = files[name].read_text(encoding="utf-8")
        assert "submodule" not in text, f"{name}: stale 'submodule' wording"
        assert "cd kit" not in text, f"{name}: stale 'cd kit' git step"
