---
status: done
---

# workato-toolkit P3b: Skills Migration + docs-ref → MCP Rewrite Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 旧 `workato-dev-kit` の canonical 20 skills を `workato-toolkit` の共有 `skills/` ツリーへ移植し、skill 本文の docs 知識ベース参照（`@docs/` `@org/docs/` `@projects/docs/` と一部の素 `docs/` 読取指示）を **docs-overlay MCP のツール呼び出し（`workato_docs_lookup` / `workato_docs_list`）** へ置換する。あわせて、移植済み `docs/` 内部の `@docs/` クロス参照（P3a レビュー follow-up #2）も同じ規約で整理する。

**Architecture:** P2 の docs-overlay MCP は `workato_docs_lookup(path)`（kit docs + project `org/docs/` を **org-wins マージ**して返す）と `workato_docs_list(prefix)`（kit+org の doc パス一覧）を公開している。旧 skills は「`@docs/X` を読む。`@org/docs/X` があればそれも読む（org 勝ち）」という手動 overlay 規約だったが、これは **MCP の `workato_docs_lookup` 1 回**に置き換わる（マージは MCP が内部で行う）。よって本 plan の中心は (1) skills の verbatim 移植、(2) READ 参照のツール呼び出しへの機械的置換、の2点。**WRITE 系（`org/docs/` への書き戻し、auto-learn/sync-connectors の kit docs 書込み）は P4（学習サイクル）スコープなので本 plan では触らない。**

**Tech Stack:** Git / Python 3 / pytest / Markdown

**親 spec:** `superpowers/2026-06-07-workato-toolkit-plugin-distribution-design.md`（§2 鍵ルール「docs 参照は MCP 経由」、§4.5 docs-overlay MCP、§5 初期コンテンツ移植）
**前提 repo:** `/Users/ryotaro/workspace/workato-toolkit`（P1+P2+P3a 完了・main に merge 済。`docs/` 362件・docs-overlay MCP 稼働）。owner=`rkawaishi`。
**移植元 repo:** `/Users/ryotaro/workspace/workato-dev-kit`（凍結。canonical = `framework/claude/skills/`。read-only として参照）。

---

## スコープと決定事項

**本 plan（P3b）の対象:**
- `framework/claude/skills/<name>/SKILL.md`（20件、各 1 ファイル・サブファイルなし）を `workato-toolkit/skills/<name>/SKILL.md` へ verbatim 移植。
- skill 本文の **`@`接頭辞付き doc 参照**（`@docs/` `@org/docs/` `@projects/docs/`）を MCP ツール呼び出しへ置換（READ のみ）。
- skill 本文の **素 `docs/`/`org/docs/` の READ 指示**のうち learn-recipe の明示 3 箇所（L21/L93/L98）を MCP 呼び出しへ置換。
- 移植済み `docs/` 内部の `@docs/` クロス参照 8 ファイル（P3a レビュー #2）を整理。

**本 plan の対象外（明示）:**
- **WRITE 系は触らない（P4）**: `org/docs/<path>` への書き戻し、auto-learn の `docs/connectors/*.md` 追記/集約（L197/L263/L331）、learn-pattern の consolidation（L140/L141）、onboard の populate 記述（L11/L102）。これらは素 `docs/` 表記で、本 plan の `@`-参照テストには掛からない＝自然に P4 へ残る。
- **rules/agents/hooks の移植と派生生成・`sync-check.yml`**（P3c）。`@.claude/rules/...` 参照（例 create-recipe の `@.claude/rules/workato-recipe-format.md`）は rules スコープなので **P3b では触らない**（P3c で扱う）。
- **guides の install 手順書換え**（旧 submodule+setup.sh）= P5。特に `docs/guides/quickstart-cursor.md:242` の `@docs/...` は「旧仕組みの説明」のメタ言及なので **書換え対象外**（P5 のガイド刷新で対応）。

**置換規約（transformation rules）— 全タスク共通:**

| パターン | 置換後 |
|---|---|
| `@docs/<path>` を読む（単一） | 「`workato_docs_lookup` ツールを path `<path>` で呼ぶ（kit + org overlay をマージして返る）」 |
| `@docs/X` + `@org/docs/X`（+ `@projects/docs/...` legacy）の overlay 3点セット | **1 行に集約**：「`workato_docs_lookup` を path `X` で呼ぶ（kit と org をマージ・org 勝ち）」。legacy `@projects/docs/` 行は**削除**（旧 submodule レイアウトの後方互換で、新配布では不要） |
| `@docs/<dir>/` 配下の「関連ファイルを読む」 | 「`workato_docs_list` を prefix `<dir>/` で呼んで該当 doc を探し、`workato_docs_lookup` で取得」 |
| `@docs/connectors/_index.md`（コネクタ特定） | 「`workato_docs_lookup` を path `connectors/_index.md` で呼ぶ」 |
| 素 `docs/<path>` / `org/docs/<path>` の **READ** 指示（learn-recipe のみ） | 「`workato_docs_lookup` を相対 path `<path>` で呼ぶ（kit+org マージ済）」。WRITE 先 `org/docs/<path>` の記述は**そのまま残す** |
| `docs/` 内部のクロス参照 `@docs/Y`（doc 本文中の "See @docs/Y"） | `@` と `docs/` を外し、「`workato_docs_lookup` で `Y` を参照」相当の素パス表記に。MCP 配信時に file-read として誤解されないようにする |

**MCP ツール仕様（P2 `mcp/docs-overlay/server.py` で確認済）:**
- `workato_docs_lookup(path: str) -> str` — path 例 `connectors/slack.md`（`.md` 省略可）。kit+org を org-wins マージ。無ければ `NOT FOUND` 文字列、traversal は `INVALID PATH`。
- `workato_docs_list(prefix: str = "") -> list` — prefix 例 `connectors/`。kit+org の doc 相対パス一覧（sorted/deduped）。

---

## File Structure（P3b で作成/変更）

- `skills/<name>/SKILL.md`（新規 20件）— 移植 + 参照書換え後の canonical skills。
- `tests/test_skills_migration.py`（新規）— 20 skill 存在、frontmatter 妥当性、`@docs/`/`@org/docs/`/`@projects/docs/` の残存ゼロ、`workato_docs_lookup` 言及の存在を検証。**唯一責務: skill 移植 + 参照書換えの完了検証**。
- `docs/{platform,logic,guides}/*.md`（変更 8件）— 内部 `@docs/` クロス参照の整理（quickstart-cursor.md は除外）。
- **変更しない**: `mcp/docs-overlay/`（サーバ無変更）、`docs/` のコネクタ本文（クロス参照整理対象8件以外）、rules/agents/hooks。

---

## Task 1: feature ブランチ作成と前提確認

**Files:** なし

- [ ] **Step 1: 最新 main から feature ブランチを作成**

Run:
```bash
cd /Users/ryotaro/workspace/workato-toolkit
git checkout main && git pull --ff-only
git checkout -b feat/p3b-skills-migration
```
Expected: `feat/p3b-skills-migration` に切り替わる。

- [ ] **Step 2: 移植元 skills の件数を確認**

Run:
```bash
OLD=/Users/ryotaro/workspace/workato-dev-kit
ls -1 "$OLD/framework/claude/skills" | wc -l | tr -d ' '   # expect 20
find "$OLD/framework/claude/skills" -name SKILL.md | wc -l | tr -d ' '  # expect 20
```
Expected: `20` / `20`。違う場合は実測に合わせて報告（BLOCKED ではない）。

---

## Task 2: skills を verbatim 移植（書換え前）

**Files:**
- Create: `skills/<name>/SKILL.md` ×20

- [ ] **Step 1: skills ツリーをコピー**

Run:
```bash
cd /Users/ryotaro/workspace/workato-toolkit
OLD=/Users/ryotaro/workspace/workato-dev-kit
mkdir -p skills
rsync -a --exclude='.DS_Store' "$OLD/framework/claude/skills/" skills/
echo "skills: $(find skills -name SKILL.md | wc -l | tr -d ' ')"   # expect 20
ls -1 skills
```
Expected: `skills: 20`、20 ディレクトリ（analyze, auto-learn, catalog, clarify, create-connector, create-genie, create-recipe, create-workflow-app, design, implement, learn-pattern, learn-recipe, onboard, plan, pull-project, push-project, spec, sync-connectors, tasks, validate-recipe）。

- [ ] **Step 2: コミット（verbatim 移植）**

Run:
```bash
git add skills/
git commit -m "feat(skills): migrate 20 canonical skills verbatim from workato-dev-kit"
```
末尾に `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`。

---

## Task 3: 書換え完了テスト（TDD・先に失敗させる）

**Files:**
- Create: `tests/test_skills_migration.py`

- [ ] **Step 1: 失敗するテストを書く**

`/Users/ryotaro/workspace/workato-toolkit/tests/test_skills_migration.py`:
```python
import re
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SKILLS = REPO / "skills"

EXPECTED_SKILLS = {
    "analyze", "auto-learn", "catalog", "clarify", "create-connector",
    "create-genie", "create-recipe", "create-workflow-app", "design",
    "implement", "learn-pattern", "learn-recipe", "onboard", "plan",
    "pull-project", "push-project", "spec", "sync-connectors", "tasks",
    "validate-recipe",
}

# @-prefixed doc references that must be gone after the rewrite (READ refs → MCP).
FORBIDDEN = re.compile(r"@(?:docs|org/docs|projects/docs)/")

# Skills that DO consult the docs knowledge base and therefore must mention the MCP tool.
SKILLS_WITH_DOC_REFS = {
    "analyze", "auto-learn", "create-connector", "create-genie", "create-recipe",
    "create-workflow-app", "learn-recipe", "plan", "push-project", "tasks",
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


def test_doc_consuming_skills_mention_mcp_tool():
    files = _skill_files()
    for name in SKILLS_WITH_DOC_REFS:
        text = files[name].read_text(encoding="utf-8")
        assert "workato_docs_lookup" in text or "workato_docs_list" in text, \
            f"{name}: rewritten skill must reference an MCP docs tool"
```

- [ ] **Step 2: テストを実行して失敗を確認**

Run:
```bash
cd /Users/ryotaro/workspace/workato-toolkit
python3 -m pytest tests/test_skills_migration.py -v
```
Expected: `test_all_skills_present` と `test_each_skill_has_frontmatter` は PASS（移植済）。`test_no_at_prefixed_doc_refs_remain` / `test_no_plain_docs_read_refs_in_learn_recipe` / `test_doc_consuming_skills_mention_mcp_tool` は FAIL（まだ未書換え）。

- [ ] **Step 3: テストファイルをコミット**

```bash
git add tests/test_skills_migration.py
git commit -m "test(skills): add migration + MCP-ref rewrite verification (failing)"
```
（trailer 付き）

---

## Task 4: 参照書換え バッチ A（単純・少数）

対象 skill: **analyze, auto-learn, create-connector, push-project, tasks**。各々の該当行を「置換規約」に従い書換える。Edit は対象 SKILL.md に対し exact 文字列置換。

**Files:** `skills/{analyze,auto-learn,create-connector,push-project,tasks}/SKILL.md`

- [ ] **Step 1: analyze — L71**

`skills/analyze/SKILL.md` の
```
Confirm @docs/patterns/deployment-guide.md's flow is embedded in tasks:
```
を
```
Confirm the deployment flow (call `workato_docs_lookup` with path `patterns/deployment-guide.md`) is embedded in tasks:
```
に置換。

- [ ] **Step 2: auto-learn — L23 のみ**（L197/263/331 は WRITE 系=P4、触らない）

`skills/auto-learn/SKILL.md` の `@docs/patterns/auto-learn-ui-operations.md` を含む文の
```
See @docs/patterns/auto-learn-ui-operations.md.
```
を
```
See the auto-learn UI operations doc (call `workato_docs_lookup` with path `patterns/auto-learn-ui-operations.md`).
```
に置換。

- [ ] **Step 3: create-connector — L27,28**

`skills/create-connector/SKILL.md` の
```
- @docs/connector-sdk/overview.md — SDK overview and setup pitfalls.
- @docs/connector-sdk/connector-rb.md — connector.rb reference (HTTP method return types, base_uri conventions, normalization helper templates).
```
を
```
- Call `workato_docs_lookup` with path `connector-sdk/overview.md` — SDK overview and setup pitfalls.
- Call `workato_docs_lookup` with path `connector-sdk/connector-rb.md` — connector.rb reference (HTTP method return types, base_uri conventions, normalization helper templates).
```
に置換。

- [ ] **Step 4: push-project — L33**

`skills/push-project/SKILL.md` の
```
- Direct push to test/prod is forbidden; promotion goes through the Deploy feature (@docs/platform/environments.md).
```
を
```
- Direct push to test/prod is forbidden; promotion goes through the Deploy feature (call `workato_docs_lookup` with path `platform/environments.md`).
```
に置換。

- [ ] **Step 5: tasks — L105**

`skills/tasks/SKILL.md` の
```
Follow @docs/patterns/deployment-guide.md's "recipe deployment flow" and always include these tasks:
```
を
```
Follow the "recipe deployment flow" (call `workato_docs_lookup` with path `patterns/deployment-guide.md`) and always include these tasks:
```
に置換。

- [ ] **Step 6: バッチ A の検証とコミット**

Run:
```bash
cd /Users/ryotaro/workspace/workato-toolkit
grep -rn "@docs/\|@org/docs/\|@projects/docs/" skills/analyze skills/auto-learn skills/create-connector skills/push-project skills/tasks || echo "BATCH_A_CLEAN"
```
Expected: `BATCH_A_CLEAN`（auto-learn は L23 のみ対象だが、L197/263/331 は素 `docs/` 表記なのでこの grep には掛からない＝残ってよい）。

```bash
git add skills/analyze skills/auto-learn skills/create-connector skills/push-project skills/tasks
git commit -m "refactor(skills): rewrite doc refs to MCP lookup (batch A: analyze/auto-learn/create-connector/push-project/tasks)"
```
（trailer 付き）

---

## Task 5: 参照書換え バッチ B（create-genie, create-workflow-app, plan）

**Files:** `skills/{create-genie,create-workflow-app,plan}/SKILL.md`

- [ ] **Step 1: create-genie — L40,41,42,205**

`skills/create-genie/SKILL.md`:
- L40-42 の
```
- @docs/connectors/_index.md + relevant connector knowledge
- @docs/platform/agent-studio.md
- @docs/platform/mcp.md
```
を
```
- Call `workato_docs_lookup` with path `connectors/_index.md` + relevant connector knowledge (look each up with `workato_docs_lookup`)
- Call `workato_docs_lookup` with path `platform/agent-studio.md`
- Call `workato_docs_lookup` with path `platform/mcp.md`
```
に置換。
- L205 の
```
Follow @docs/patterns/deployment-guide.md and walk through the deploy:
```
を
```
Follow the deployment guide (call `workato_docs_lookup` with path `patterns/deployment-guide.md`) and walk through the deploy:
```
に置換。

- [ ] **Step 2: create-workflow-app — L20,21,209**

`skills/create-workflow-app/SKILL.md`:
- L20-21 の
```
- @docs/platform/workflow-apps.md — construction patterns, providers, actions
- @docs/patterns/deployment-guide.md — deployment steps and common errors
```
を
```
- Call `workato_docs_lookup` with path `platform/workflow-apps.md` — construction patterns, providers, actions
- Call `workato_docs_lookup` with path `patterns/deployment-guide.md` — deployment steps and common errors
```
に置換。
- L209 の
```
Follow "Workflow App deployment flow" in @docs/patterns/deployment-guide.md and walk through the stages:
```
を
```
Follow the "Workflow App deployment flow" section (call `workato_docs_lookup` with path `patterns/deployment-guide.md`) and walk through the stages:
```
に置換。

- [ ] **Step 3: plan — L44, L66-68（overlay 集約）, L101**

`skills/plan/SKILL.md`:
- L44 の
```
2. For each defined provider, follow @docs/platform/resource-providers.md to detect and run the relevant tool.
```
を
```
2. For each defined provider, follow the resource-providers doc (call `workato_docs_lookup` with path `platform/resource-providers.md`) to detect and run the relevant tool.
```
に置換。
- L66-68 の overlay 3点セット
```
- @docs/patterns/recipe-patterns/_index.md (kit canonical)
- @org/docs/patterns/recipe-patterns/_index.md (org-side, if present)
- @projects/docs/patterns/ (legacy, read-only for backwards compatibility)
```
を **1 行に集約**
```
- Call `workato_docs_lookup` with path `patterns/recipe-patterns/_index.md` (returns kit patterns merged with any org overlay — org wins on conflict)
```
に置換。
- L101 の
```
If the design includes anything that talks to the Workato API (CLI/MCP, API Platform, OEM integration, etc.), always read the comparison table and decision flow in @docs/platform/workato-api-systems.md (to avoid confusing the four "API Client" systems and having to redesign).
```
を
```
If the design includes anything that talks to the Workato API (CLI/MCP, API Platform, OEM integration, etc.), always read the comparison table and decision flow by calling `workato_docs_lookup` with path `platform/workato-api-systems.md` (to avoid confusing the four "API Client" systems and having to redesign).
```
に置換。

- [ ] **Step 4: バッチ B の検証とコミット**

Run:
```bash
grep -rn "@docs/\|@org/docs/\|@projects/docs/" skills/create-genie skills/create-workflow-app skills/plan || echo "BATCH_B_CLEAN"
git add skills/create-genie skills/create-workflow-app skills/plan
git commit -m "refactor(skills): rewrite doc refs to MCP lookup (batch B: create-genie/create-workflow-app/plan)"
```
Expected: `BATCH_B_CLEAN`。（trailer 付き）

---

## Task 6: 参照書換え バッチ C（create-recipe + learn-recipe）

**Files:** `skills/create-recipe/SKILL.md`, `skills/learn-recipe/SKILL.md`

- [ ] **Step 1: create-recipe — L55,56**

```
- Use `@docs/connectors/_index.md` to identify the connector you'll use.
- Read `@docs/connectors/<connector>.md` for available triggers/actions and field info.
```
を
```
- Call `workato_docs_lookup` with path `connectors/_index.md` to identify the connector you'll use.
- Call `workato_docs_lookup` with path `connectors/<connector>.md` for available triggers/actions and field info (it returns kit + any org overlay).
```
に置換。

- [ ] **Step 2: create-recipe — L74,76**

```
1. **Load the environment config**: read .resource-providers.yml. If it doesn't exist, either walk the user through the initial setup or skip to Step 6 (see "Initial setup" in @docs/platform/resource-providers.md).
```
を
```
1. **Load the environment config**: read .resource-providers.yml. If it doesn't exist, either walk the user through the initial setup or skip to Step 6 (see "Initial setup" — call `workato_docs_lookup` with path `platform/resource-providers.md`).
```
に置換。
```
3. **Detect and run tools**: for each defined provider, detect and run the tool following "How skills use this" in @docs/platform/resource-providers.md.
```
を
```
3. **Detect and run tools**: for each defined provider, detect and run the tool following "How skills use this" — call `workato_docs_lookup` with path `platform/resource-providers.md`.
```
に置換。

- [ ] **Step 3: create-recipe — L163（logic dir）**

```
- If logic steps are needed, read the relevant file under `@docs/logic/`.
```
を
```
- If logic steps are needed, call `workato_docs_list` with prefix `logic/` to find the relevant doc, then `workato_docs_lookup` it.
```
に置換。

- [ ] **Step 4: create-recipe — L170-172（overlay 集約）**

```
   - `@docs/patterns/recipe-patterns/_index.md` — kit canonical patterns
   - `@org/docs/patterns/recipe-patterns/_index.md` — org-recorded patterns (if present)
   - `@projects/docs/patterns/` — legacy patterns (read-only for backwards compatibility)
```
を **1 行に集約**
```
   - Call `workato_docs_lookup` with path `patterns/recipe-patterns/_index.md` — returns the kit patterns merged with any org overlay (org wins on conflict).
```
に置換。直前の見出し行 `1. Read the pattern catalog (kit and org sides; org wins on conflicts):` はそのまま残してよい（意味は MCP 呼び出しと整合）。

- [ ] **Step 5: create-recipe — L181,182,183**

```
- `@docs/logic/data-pills.md` for datapill notation.
- The relevant file under `@docs/logic/` for the syntax of any logic step.
- `@docs/patterns/deployment-guide.md` for deploy-time caveats.
```
を
```
- Call `workato_docs_lookup` with path `logic/data-pills.md` for datapill notation.
- The relevant `logic/` doc (use `workato_docs_list` prefix `logic/`, then `workato_docs_lookup`) for the syntax of any logic step.
- Call `workato_docs_lookup` with path `patterns/deployment-guide.md` for deploy-time caveats.
```
に置換。

- [ ] **Step 6: create-recipe — L231**

```
Then, following "Recipe deployment flow" in `@docs/patterns/deployment-guide.md`, walk through the deploy in stages:
```
を
```
Then, following "Recipe deployment flow" (call `workato_docs_lookup` with path `patterns/deployment-guide.md`), walk through the deploy in stages:
```
に置換。

- [ ] **Step 7: learn-recipe — L21（READ→MCP、WRITE 先は残す）**

```
Every write target is `org/docs/<relative-path>`. Read the kit's `docs/<same-relative-path>` first and **skip** anything already documented there (only write differences, corrections, and org-specific additions).
```
を
```
Every write target is `org/docs/<relative-path>`. First call `workato_docs_lookup` with the `<relative-path>` (it returns the kit doc merged with any existing org overlay) and **skip** anything already documented there (only write differences, corrections, and org-specific additions).
```
に置換。（`org/docs/<relative-path>` という WRITE 先表記は残す）

- [ ] **Step 8: learn-recipe — L93**

```
   a. Check whether `provider` and `name` are known (consult both `docs/connectors/<provider>.md` and `org/docs/connectors/<provider>.md`).
```
を
```
   a. Check whether `provider` and `name` are known (call `workato_docs_lookup` with path `connectors/<provider>.md` — it returns kit + org merged).
```
に置換。

- [ ] **Step 9: learn-recipe — L98**

```
6. Read the kit-side `docs/<same-relative-path>` too; if the info is already there, **do not write it**.
```
を
```
6. Call `workato_docs_lookup` with the `<relative-path>` too; if the info is already there, **do not write it**.
```
に置換。

- [ ] **Step 10: バッチ C の検証とコミット**

Run:
```bash
grep -rn "@docs/\|@org/docs/\|@projects/docs/" skills/create-recipe skills/learn-recipe || echo "BATCH_C_CLEAN"
grep -n "consult both \`docs/connectors/\|Read the kit's \`docs/\|Read the kit-side \`docs/" skills/learn-recipe/SKILL.md || echo "LEARN_RECIPE_READS_CONVERTED"
git add skills/create-recipe skills/learn-recipe
git commit -m "refactor(skills): rewrite doc refs to MCP lookup (batch C: create-recipe/learn-recipe)"
```
Expected: `BATCH_C_CLEAN` / `LEARN_RECIPE_READS_CONVERTED`。（trailer 付き）

---

## Task 7: docs/ 内部クロス参照の整理（P3a レビュー #2）

移植済み `docs/` の 8 ファイルに残る `@docs/` クロス参照を整理。**`docs/guides/quickstart-cursor.md:242` は除外**（旧仕組み説明のメタ言及＝P5）。

**Files:** `docs/platform/api-platform.md`, `docs/logic/if-conditions.md`, `docs/platform/environments.md`, `docs/platform/workbot.md`, `docs/platform/mcp.md`, `docs/platform/cli-profiles.md`, `docs/logic/triggers.md`

- [ ] **Step 1: 各クロス参照から `@` を外し MCP 参照表記へ**

各ファイルの `@docs/<Y>` 形式を、「`<Y>` を `workato_docs_lookup` で参照」と読めるよう **`@docs/` 接頭辞を除去**して素の doc パス表記にする。例:

`docs/platform/api-platform.md:46`
```
See `@docs/platform/mcp.md` for details.
```
→
```
See the `platform/mcp.md` doc (look it up via `workato_docs_lookup`) for details.
```

同様に以下を機械的に変換（`@docs/X` → `` `X` doc (via `workato_docs_lookup`) ``。リスト行の `@docs/X — desc` は `` `X` (via `workato_docs_lookup`) — desc ``）:
- `docs/logic/if-conditions.md:65` `@docs/logic/triggers.md`
- `docs/platform/environments.md:86` `@docs/platform/environment-properties.md`
- `docs/platform/environments.md:112` `@docs/platform/cli-profiles.md`
- `docs/platform/environments.md:127-130` `@docs/platform/cli-profiles.md` / `environment-properties.md` / `@docs/patterns/workspace-management.md` / `deployment-guide.md`
- `docs/platform/workbot.md:41,42` `@docs/connectors/workbot-for-slack.md` / `workbot-for-teams.md`
- `docs/platform/workbot.md:48` `@docs/learned-patterns.md`
- `docs/platform/mcp.md:49` `@docs/platform/api-platform.md`
- `docs/platform/cli-profiles.md:25,94` `@docs/platform/environments.md`
- `docs/logic/triggers.md:81` `@docs/logic/if-conditions.md`

- [ ] **Step 2: 検証（quickstart-cursor.md だけ残ること）とコミット**

Run:
```bash
cd /Users/ryotaro/workspace/workato-toolkit
grep -rln "@docs/\|@org/docs/\|@projects/docs/" docs --include='*.md'
```
Expected: `docs/guides/quickstart-cursor.md` の **1 ファイルのみ**（メタ言及・P5 で対応）。他は出ないこと。

```bash
git add docs/
git commit -m "docs: convert internal @docs cross-refs to MCP-lookup phrasing (P3a review #2)"
```
（trailer 付き）

---

## Task 8: 全テスト緑化と push / PR

**Files:** なし（検証 + git/PR）

- [ ] **Step 1: skills 移植テストを実行して PASS**

Run:
```bash
cd /Users/ryotaro/workspace/workato-toolkit
python3 -m pytest tests/test_skills_migration.py -v
```
Expected: 全 PASS。落ちる場合は該当 skill のバッチ Step に戻る。

- [ ] **Step 2: 全スイート実行（回帰なし）**

Run:
```bash
python3 -m pytest -q
```
Expected: test_overlay.py / test_manifests.py / test_docs_migration.py / test_skills_migration.py すべて PASS。

- [ ] **Step 3: 残存 `@`-参照の最終 grep（skills 全体）**

Run:
```bash
grep -rn "@docs/\|@org/docs/\|@projects/docs/" skills || echo "SKILLS_FULLY_CLEAN"
```
Expected: `SKILLS_FULLY_CLEAN`。

- [ ] **Step 4: push**

Run:
```bash
git push -u origin feat/p3b-skills-migration
```

- [ ] **Step 5: PR 作成**

Run:
```bash
gh pr create --base main --head feat/p3b-skills-migration \
  --title "P3b: migrate 20 skills + rewrite doc refs to docs-overlay MCP" \
  --body "$(cat <<'EOF'
## P3b — Skills Migration + docs-ref → MCP Rewrite

旧 `workato-dev-kit` の canonical 20 skills を共有 `skills/` へ移植し、docs 知識ベース参照を docs-overlay MCP（`workato_docs_lookup` / `workato_docs_list`）へ置換。手動 overlay（`@docs/X`+`@org/docs/X`）は MCP の org-wins マージ 1 呼び出しへ集約。

### 変更
- `skills/` 20 skill 移植（verbatim → 参照書換え）
- `@docs/` `@org/docs/` `@projects/docs/` の READ 参照 → MCP ツール呼び出し（legacy `@projects/docs/` は削除）
- learn-recipe の素 `docs/` READ 指示も MCP 化（WRITE 先 `org/docs/` は P4 のため温存）
- `docs/` 内部 `@docs/` クロス参照 7 ファイル整理（P3a review #2。quickstart-cursor.md のメタ言及は P5）

### 対象外（明示）
- WRITE 系（org/docs 書戻し、auto-learn/sync の kit docs 書込み）= P4
- rules/agents/hooks 移植・派生生成・sync-check.yml = P3c
- `@.claude/rules/...` 参照 = P3c
- guides の install 手順刷新（旧 submodule）= P5

### 検証
- `tests/test_skills_migration.py`（20 skill 存在・frontmatter・@-参照ゼロ・MCP 言及）
- `pytest -q` 全 PASS

次: P3c（rules/agents/hooks + 派生生成 + sync-check.yml）。

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```
Expected: PR URL。

- [ ] **Step 6: PR URL を報告し、レビュー/マージ判断を仰ぐ**

---

## Self-Review（plan 作成者によるチェック結果）

**Spec coverage（§2 鍵ルール / §4.5 / §5 の skill 移植 + MCP 参照置換）:**
- skills verbatim 移植 → Task 2 ✅
- `@docs/@org/docs/@projects/docs` READ 参照 → MCP 置換 → Task 4-6（全 9 skill + learn-recipe 素 read）✅、Explore 抽出の全 @-参照 occurrence を網羅（analyze L71 / auto-learn L23 / create-connector L27,28 / create-genie L40-42,205 / create-recipe L55,56,74,76,163,170-172,181-183,231 / create-workflow-app L20,21,209 / plan L44,66-68,101 / push-project L33 / tasks L105）。
- overlay 手動 dual-read の MCP 集約 → Task 5 Step3 / Task 6 Step4 ✅
- docs/ 内部クロス参照（review #2）→ Task 7 ✅（quickstart-cursor のメタ言及は除外し P5 送り）
- 完了の客観検証（@-参照ゼロ・MCP 言及）→ Task 3 のテスト ✅

**Placeholder scan:** 各 Edit に exact old/new テキストを明記。Task 7 の docs/ クロス参照のみ「同型変換」を occurrence リスト + 例で指示（全 occurrence をファイル:行で列挙済み）。TODO/「適切に」なし。

**Type consistency:** 使用ツール名は P2 実装と一致（`workato_docs_lookup(path)` / `workato_docs_list(prefix)`）。テストの禁止パターン正規表現 `@(?:docs|org/docs|projects/docs)/` は対象3種を網羅。`SKILLS_WITH_DOC_REFS` の 10 skill は Task 4-6 で実際に MCP 言及が入る skill と一致（analyze/auto-learn/create-connector/create-genie/create-recipe/create-workflow-app/learn-recipe/plan/push-project/tasks）。

**スコープ境界:** WRITE 系（素 `docs/` 表記）はテストの `@`-grep に掛からず自然に P4 へ残る。`@.claude/rules/...`（create-recipe L168 付近）は `@docs` パターンに掛からないため本 plan のテストを汚さない（P3c 対応）。design/implement/catalog/clarify/spec/sync-connectors/pull-project/validate-recipe/onboard/learn-pattern は @-参照を持たない（または WRITE 系のみ）ため Task 4-6 の書換え対象外で正しい。
