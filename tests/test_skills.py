"""Skill guards (plugin/skills/): presence, frontmatter, and the MCP-reference /
bare-path sweeps that keep skill bodies on the docs-overlay read convention."""
import re

from conftest import SKILLS

EXPECTED_SKILLS = {
    "analyze", "auto-learn", "catalog", "deploy-project",
    "implement", "issue-api-keys", "learn-pattern", "learn-recipe",
    "onboard", "ping", "plan", "pull-project", "push-project",
    "setup-workspace", "spec", "sync-connectors", "tasks", "validate-recipe",
    "workato-create",
}

# @-prefixed doc references that must be gone after the rewrite (READ refs → MCP).
FORBIDDEN = re.compile(r"@(?:docs|org/docs|projects/docs)/")

# Skills that DO consult the docs knowledge base and therefore must mention the MCP tool.
SKILLS_WITH_DOC_REFS = {
    "analyze", "auto-learn", "deploy-project", "issue-api-keys", "learn-recipe",
    "plan", "push-project", "tasks", "workato-create",
}


def _skill_files():
    files = {p.parent.name: p for p in SKILLS.rglob("SKILL.md")}
    # 空なら SKILLS パスが壊れている。内容系テストが空振り PASS しないよう即死させる。
    assert files, f"no skills found under {SKILLS} — layout broken?"
    return files


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
    text = (SKILLS / "workato-create" / "references" / "recipe.md").read_text(encoding="utf-8")
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


# --- /workato-create consolidation (issue #18) ---
CREATE_REFERENCES = {"recipe", "genie", "mcp-server", "workflow-app", "connector"}


def _create_dir():
    return SKILLS / "workato-create"


def test_workato_create_has_type_references():
    refs = {p.stem for p in (_create_dir() / "references").glob("*.md")}
    assert refs == CREATE_REFERENCES, f"missing/extra: {CREATE_REFERENCES ^ refs}"


def test_workato_create_router_points_at_every_reference():
    text = (_create_dir() / "SKILL.md").read_text(encoding="utf-8")
    for ref in CREATE_REFERENCES:
        assert f"references/{ref}.md" in text, (
            f"router must route the {ref} subcommand to its reference file"
        )


def test_no_references_to_retired_create_skills():
    """The four create-* skills are gone; nothing shipped may still invoke them."""
    retired = re.compile(r"/create-(recipe|genie|workflow-app|connector)\b")
    offenders = []
    scan = (
        list(SKILLS.rglob("*.md"))
        + list((SKILLS.parent / "docs").rglob("*.md"))
        + list((SKILLS.parent / "rules").glob("*.md"))
        + [SKILLS.parent / "agents" / "workato-builder.md"]
    )
    for p in scan:
        for i, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
            if retired.search(line):
                offenders.append(f"{p.relative_to(SKILLS.parent)}:{i}: {line.strip()}")
    assert not offenders, "retired skill references:\n" + "\n".join(offenders)


def test_create_references_obey_skill_content_guards():
    """references/*.md are skill content: same bare-path prohibitions apply."""
    for ref in CREATE_REFERENCES:
        text = (_create_dir() / "references" / f"{ref}.md").read_text(encoding="utf-8")
        assert not FORBIDDEN.search(text), f"references/{ref}.md has @-prefixed doc refs"
        assert "workato_docs_lookup" in text, (
            f"references/{ref}.md must consult the knowledge base via the MCP"
        )


def test_builder_resolves_references_via_asset_path():
    """workato-builder (a subagent) cannot rely on always-on context or skill
    paths (issue #22); it fetches the generation reference via the MCP."""
    agent = (SKILLS.parent / "agents" / "workato-builder.md").read_text(encoding="utf-8")
    assert "workato_asset_path" in agent, (
        "builder must resolve references/<type>.md via workato_asset_path"
    )


# --- Knowledge-convention single-sourcing (issue #21) ---
LEARNING_FAMILY = {"learn-recipe", "learn-pattern", "auto-learn", "sync-connectors", "onboard"}

# Distinctive header rows of the routing tables that must live ONLY in the
# org-knowledge-overlay rule (re-inlined copies drifted — issue #21).
_ROUTING_TABLE_MARKERS = (
    "| Type of finding | Destination |",
    "| Type of knowledge | Where it lives |",
)


def test_learning_family_defers_to_overlay_rule():
    files = _skill_files()
    for name in LEARNING_FAMILY:
        text = files[name].read_text(encoding="utf-8")
        assert "org-knowledge-overlay" in text, (
            f"{name}: must defer to the org-knowledge-overlay rule by name "
            "instead of re-stating the write/dedup conventions"
        )


def test_routing_tables_only_in_the_rule():
    offenders = []
    scan = list(SKILLS.rglob("*.md")) + list((SKILLS.parent / "docs" / "guides").glob("*.md"))
    for p in scan:
        text = p.read_text(encoding="utf-8")
        for marker in _ROUTING_TABLE_MARKERS:
            if marker in text:
                offenders.append(f"{p.relative_to(SKILLS.parent)}: {marker}")
    assert not offenders, (
        "destination-routing tables re-inlined outside the rule:\n" + "\n".join(offenders)
    )


# --- spec-driven family consolidation (issue #20) ---

def test_spec_absorbs_clarify_and_migrate():
    """/clarify (Open-Questions loop) and /design migrate (legacy DESIGN.md
    conversion) are modes of /spec now — 7 pipeline skills became 5."""
    text = (SKILLS / "spec" / "SKILL.md").read_text(encoding="utf-8")
    assert "Open Questions" in text and "resolve" in text.lower(), (
        "spec must carry the clarification loop"
    )
    assert "migrate" in text and "DESIGN.md" in text, (
        "spec must carry the legacy-DESIGN.md migration mode"
    )


def test_no_references_to_retired_sdd_skills():
    retired = re.compile(r"/(clarify|design)\b")
    offenders = []
    scan = (
        list(SKILLS.rglob("*.md"))
        + list((SKILLS.parent / "docs").rglob("*.md"))
        + list((SKILLS.parent / "rules").glob("*.md"))
        + list((SKILLS.parent / "templates").glob("*"))  # templates ship too
        + [SKILLS.parent / "agents" / "workato-builder.md"]
    )
    for p in scan:
        for i, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
            if retired.search(line):
                offenders.append(f"{p.relative_to(SKILLS.parent)}:{i}: {line.strip()}")
    assert not offenders, "retired /clarify //design references:\n" + "\n".join(offenders)


def test_kind_tag_registry_lives_only_in_tasks():
    """The tag -> owning-skill registry is defined once (issue #20: three
    divergent copies had already drifted on [connection])."""
    owners = [p.parent.name for p in SKILLS.rglob("SKILL.md")
              if "| Tag | Owning skill" in p.read_text(encoding="utf-8")]
    assert owners == ["tasks"], f"tag registry must live only in tasks, found: {owners}"
    implement = (SKILLS / "implement" / "SKILL.md").read_text(encoding="utf-8")
    assert "| Tag | Skill / action it dispatches to |" not in implement, (
        "implement must reference the /tasks registry, not keep its own copy"
    )


def test_plan_template_conventions_match_the_rules():
    text = (SKILLS / "plan" / "SKILL.md").read_text(encoding="utf-8")
    assert ".data_table.json" not in text, (
        "plan template must use *.workato_db_table.json (matches the "
        "workato-project-structure rule and every other consumer)"
    )
    assert "workato_db_table.json" in text
    assert "fnc_" in text, (
        "Recipe Function tasks need the fnc_ filename prefix from the rule"
    )


def test_spec_single_argument_grammar():
    text = (SKILLS / "spec" / "SKILL.md").read_text(encoding="utf-8")
    assert "<project-name> <feature-slug>" not in text, (
        "spec must use the slash form <project>/<NNN>-<slug> like every "
        "downstream skill (single argument grammar)"
    )
