"""Skill guards (plugin/skills/): presence, frontmatter, and the MCP-reference /
bare-path sweeps that keep skill bodies on the docs-overlay read convention."""
import re

from conftest import SKILLS

EXPECTED_SKILLS = {
    "analyze", "auto-learn", "catalog", "deploy-project", "diagnose-jobs",
    "implement", "inspect-env", "issue-api-keys", "learn-pattern", "learn-recipe",
    "onboard", "ping", "plan", "pull-project", "push-project",
    "run-recipes", "setup-workspace", "spec", "sync-connectors", "tasks",
    "validate-recipe", "workato-create",
}

# @-prefixed doc references that must be gone after the rewrite (READ refs → MCP).
FORBIDDEN = re.compile(r"@(?:docs|org/docs|projects/docs)/")

# Skills that DO consult the docs knowledge base and therefore must mention the MCP tool.
SKILLS_WITH_DOC_REFS = {
    "analyze", "auto-learn", "deploy-project", "diagnose-jobs", "inspect-env",
    "issue-api-keys", "learn-recipe", "plan", "push-project", "tasks",
    "workato-create",
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


# ---- /run-recipes (operations-lifecycle spec 2026-07-07 §7; S6-1〜S6-4) ----

def _run_recipes_text():
    return (SKILLS / "run-recipes" / "SKILL.md").read_text(encoding="utf-8")


def test_run_recipes_uses_helper_not_raw_cli():
    """S6-1: 実行はヘルパー `recipes start/stop`（dev ガード内蔵）経由。
    raw CLI の `workato recipes start|stop` を手順として書かない。"""
    text = _run_recipes_text()
    assert "workato-api.py recipes list" in text, "status must go through the helper"
    assert re.search(r"workato-api\.py recipes (start|stop)", text), \
        "start/stop must go through the helper (built-in dev guard)"
    # ヘルパー行は "workato-api.py recipes start" であり、この部分文字列
    # "workato recipes start" を含まないので、素朴なパターンで誤検知しない。
    offenders = [
        line.strip() for line in text.splitlines()
        if re.search(r"\bworkato recipes (start|stop)\b", line)
    ]
    assert not offenders, "raw CLI start/stop in run-recipes:\n" + "\n".join(offenders)


def test_run_recipes_has_prod_boundary_section():
    """S6-3 AC: test/prod プロファイル検知時は実行せず案内へ切替える。案内には
    レシピ特定情報 + **URL** + hotfix 経路が揃うこと（hook は最終防衛線であって UX ではない）。"""
    text = _run_recipes_text()
    assert "-dev" in text, "must resolve/check the profile suffix before any mutation"
    assert re.search(r"\bUI\b", text), "prod boundary guidance must point at the Workato UI"
    assert "URL" in text, "S6-3 AC: guidance must include the direct recipe URL(s)"
    assert re.search(r"recipe name\(s\) and ID\(s\)|recipe ID", text), \
        "S6-3 AC: guidance must carry recipe-identifying info"
    assert "hotfix" in text.lower(), "prod boundary guidance must include the hotfix path"
    assert "/deploy-project" in text, "the sanctioned fix path for test/prod is deploy"


def test_run_recipes_connects_start_failures_to_diagnose():
    """S6-4: 起動エラー専用節があり、エラー本文をそのまま示し、盲目的リトライを
    禁じ、/diagnose-jobs（起動エラー入口）へ接続する。"""
    text = _run_recipes_text()
    assert re.search(r"^#+ .*Start failures", text, re.MULTILINE), \
        "S6-4 needs its own section — a stray /diagnose-jobs mention elsewhere is not enough"
    assert "verbatim" in text, "S6-4: show the start error output verbatim"
    assert re.search(r"not retry blindly|Do not retry", text), "S6-4: no blind retries"
    assert "/diagnose-jobs" in text


def test_run_recipes_restart_orders_stop_then_start():
    """S6-1 AC: restart は stop → start の順序保証つき。操作後は状態を再表示する。"""
    text = _run_recipes_text()
    assert "stop → start" in text or "stop then start" in text
    assert re.search(r"Re-run `?status`?", text), \
        "S6-1 AC: after any operation the resulting state is re-displayed"


# ---- /diagnose-jobs (operations-lifecycle spec 2026-07-07 §7; S7-1〜S7-4, S6-4, S5-2) ----

def _diagnose_jobs_text():
    return (SKILLS / "diagnose-jobs" / "SKILL.md").read_text(encoding="utf-8")


def test_diagnose_jobs_fix_cycle_is_dev_only():
    """S7-2/§5: 修正サイクルは dev 限定 — test/prod には触れず、修正の反映は
    常に deploy 経由。--no-fix で診断・提案のみに抑制できる。"""
    text = _diagnose_jobs_text()
    assert "-dev" in text, "must resolve/check the profile before the fix loop"
    assert "--no-fix" in text
    assert "/deploy-project" in text, "test/prod fixes travel via deploy, never directly"


def test_diagnose_jobs_collects_per_recipe_via_helper():
    """S7-1: ヘルパーの jobs list はレシピ単位（--recipe-id 必須）。フォルダ対象は
    recipes list --folder-id でレシピ列挙してから照会する。"""
    text = _diagnose_jobs_text()
    assert "workato-api.py recipes list" in text and "--folder-id" in text
    assert "workato-api.py jobs list" in text and "--recipe-id" in text
    assert "workato-api.py jobs get" in text


def test_diagnose_jobs_has_start_error_entrance():
    """S6-4: 入口は失敗ジョブだけでなく起動エラーも — ジョブが 1 件も無くても
    診断に入れ、起動成功→テスト投入の順序を保証する。"""
    text = _diagnose_jobs_text()
    assert re.search(r"^#+ .*\bStart errors?\b", text, re.MULTILINE), \
        "start-error entrance needs its own section"
    assert re.search(r"no jobs", text, re.IGNORECASE), \
        "must state it works even when zero jobs exist"
    assert re.search(r"start success", text, re.IGNORECASE), \
        "S6-4 AC: entrance (b) exits on start success, then proceeds to injection"


def test_diagnose_jobs_loop_discipline():
    """S7-2 AC: 周回記録・同一修正の再提案禁止・上限（既定 5 周）・途中の再分類
    停止・green での commit 促し。"""
    text = _diagnose_jobs_text()
    assert re.search(r"same fix twice|再提案", text), "no-same-fix-twice rule missing"
    assert re.search(r"\b5\b.*(iteration|round|loop)|(iteration|round|loop).*\b5\b",
                     text, re.IGNORECASE), "iteration cap (default 5) missing"
    assert re.search(r"one line per iteration|per iteration", text, re.IGNORECASE), \
        "S7-2 AC: per-iteration trail missing"
    assert "git commit" in text, "S7-2 AC: commit prompt on green missing"
    assert re.search(r"mid-loop|flips to", text), \
        "S7-2: mid-loop reclassification must stop the loop"


def test_diagnose_jobs_verifies_values_not_just_status():
    """S5-2 AC: 「ジョブ成功 = 合格」にしない — 値まで照合し、期待値が無ければ
    ユーザに確認してから照合する（勝手に green 宣言しない）。"""
    text = _diagnose_jobs_text()
    assert re.search(r"output values", text, re.IGNORECASE)
    assert re.search(r"never self-declare green|ask the user for them", text), \
        "S5-2 AC: with no expected values, ask — do not self-pass"


def test_diagnose_jobs_flags_unreclaimed_failed_jobs():
    """S7-3: green で終わらせない — 修正前に失敗したジョブ（未回収の業務データ）を
    必ず指摘し、再実行の段取り + 非冪等（二重処理）警告を出す。"""
    text = _diagnose_jobs_text()
    assert re.search(r"failed before|before the fix", text, re.IGNORECASE)
    assert re.search(r"rerun|re-run", text, re.IGNORECASE)
    assert re.search(r"idempoten|double-process", text, re.IGNORECASE), \
        "S7-3 AC: warn about double-processing on rerun"


def test_diagnose_jobs_ui_handover_roundtrip():
    """S7-4: 直せないものは診断結果（疑わしい箇所）を添えて UI 修正へ引き渡し、
    完了後 /pull-project → diff → commit → /learn-recipe。引き渡しから pull 完了
    まで push を封じる（人の修正の上書き防止）。"""
    text = _diagnose_jobs_text()
    assert "/pull-project" in text
    assert "/learn-recipe" in text
    assert re.search(r"diagnosis attached", text), \
        "S7-4 AC: handover carries the diagnosis (suspected steps/settings)"
    assert re.search(r"until the pull completes", text), \
        "S7-4 AC: push frozen from handover until the pull completes"
    assert re.search(r"diff", text), "S7-4: present what the human changed"


def test_diagnose_jobs_tail_is_bounded():
    """S7-1 AC: tail は常駐監視ではない — セッション内・明示的な終了条件つき
    （ヘルパーの --max-iterations を使う）。"""
    text = _diagnose_jobs_text()
    assert "jobs tail" in text
    assert "--max-iterations" in text


# ---- /inspect-env (operations-lifecycle spec 2026-07-07 §7; S8-1, S8-2, S8-5/6 検証, S7-3 prod 側) ----

def _inspect_env_text():
    return (SKILLS / "inspect-env" / "SKILL.md").read_text(encoding="utf-8")


def test_inspect_env_declares_read_only_up_front():
    """スキル冒頭で読取専用を宣言する（S8-2 AC）。"""
    text = _inspect_env_text()
    head = "\n".join(text.splitlines()[:20])
    assert re.search(r"read[- ]only", head, re.IGNORECASE), \
        "read-only declaration must appear at the top of the skill"


def test_inspect_env_code_blocks_contain_no_write_commands():
    """§7 全走査ガード: コードブロックに書込系コマンド
    （push / recipes start・stop / deploy run / sdk push / properties set）を含まない。"""
    text = _inspect_env_text()
    blocks = re.findall(r"```(?:bash|sh)?\n(.*?)```", text, re.DOTALL)
    assert blocks, "inspect-env should carry runnable read commands"
    write_cmd = re.compile(
        r"\bworkato push\b|\bsdk push\b|recipes (start|stop)\b"
        r"|deploy run\b|properties set\b|--restart-recipes"
    )
    offenders = [
        line.strip()
        for block in blocks for line in block.splitlines()
        if write_cmd.search(line)
    ]
    assert not offenders, "write commands in inspect-env code blocks:\n" + "\n".join(offenders)


def test_inspect_env_diffs_via_scratch_pull():
    """S8-2: prod/test の定義は scratch（temp copy）へ pull して dev と diff —
    ヘルパーの sdk diff-project（読取専用）を対象プロファイルで使う。"""
    text = _inspect_env_text()
    assert "sdk diff-project" in text
    assert "--profile" in text
    assert re.search(r"temp|scratch", text, re.IGNORECASE)


def test_inspect_env_distinguishes_deploy_success_from_running():
    """S8-1 AC: 「deploy 成功 ≠ 業務が動いている」— レシピ停止中/初ジョブ未達を
    区別して報告する。"""
    text = _inspect_env_text()
    assert re.search(r"deploy succ", text, re.IGNORECASE)
    assert re.search(r"stopped", text, re.IGNORECASE)
    assert re.search(r"first job", text, re.IGNORECASE)


def test_inspect_env_verifies_env_config():
    """S8-5/S8-6 検証: properties の欠落とテーブルのシード状況を環境差として
    検知する（読取可否が未確認の間は人間への確認にフォールバック）。"""
    text = _inspect_env_text()
    assert "properties" in text
    assert re.search(r"Lookup|Data Table", text)


def test_inspect_env_prod_reclaim_and_consent():
    """S7-3 prod 側: 回収対象の失敗ジョブ一覧 + UI 再実行手順（実行は人間）。
    S8-1: prod への合成テストデータ投入は明示合意なしに提案しない。"""
    text = _inspect_env_text()
    assert re.search(r"rerun|re-run", text, re.IGNORECASE)
    assert re.search(r"idempoten|double-process", text, re.IGNORECASE)
    assert re.search(r"explicit consent|explicitly agree", text, re.IGNORECASE)
