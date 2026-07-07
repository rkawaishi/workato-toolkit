---
status: done
---

# P4 Learning-WRITE Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
>
> **Project convention override:** plans live at `superpowers/` (repo root) and remain **uncommitted**, like the design/prfaq/P1–P3c plans. Do NOT save under `docs/` (that is the bundled, read-only kit docs tree).

**Goal:** Redirect every learning-WRITE skill so it writes only to the project's workspace repo (`org/docs/` and `connectors/docs/`), never to the plugin's bundled read-only `docs/`, and align the always-on `org-knowledge-overlay` rule with plugin-distribution reality.

**Architecture:** Under plugin distribution the kit's `docs/` is bundled inside the plugin cache (read-only) and surfaced through the docs-overlay MCP (`workato_docs_lookup(path)` / `workato_docs_list(prefix)`, org-wins merge). All four learning skills (`/learn-recipe`, `/learn-pattern`, `/sync-connectors`, `/auto-learn`) must (a) READ canonical docs via the MCP tool, and (b) WRITE only to writable workspace locations: `org/docs/connectors/<provider>.md` for pre-built/org connector knowledge (decision 2026-06-07: pre-built spec from `/sync-connectors` & `/auto-learn` also goes to `org/docs/`, unifying with `/learn-recipe`), `org/docs/patterns/...` for patterns, and `connectors/docs/<name>.md` for custom-connector docs (already workspace-side, unchanged). The `org-knowledge-overlay` rule is the canonical source for the always-on knowledge in CLAUDE.md/AGENTS.md/GEMINI.md and the per-rule `.mdc`; editing it requires regenerating derived files via `scripts/sync_derived.py` (drift enforced by `.github/workflows/sync-check.yml`).

**Tech Stack:** Markdown SKILL.md / rule files, Python 3 pytest integrity tests (`tests/`), `scripts/sync_derived.py` derived-file generator.

---

## File Structure

- Modify: `rules/org-knowledge-overlay.md` — canonical always-on rule; remove submodule/symlink-era text, convert read convention to MCP, route sync-skill writes to `org/docs/`.
- Generated (do not hand-edit; produced by the generator): `rules/org-knowledge-overlay.mdc`, `rules/workato-project.mdc` (aggregate), `CLAUDE.md`, `AGENTS.md`, `GEMINI.md`.
- Modify: `skills/learn-recipe/SKILL.md` — duplicate-check via MCP; drop submodule git language.
- Modify: `skills/learn-pattern/SKILL.md` — index read via MCP; drop submodule git language; reword "do not write to docs/".
- Modify: `skills/sync-connectors/SKILL.md` — pre-built writes → `org/docs/connectors/`; existing-doc reads via MCP; git management → workspace repo; custom (`connectors/docs/`) unchanged.
- Modify: `skills/auto-learn/SKILL.md` — Phase 1 read via MCP; Phase 4 append → `org/docs/connectors/`; `--followups` greps `org/docs/connectors/`; git management → workspace repo.
- Modify: `tests/test_skills_migration.py` — add WRITE-target + MCP-mention + no-submodule guards for the learning skills.
- Modify: `tests/test_rules_agents_hooks_migration.py` — add `org-knowledge-overlay` rule plugin-reality guard.

**Out of scope (record as follow-up, do NOT fix here):**
- `skills/auto-learn/SKILL.md` `allowed-tools` lists `mcp__Claude_in_Chrome__*` but the runtime exposes `mcp__claude-in-chrome__*` (lowercase/hyphen). This is a functional mismatch but verifying the correct server name requires the Chrome extension at runtime → defer to P4 runtime verification.
- Any actual content migration of already-collected kit `docs/connectors/*.md` into projects. This plan changes skill behavior only.

---

## Task 1: Test guards for learning-WRITE redesign (RED)

Write the integrity guards first. They MUST fail against the current (unmigrated) skills/rule, proving they bite.

**Files:**
- Modify: `tests/test_skills_migration.py`
- Modify: `tests/test_rules_agents_hooks_migration.py`

- [ ] **Step 1: Add skill WRITE-target + MCP + no-submodule guards**

Append to `tests/test_skills_migration.py` (after the existing `test_rules_referenced_by_name`):

```python
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
```

- [ ] **Step 2: Add the `org-knowledge-overlay` rule plugin-reality guard**

Append to `tests/test_rules_agents_hooks_migration.py` (end of file):

```python
def test_overlay_rule_reflects_plugin_distribution():
    text = (RULES / "org-knowledge-overlay.md").read_text(encoding="utf-8")
    # Reads go through the docs-overlay MCP, not @docs/@org/docs file reads.
    assert "workato_docs_lookup" in text, "overlay rule must describe the MCP read tool"
    # Submodule / symlink era wording must be gone.
    assert "submodule" not in text, "overlay rule still mentions a kit submodule"
    assert "symlink to kit/docs" not in text, "overlay rule still describes the docs/ symlink"
    # The official-spec write target is now org/docs (not the read-only bundled docs/).
    assert "`docs/` (kit) | `/sync-connectors`" not in text, \
        "overlay rule still routes sync skills to the read-only kit docs/"
```

- [ ] **Step 3: Run the new tests to verify they FAIL**

Run: `cd /Users/ryotaro/workspace/workato-toolkit && python3 -m pytest tests/test_skills_migration.py::test_sync_skills_write_to_org_docs tests/test_skills_migration.py::test_learning_skills_reference_mcp_tool tests/test_skills_migration.py::test_learning_skills_have_no_submodule_language tests/test_rules_agents_hooks_migration.py::test_overlay_rule_reflects_plugin_distribution -v`

Expected: all 4 FAIL — `sync-connectors`/`auto-learn` still write bare `docs/connectors/`, `sync-connectors`/`learn-pattern` lack `workato_docs_lookup`, skills still say "submodule"/"cd kit", and the overlay rule still has submodule/symlink/`docs/` (kit) text.

- [ ] **Step 4: Commit the failing guards**

```bash
cd /Users/ryotaro/workspace/workato-toolkit
git add tests/test_skills_migration.py tests/test_rules_agents_hooks_migration.py
git commit -m "test(p4): add learning-WRITE redesign guards (RED)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 2: Migrate `skills/learn-recipe/SKILL.md`

`learn-recipe` already writes to `org/docs/` and already uses `workato_docs_lookup` in places. Only the duplicate-check section (still greps a local kit `docs/` file) and the git-management submodule line need fixing.

**Files:**
- Modify: `skills/learn-recipe/SKILL.md`

- [ ] **Step 1: Convert the Duplicate-check section to the MCP lookup**

Replace this block (currently lines ~102–108):

```markdown
## Duplicate check

Before writing, grep both files for the same content:
- The destination `org/docs/<path>.md`
- The corresponding kit-side `docs/<same-path>.md`

- The kit already has field info for the same action → add only the diff (org-specific fields or corrections).
- The same rule already exists → skip.
```

with:

```markdown
## Duplicate check

Before writing, compare against what already exists:
- The destination `org/docs/<path>.md` (read it directly — it is in the workspace repo).
- The kit canonical doc, via `workato_docs_lookup("<path>")` (it returns the bundled kit doc merged with any org overlay).

- The kit already has field info for the same action → add only the diff (org-specific fields or corrections).
- The same rule already exists → skip.
```

- [ ] **Step 2: Fix the git-management submodule language**

Replace this block (currently lines ~150–160):

```markdown
## Git management

Writes happen in the workspace repository, under `org/docs/` and `projects/<name>/specs/`:

```bash
cd <workspace-root>
git add org/docs/ projects/<name>/specs/
git commit -m "docs(org): learn from <project-name> recipes"
```

**Do not commit to the kit submodule (`kit/`).** When you accumulate general findings worth upstreaming, open a separate PR against the kit repository.
```

with:

```markdown
## Git management

Writes happen in the workspace repository, under `org/docs/` and `projects/<name>/specs/`:

```bash
cd <workspace-root>
git add org/docs/ projects/<name>/specs/
git commit -m "docs(org): learn from <project-name> recipes"
```

**Never write to the plugin's bundled `docs/` — it is read-only.** When you accumulate general findings worth upstreaming into the kit, open a separate PR against the `workato-toolkit` repository.
```

- [ ] **Step 3: Run the learn-recipe-relevant guards**

Run: `cd /Users/ryotaro/workspace/workato-toolkit && python3 -m pytest tests/test_skills_migration.py -k "learn_recipe or learning_skills or no_plain_docs" -v`

Expected: PASS (learn-recipe now has no `submodule`/`cd kit`, still references `workato_docs_lookup`, existing `test_no_plain_docs_read_refs_in_learn_recipe` still green).

- [ ] **Step 4: Commit**

```bash
cd /Users/ryotaro/workspace/workato-toolkit
git add skills/learn-recipe/SKILL.md
git commit -m "docs(p4): learn-recipe duplicate-check via MCP, drop submodule git steps

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 3: Migrate `skills/learn-pattern/SKILL.md`

`learn-pattern` writes to `org/docs/patterns/recipe-patterns/` (correct). It still reads the kit canonical `_index.md` via a plain local path, mentions the submodule in git management, and tells the user "do not write to docs/" in submodule terms.

**Files:**
- Modify: `skills/learn-pattern/SKILL.md`

- [ ] **Step 1: Convert the existing-pattern survey to the MCP lookup**

Replace this block (currently lines ~22–28):

```markdown
First survey existing patterns (read kit canonical and org sides; org wins on conflicts):
- `docs/patterns/recipe-patterns/_index.md` — kit canonical, generic patterns.
- `org/docs/patterns/recipe-patterns/_index.md` — org-recorded patterns (if present).
- `projects/docs/patterns/_index.md` — legacy org-domain patterns (if present; read-only for backwards compatibility).
```

with:

```markdown
First survey existing patterns (kit canonical merged with the org side; org wins on conflicts):
- `workato_docs_lookup("patterns/recipe-patterns/_index.md")` — returns the bundled kit index merged with any `org/docs/` overlay.
- `projects/docs/patterns/_index.md` — legacy org-domain patterns (if present; read it directly — read-only, for backwards compatibility).
```

- [ ] **Step 2: Fix the index-creation reference**

Replace this line (currently line ~128):

```markdown
If the file doesn't exist, create it using the same format as `docs/patterns/recipe-patterns/_index.md` (kit canonical).
```

with:

```markdown
If the file doesn't exist, create it using the same format as the kit canonical index (fetch it via `workato_docs_lookup("patterns/recipe-patterns/_index.md")`).
```

- [ ] **Step 3: Reword the "Do not write to" block**

Replace this block (currently lines ~139–143):

```markdown
**Do not write to**:
- `docs/patterns/recipe-patterns/` (kit canonical, read-only).
- `projects/docs/patterns/` (legacy; existing files are read-only. New writes consolidate into the org side).

When valuable generic patterns accumulate for potential upstreaming, open a separate PR against the kit repository (out of scope here).
```

with:

```markdown
**Do not write to**:
- The plugin's bundled `docs/patterns/recipe-patterns/` (kit canonical, read-only — surfaced via the MCP lookup, never writable from a project).
- `projects/docs/patterns/` (legacy; existing files are read-only. New writes consolidate into the org side).

When valuable generic patterns accumulate for potential upstreaming, open a separate PR against the `workato-toolkit` repository (out of scope here).
```

- [ ] **Step 4: Fix the git-management submodule line**

Replace this block (currently lines ~152–162):

```markdown
## Git management

The write target is in the workspace repository's `org/docs/patterns/recipe-patterns/` (outside the kit submodule):

```bash
cd <workspace-root>
git add org/docs/patterns/recipe-patterns/
git commit -m "docs(org): record pattern <pattern-name>"
```

**Do not commit to the kit submodule (`kit/`).**
```

with:

```markdown
## Git management

The write target is in the workspace repository's `org/docs/patterns/recipe-patterns/`:

```bash
cd <workspace-root>
git add org/docs/patterns/recipe-patterns/
git commit -m "docs(org): record pattern <pattern-name>"
```

**Never write to the plugin's bundled `docs/` — it is read-only.**
```

- [ ] **Step 5: Run the learn-pattern-relevant guards**

Run: `cd /Users/ryotaro/workspace/workato-toolkit && python3 -m pytest tests/test_skills_migration.py -k "learning_skills" -v`

Expected: PASS for `learn-pattern` portions of `test_learning_skills_reference_mcp_tool` and `test_learning_skills_have_no_submodule_language` (it now references `workato_docs_lookup` and has no `submodule`/`cd kit`).

- [ ] **Step 6: Commit**

```bash
cd /Users/ryotaro/workspace/workato-toolkit
git add skills/learn-pattern/SKILL.md
git commit -m "docs(p4): learn-pattern index read via MCP, drop submodule git steps

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 4: Migrate `skills/sync-connectors/SKILL.md`

Pre-built connector docs move from the read-only kit `docs/connectors/` to the workspace `org/docs/connectors/`. Existing-doc reads (for diffing against the API) go through the MCP lookup. Custom-connector handling (`connectors/docs/`) is unchanged.

**Files:**
- Modify: `skills/sync-connectors/SKILL.md`

- [ ] **Step 1: Fix the frontmatter description**

Replace (line 1, the `description:` value fragment):

```
Pre-built connectors are fetched via the API and written to `docs/connectors/`; custom connectors are parsed from `connector.rb` and written to `connectors/docs/`.
```

with:

```
Pre-built connectors are fetched via the API and written to the workspace `org/docs/connectors/`; custom connectors are parsed from `connector.rb` and written to `connectors/docs/`.
```

- [ ] **Step 2: Fix the intro bullets**

Replace this block (currently lines ~9–11):

```markdown
- **Pre-built connectors**: fetched from the Workato API → updates `docs/connectors/`.
- **Custom connectors**: parsed from `connector.rb` → updates `connectors/docs/`.
```

with:

```markdown
- **Pre-built connectors**: fetched from the Workato API → updates the workspace `org/docs/connectors/`. (The kit's bundled `docs/connectors/` is read-only; read it for diffing via `workato_docs_lookup`, but never write there.)
- **Custom connectors**: parsed from `connector.rb` → updates `connectors/docs/`.
```

- [ ] **Step 3: Repoint "Updating one pre-built connector"**

Replace this block (currently lines ~162–182):

```markdown
3. Create or update `docs/connectors/<name>.md`:

```markdown
# <Title> connector

Provider: `<name>`

## Triggers
| Name | Internal name | Batch | Description |
|---|---|---|---|
| <title> | `<name>` | Yes/- | |

## Actions
| Name | Internal name | Batch | Description |
|---|---|---|---|
| <title> | `<name>` | Yes/- | |

## Field details

(accumulated by /learn-recipe)
```
```

with:

```markdown
3. Read the existing merged doc with `workato_docs_lookup("connectors/<name>.md")` (kit + org overlay) to see what is already documented, then create or update the workspace file `org/docs/connectors/<name>.md` (create the directory with `mkdir -p org/docs/connectors` on first write). Write only triggers/actions not already present in the merged result:

```markdown
# <Title> connector

Provider: `<name>`

## Triggers
| Name | Internal name | Batch | Description |
|---|---|---|---|
| <title> | `<name>` | Yes/- | |

## Actions
| Name | Internal name | Batch | Description |
|---|---|---|---|
| <title> | `<name>` | Yes/- | |

## Field details

(accumulated by /learn-recipe and /auto-learn, in this same org/docs file)
```
```

- [ ] **Step 4: Repoint the diff-update rules**

Replace this block (currently lines ~184–193):

```markdown
### Diff-update rules

- **New file**: create when the file doesn't exist.
- **Existing file**:
  - Compare triggers/actions retrieved from the API with what's in the file.
  - Add anything new.
  - **Always preserve the frontmatter (the `---`-delimited YAML block).** Items like `connector_id` are managed by `sdk push` — never rewrite them.
  - Preserve sections after `## Field details` (info accumulated by `/learn-recipe`).
  - Annotate triggers / actions that flipped to deprecated.
- **Canonical provider name**: the API's `name` field is the canonical provider name.
```

with:

```markdown
### Diff-update rules

- **New file**: create `org/docs/connectors/<name>.md` when it doesn't exist.
- **Existing file** (`org/docs/connectors/<name>.md`):
  - Compare triggers/actions retrieved from the API with the merged result from `workato_docs_lookup("connectors/<name>.md")` (so kit-documented ops are not duplicated into the org file).
  - Add only what is missing.
  - **Always preserve the frontmatter (the `---`-delimited YAML block).** Items like `connector_id` are managed by `sdk push` — never rewrite them.
  - Preserve sections after `## Field details` (info accumulated by `/learn-recipe` / `/auto-learn`).
  - Annotate triggers / actions that flipped to deprecated.
- **Canonical provider name**: the API's `name` field is the canonical provider name.
```

- [ ] **Step 5: Repoint the `--all` pre-built sub-section**

Replace this block (currently lines ~197–202):

```markdown
#### Pre-built connectors
```bash
# Fetch every pre-built connector
python3 scripts/workato-api.py connectors list-platform
```
Fetch the JSON for every connector and generate / update `docs/connectors/<name>.md` for each.
```

with:

```markdown
#### Pre-built connectors
```bash
# Fetch every pre-built connector
python3 scripts/workato-api.py connectors list-platform
```
Fetch the JSON for every connector and generate / update `org/docs/connectors/<name>.md` for each (diffing against `workato_docs_lookup` so kit-documented ops are not re-written).
```

- [ ] **Step 6: Repoint `--check`**

Replace this block (currently lines ~207–215):

```markdown
1. Fetch every connector's triggers / actions from the API.
2. Compare with existing files in `docs/connectors/`.
3. Report the diff:
   - ✅ Match
   - ⚠️ API has it, docs don't (new trigger / action)
   - ❌ Docs have it, API doesn't (removed or renamed)
   - 📄 Connector with no docs file at all
```

with:

```markdown
1. Fetch every connector's triggers / actions from the API.
2. Compare with the merged docs from `workato_docs_lookup("connectors/<name>.md")` (kit + `org/docs/` overlay).
3. Report the diff:
   - ✅ Match
   - ⚠️ API has it, docs don't (new trigger / action)
   - ❌ Docs have it, API doesn't (removed or renamed)
   - 📄 Connector with no docs at all (neither kit nor org)
```

- [ ] **Step 7: Repoint the `_index.md` section**

Replace this block (currently lines ~217–222):

```markdown
## Updating `docs/connectors/_index.md` (pre-built only)

During `--all`, also update `_index.md`:
- Refresh the pre-built connector list precisely from the API data.
- Use the `name` field as the provider name.
- Do not include custom connectors here (those are managed in `connectors/docs/` because they are org-specific).
```

with:

```markdown
## Updating `org/docs/connectors/_index.md` (pre-built only)

During `--all`, also update the workspace `org/docs/connectors/_index.md` (seed it from `workato_docs_lookup("connectors/_index.md")` if it does not yet exist):
- Refresh the pre-built connector list precisely from the API data.
- Use the `name` field as the provider name.
- Do not include custom connectors here (those are managed in `connectors/docs/` because they are org-specific).
```

- [ ] **Step 8: Repoint the Output section**

Replace this line (currently line ~229):

```markdown
- The list of created / updated files (`docs/connectors/`).
```

with:

```markdown
- The list of created / updated files (`org/docs/connectors/`).
```

- [ ] **Step 9: Rewrite the Git-management section**

Replace this block (currently lines ~238–258):

```markdown
## Git management

This skill writes to **two locations**:

- `docs/connectors/*.md` → the knowledge base inside the kit (submodule) → PR back to workato-dev-kit.
- `connectors/docs/*.md` → the workspace repository's custom-connector knowledge.

Commit after running:

```bash
# Workspace side (custom connector updates)
git add connectors/docs/
git commit -m "docs: update custom connector info"

# Kit side (pre-built connector updates) → PR to workato-dev-kit
cd kit
git add docs/connectors/
git commit -m "docs: update pre-built connector info"
```

Committing and pushing only one side leaves your knowledge inconsistent.
```

with:

```markdown
## Git management

This skill writes to **two workspace-repo locations** (the plugin's bundled `docs/` is read-only and is never written):

- `org/docs/connectors/*.md` → pre-built connector knowledge in the org overlay.
- `connectors/docs/*.md` → the workspace repository's custom-connector knowledge.

Commit after running:

```bash
cd <workspace-root>
git add org/docs/connectors/ connectors/docs/
git commit -m "docs: update connector info (pre-built + custom)"
```

To upstream pre-built spec into the kit canonical docs, open a separate PR against the `workato-toolkit` repository (out of scope here).
```

- [ ] **Step 10: Run the sync-connectors guards**

Run: `cd /Users/ryotaro/workspace/workato-toolkit && python3 -m pytest tests/test_skills_migration.py -k "sync_skills or learning_skills" -v`

Expected: PASS — `sync-connectors` now has no bare `docs/connectors/`, writes to `org/docs/connectors/`, references `workato_docs_lookup`, and has no `submodule`/`cd kit`.

- [ ] **Step 11: Commit**

```bash
cd /Users/ryotaro/workspace/workato-toolkit
git add skills/sync-connectors/SKILL.md
git commit -m "docs(p4): sync-connectors writes pre-built to org/docs, reads via MCP

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 5: Migrate `skills/auto-learn/SKILL.md`

`/auto-learn` harvests pre-built connector fields via the Workato UI and appends them to connector docs. Those appends move to `org/docs/connectors/`; the "already learned" skip-check and the `--followups` aggregation follow.

**Files:**
- Modify: `skills/auto-learn/SKILL.md`

- [ ] **Step 1: Fix the frontmatter description**

Replace (line 2, the `description:` value fragment):

```
appending the results to `docs/connectors/<provider>.md`
```

with:

```
appending the results to the workspace `org/docs/connectors/<provider>.md`
```

- [ ] **Step 2: Fix the intro paragraph**

Replace this line (currently line 8):

```markdown
Drive the Workato UI through Claude in Chrome and actively collect input / output fields for every operation (trigger / action) of the target connector, then append the results to `docs/connectors/<provider>.md`.
```

with:

```markdown
Drive the Workato UI through Claude in Chrome and actively collect input / output fields for every operation (trigger / action) of the target connector, then append the results to the workspace `org/docs/connectors/<provider>.md`. (The kit's bundled `docs/connectors/` is read-only; read it for the skip-check via `workato_docs_lookup`, but never write there.)
```

- [ ] **Step 3: Repoint the `--followups` option description**

Replace this block (currently line 37):

```markdown
- `--followups` — **no-UI mode**. Aggregate the `## Learning summary` sections of existing `docs/connectors/*.md` and print to stdout. A `<provider>` argument restricts to one connector; otherwise aggregates across all 7+ connectors. The execution flow (Phases 1–5) does not run. See "Followups mode" at the end of this file.
```

with:

```markdown
- `--followups` — **no-UI mode**. Aggregate the `## Learning summary` sections of existing `org/docs/connectors/*.md` and print to stdout. A `<provider>` argument restricts to one connector; otherwise aggregates across all connectors. The execution flow (Phases 1–5) does not run. See "Followups mode" at the end of this file.
```

- [ ] **Step 4: Repoint Phase 1 Bootstrap**

Replace this block (currently lines ~80–86):

```markdown
### Phase 1: Bootstrap

1. Read `docs/connectors/<provider>.md`.
2. Enumerate op name and kind from the Triggers / Actions tables.
3. Exclude: `__adhoc_http_action`, deprecated entries (rows annotated `[deprecated]` etc.).
4. Unless `--force` is set, skip ops that already have a section starting with `### <op>`. Match **by op name only** (the token right after `### ` at the start of the line); ignore parenthesised suffixes such as display titles. For example, both `### delete_message (Delete message)` and `### delete_message (Action)` count as the same op and are skipped.
5. Put the remaining ops into the processing queue.
```

with:

```markdown
### Phase 1: Bootstrap

1. Read the merged connector doc via `workato_docs_lookup("connectors/<provider>.md")` (bundled kit doc + `org/docs/` overlay).
2. Enumerate op name and kind from the Triggers / Actions tables.
3. Exclude: `__adhoc_http_action`, deprecated entries (rows annotated `[deprecated]` etc.).
4. Unless `--force` is set, skip ops that already have a section starting with `### <op>` in the merged result. Match **by op name only** (the token right after `### ` at the start of the line); ignore parenthesised suffixes such as display titles. For example, both `### delete_message (Delete message)` and `### delete_message (Action)` count as the same op and are skipped.
5. Put the remaining ops into the processing queue.
```

- [ ] **Step 5: Repoint Phase 4 append target**

Replace this line (currently line 156):

```markdown
In `docs/connectors/<provider>.md`, append each op's result to the `## Action details` / `## Trigger details` sections:
```

with:

```markdown
In the workspace `org/docs/connectors/<provider>.md` (create the directory with `mkdir -p org/docs/connectors` on first write), append each op's result to the `## Action details` / `## Trigger details` sections:
```

- [ ] **Step 6: Repoint the Phase-4 Learning-summary instruction**

Replace this line (currently line 197):

```markdown
After appending each op's result, add a `## Learning summary` section to the **end** of `docs/connectors/<provider>.md` (below the final `## ...` section). **Replace if it already exists** — this section holds only the latest run's snapshot, and historical runs are tracked via git history.
```

with:

```markdown
After appending each op's result, add a `## Learning summary` section to the **end** of `org/docs/connectors/<provider>.md` (below the final `## ...` section). **Replace if it already exists** — this section holds only the latest run's snapshot, and historical runs are tracked via git history.
```

- [ ] **Step 7: Repoint the follow-ups grep hint**

Replace this line (currently line 240):

```markdown
This section becomes **the single reference point for "give me follow-ups" requests**. `grep "^## Learning summary" docs/connectors/*.md -A 200` produces follow-ups for every connector.
```

with:

```markdown
This section becomes **the single reference point for "give me follow-ups" requests**. `grep "^## Learning summary" org/docs/connectors/*.md -A 200` produces follow-ups for every connector.
```

- [ ] **Step 8: Repoint Phase 5 persisted line and "produce follow-ups" note**

Replace this line (currently line 254):

```markdown
- Persisted: updated `## Learning summary` in docs/connectors/<provider>.md
```

with:

```markdown
- Persisted: updated `## Learning summary` in org/docs/connectors/<provider>.md
```

Then replace this line (currently line 263):

```markdown
When asked later to "produce follow-ups", you can answer just by reading the `## Learning summary` blocks in `docs/connectors/*.md`. The result is deterministically reproducible in a new session.
```

with:

```markdown
When asked later to "produce follow-ups", you can answer just by reading the `## Learning summary` blocks in `org/docs/connectors/*.md`. The result is deterministically reproducible in a new session.
```

- [ ] **Step 9: Repoint the relearn "New sections" reference and the manual-feedback hint**

Replace this line (currently line 295):

```markdown
- New sections use the same format as [/learn-recipe](../learn-recipe/SKILL.md).
```

with:

```markdown
- New sections use the same format as `/learn-recipe` (both write to the same `org/docs/connectors/<provider>.md`).
```

Then replace this line (currently line 307):

```markdown
When you notice any of these, either run `/learn-recipe` on a specific recipe or edit `docs/connectors/<provider>.md` directly.
```

with:

```markdown
When you notice any of these, either run `/learn-recipe` on a specific recipe or edit `org/docs/connectors/<provider>.md` directly.
```

- [ ] **Step 10: Repoint the Followups-mode body**

Replace this block (currently lines ~329–346):

```markdown
A **read-only aggregation mode** independent of the normal `/auto-learn` execution (no UI operations). It does not run Phases 1–5 at all — just reads the `## Learning summary` sections of `docs/connectors/*.md` and lists follow-ups.

### Invocation

```
/auto-learn --followups            # aggregate across all connectors
/auto-learn <provider> --followups # only the specified connector
```

### Behaviour

1. Targets:
   - With `<provider>` → `docs/connectors/<provider>.md` only.
   - Without → all of `docs/connectors/*.md` (exclude non-connector files like `_index.md` after content inspection).
2. Read each file and extract the `## Learning summary` section (up to the next `## ` or EOF).
```

with:

```markdown
A **read-only aggregation mode** independent of the normal `/auto-learn` execution (no UI operations). It does not run Phases 1–5 at all — just reads the `## Learning summary` sections of `org/docs/connectors/*.md` and lists follow-ups.

### Invocation

```
/auto-learn --followups            # aggregate across all connectors
/auto-learn <provider> --followups # only the specified connector
```

### Behaviour

1. Targets:
   - With `<provider>` → `org/docs/connectors/<provider>.md` only.
   - Without → all of `org/docs/connectors/*.md` (exclude non-connector files like `_index.md` after content inspection).
2. Read each file and extract the `## Learning summary` section (up to the next `## ` or EOF).
```

- [ ] **Step 11: Rewrite the Git-management section**

Replace this block (currently lines ~379–387):

```markdown
## Git management

The write target is `docs/connectors/<provider>.md` inside the kit (submodule) only. The skill itself does not commit (the user decides at the end). Commit inside the kit and PR back to workato-dev-kit:

```bash
cd kit
git add docs/connectors/<provider>.md
git commit -m "auto-learn: <provider> N op (M ok / K failed)"
```
```

with:

```markdown
## Git management

The write target is the workspace `org/docs/connectors/<provider>.md` (the plugin's bundled `docs/` is read-only). The skill itself does not commit (the user decides at the end):

```bash
cd <workspace-root>
git add org/docs/connectors/<provider>.md
git commit -m "auto-learn: <provider> N op (M ok / K failed)"
```

To upstream broadly-useful spec into the kit canonical docs, open a separate PR against the `workato-toolkit` repository.
```

- [ ] **Step 12: Repoint the Related-docs links**

Replace this block (currently lines ~390–394):

```markdown
- [/sync-connectors](../sync-connectors/SKILL.md) — collect Triggers/Actions lists (the upstream of this skill).
- [/learn-recipe](../learn-recipe/SKILL.md) — learn fields from an existing recipe (manual feedback path).
- [docs/patterns/auto-learn-ui-operations.md](../../../docs/patterns/auto-learn-ui-operations.md) — full DOM-selector reference for UI operations.
- [Issue #27](https://github.com/rkawaishi/workato-dev-kit/issues/27) — design motivation.
```

with:

```markdown
- `/sync-connectors` — collect Triggers/Actions lists (the upstream of this skill).
- `/learn-recipe` — learn fields from an existing recipe (manual feedback path).
- `workato_docs_lookup("patterns/auto-learn-ui-operations.md")` — full DOM-selector reference for UI operations.
- [Issue #27](https://github.com/rkawaishi/workato-dev-kit/issues/27) — design motivation (historical).
```

- [ ] **Step 13: Run the auto-learn guards**

Run: `cd /Users/ryotaro/workspace/workato-toolkit && python3 -m pytest tests/test_skills_migration.py -k "sync_skills or learning_skills" -v`

Expected: PASS — `auto-learn` now has no bare `docs/connectors/`, writes to `org/docs/connectors/`, references `workato_docs_lookup`, and has no `submodule`/`cd kit`.

- [ ] **Step 14: Commit**

```bash
cd /Users/ryotaro/workspace/workato-toolkit
git add skills/auto-learn/SKILL.md
git commit -m "docs(p4): auto-learn appends to org/docs, reads/followups via org overlay

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 6: Align the `org-knowledge-overlay` rule + regenerate derived files

The canonical always-on rule still describes the submodule/symlink era and routes sync skills to the read-only kit `docs/`. Rewrite it to plugin reality, then regenerate the derived files so CLAUDE.md/AGENTS.md/GEMINI.md and the `.mdc` files stay in sync (enforced by `sync-check.yml`).

**Files:**
- Modify: `rules/org-knowledge-overlay.md`
- Regenerate (via generator): `rules/org-knowledge-overlay.mdc`, `rules/workato-project.mdc`, `CLAUDE.md`, `AGENTS.md`, `GEMINI.md`

- [ ] **Step 1: Rewrite the rule intro + Layout**

Replace this block (currently lines 1–26):

```markdown
# Org Knowledge Overlay

A convention for accumulating organization-specific knowledge separately from the kit's knowledge base (`docs/`).
This guarantees that updating the kit does not lose or overwrite the organization's learning.

## Layout

```
<workspace-root>/
├── docs/                       ← symlink to kit/docs/ (read-only)
│   ├── connectors/<name>.md
│   ├── logic/<topic>.md
│   ├── platform/<topic>.md
│   ├── patterns/<...>
│   └── learned-patterns.md
└── org/                        ← organization knowledge. The kit never touches this.
    └── docs/                   ← mirrors the docs/ tree
        ├── connectors/<name>.md
        ├── logic/<topic>.md
        ├── platform/<topic>.md
        ├── patterns/<...>
        └── learned-patterns.md
```

`org/` is managed in the workspace repository (outside the kit submodule).
You may create directories under `org/docs/` on demand; you do not need to pre-create empty ones.
```

with:

```markdown
# Org Knowledge Overlay

A convention for accumulating organization-specific knowledge separately from the kit's bundled knowledge base.
This guarantees that updating the toolkit does not lose or overwrite the organization's learning.

The kit's canonical docs ship **inside the plugin** and are read-only. They are surfaced through the
docs-overlay MCP (`workato_docs_lookup(path)` / `workato_docs_list(prefix)`), which merges them with the
project's `org/docs/` overlay (org wins on conflicts). Skills never read the bundled docs from a local path.

## Layout

```
<workspace-root>/                 ← your project / workspace repository
└── org/                          ← organization knowledge. The kit/plugin never touches this.
    └── docs/                     ← mirrors the kit docs/ tree
        ├── connectors/<name>.md
        ├── logic/<topic>.md
        ├── platform/<topic>.md
        ├── patterns/<...>
        └── learned-patterns.md

<plugin install dir>/docs/         ← kit canonical docs, BUNDLED + READ-ONLY (served via the docs-overlay MCP)
```

`org/` is managed in the workspace repository. You may create directories under `org/docs/` on demand;
you do not need to pre-create empty ones.
```

- [ ] **Step 2: Rewrite the Responsibilities table + the "Do not edit" note**

Replace this block (currently lines 28–39):

```markdown
## Responsibilities

| Type of knowledge | Where it lives | Skill that writes it |
|---|---|---|
| Workato official spec and API info for every connector | `docs/` (kit) | `/sync-connectors`, `/auto-learn` |
| Field info and operational know-how for what the org actually uses | `org/docs/` | `/learn-recipe`, `/learn-pattern` |
| Corrections or addenda to kit docs | `org/docs/<same-relative-path>` | Edited manually by the user |
| Org-specific connectors, logic, patterns | `org/docs/<...>` | Edited manually by the user |

**Do not edit the kit's `docs/` directly** — that would commit into the kit submodule.
If you find an error, write a correction at `org/docs/<same-relative-path>`.
If you later want to upstream it into the kit, open a separate PR (out of scope here).
```

with:

```markdown
## Responsibilities

| Type of knowledge | Where it lives | Skill that writes it |
|---|---|---|
| Workato official spec and API info for every connector | `org/docs/` | `/sync-connectors`, `/auto-learn` |
| Field info and operational know-how for what the org actually uses | `org/docs/` | `/learn-recipe`, `/learn-pattern` |
| Corrections or addenda to kit docs | `org/docs/<same-relative-path>` | Edited manually by the user |
| Org-specific connectors, logic, patterns | `org/docs/<...>` | Edited manually by the user |

**Never write to the plugin's bundled `docs/`** — it is read-only.
If you find an error, write a correction at `org/docs/<same-relative-path>`.
If you later want to upstream knowledge into the kit canonical docs, open a separate PR against the
`workato-toolkit` repository (out of scope here).
```

- [ ] **Step 3: Rewrite the Read convention**

Replace this block (currently lines 41–53):

```markdown
## Read convention

When a skill or recipe-creation process references `@docs/<path>`, it must also check the matching `@org/docs/<path>`:

1. Read `@docs/<path>`.
2. If `@org/docs/<path>` exists, read it as well.
3. When the two conflict, **the org version wins** (org overrides kit defaults).
4. Non-overlapping information from each is additive.

Examples:
- Referencing `@docs/connectors/clearbit.md` → also check `@org/docs/connectors/clearbit.md`.
- Referencing `@docs/logic/data-pills.md` → also check `@org/docs/logic/data-pills.md`.
- For org-only resources like `@org/docs/connectors/<internal>.md` (no kit equivalent), read just the org file.
```

with:

```markdown
## Read convention

To consult a knowledge-base document, call the docs-overlay MCP tool — do **not** read a local `docs/` path:

1. Call `workato_docs_lookup("<path>")`. It returns the bundled kit doc merged with `org/docs/<path>` if present.
2. When the two conflict, **the org version wins** (org overrides kit defaults); non-overlapping info is additive.
3. Use `workato_docs_list("<prefix>")` to discover available documents under a prefix.

Examples:
- Connector spec → `workato_docs_lookup("connectors/clearbit.md")`.
- Datapill patterns → `workato_docs_lookup("logic/data-pills.md")`.
- For org-only resources with no kit equivalent (e.g. an internal connector), the same call returns just the org file.
```

- [ ] **Step 4: Convert the learning-skills "before writing" read instruction**

Replace this line (currently line 76):

```markdown
Before writing, read the matching `docs/<same-relative-path>` and skip anything the kit already documents. Only write **differences, corrections, and org-specific additions** to `org/docs/`.
```

with:

```markdown
Before writing, call `workato_docs_lookup("<same-relative-path>")` and skip anything the kit already documents. Only write **differences, corrections, and org-specific additions** to `org/docs/`.
```

- [ ] **Step 5: Rewrite the Sync-skills paragraph**

Replace this block (currently lines 78–80):

```markdown
### Sync skills (`/sync-connectors`, `/auto-learn`)

These write information obtained from Workato official sources into the kit canonical `docs/`. They continue to target `kit/docs/connectors/<name>.md` (commits inside the kit submodule). They do not touch `org/docs/connectors/<name>.md`.
```

with:

```markdown
### Sync skills (`/sync-connectors`, `/auto-learn`)

These collect information from Workato official sources (API / UI). Because the kit's bundled `docs/` is
read-only under plugin distribution, they write to the workspace **`org/docs/connectors/<name>.md`**
(the same file `/learn-recipe` grows). Custom-connector docs go to `connectors/docs/<name>.md`.
To promote broadly-useful spec into the kit canonical docs, open a separate PR against `workato-toolkit`.
```

- [ ] **Step 6: Fix the Git-management submodule line**

Replace this block (currently lines 82–92):

```markdown
## Git management

Changes under `org/docs/` are committed in the workspace repository:

```bash
cd <workspace-root>
git add org/docs/
git commit -m "docs(org): learn from <project-name> recipes"
```

Do not commit to the kit submodule (`kit/`).
```

with:

```markdown
## Git management

Changes under `org/docs/` are committed in the workspace repository:

```bash
cd <workspace-root>
git add org/docs/
git commit -m "docs(org): learn from <project-name> recipes"
```

Never write to the plugin's bundled `docs/` — it is read-only.
```

- [ ] **Step 7: Run the generator**

Run: `cd /Users/ryotaro/workspace/workato-toolkit && python3 scripts/sync_derived.py`
Expected: exits 0; regenerates `rules/org-knowledge-overlay.mdc`, `rules/workato-project.mdc`, `CLAUDE.md`, `AGENTS.md`, `GEMINI.md` with the new overlay text.

- [ ] **Step 8: Run the rule + derived-sync guards**

Run: `cd /Users/ryotaro/workspace/workato-toolkit && python3 -m pytest tests/test_rules_agents_hooks_migration.py::test_overlay_rule_reflects_plugin_distribution tests/test_derived_sync.py -v`
Expected: PASS — the overlay rule guard passes and `test_derived_files_in_sync_with_source` is green (derived files match the regenerated source because they are staged/committed in the next step).

> Note: `test_derived_files_in_sync_with_source` checks `git status`, so it is only green after the regenerated derived files are committed (Step 9). If it flags uncommitted derived files before Step 9, that is expected — commit, then it passes.

- [ ] **Step 9: Commit the rule + regenerated derived files together**

```bash
cd /Users/ryotaro/workspace/workato-toolkit
git add rules/org-knowledge-overlay.md rules/org-knowledge-overlay.mdc rules/workato-project.mdc CLAUDE.md AGENTS.md GEMINI.md
git commit -m "docs(p4): align org-knowledge-overlay rule with plugin distribution

Kit docs are bundled read-only and served via the docs-overlay MCP; sync
skills now write pre-built spec to org/docs. Regenerate derived context/.mdc.

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 7: Full suite + final review

**Files:** none (verification only)

- [ ] **Step 1: Run the entire test suite**

Run: `cd /Users/ryotaro/workspace/workato-toolkit && python3 -m pytest -q`
Expected: all tests pass (the prior 58 plus the new P4 guards). If `test_derived_files_in_sync_with_source` fails, a derived file drifted — re-run `python3 scripts/sync_derived.py`, inspect `git diff`, and commit.

- [ ] **Step 2: Confirm no bare kit-docs write paths remain anywhere in the learning skills**

Run: `cd /Users/ryotaro/workspace/workato-toolkit && grep -rnE '(?<!org/)docs/connectors/' skills/learn-recipe skills/learn-pattern skills/sync-connectors skills/auto-learn || echo "clean"`
(If `grep -P` lookbehind is unavailable on this platform, use: `grep -rn 'docs/connectors/' skills/{learn-recipe,learn-pattern,sync-connectors,auto-learn} | grep -v 'org/docs/connectors/' || echo "clean"`.)
Expected: `clean`.

- [ ] **Step 3: Final code review**

Run `/code-review` against `main...HEAD` (the P4 branch). Address any CONFIRMED/PLAUSIBLE findings. (Per the project lesson, `/codex:review` cannot see committed diffs — use local `/code-review`.)

---

## Self-Review (author checklist — completed)

**Spec coverage:** Decision "pre-built spec → org/docs" → Tasks 4, 5, 6. "learn-* residual submodule cleanup" → Tasks 2, 3. "rule contradicts decision/MCP reality" → Task 6. "drift enforcement" → Task 6 Step 7–9 + Task 7. Test guards → Task 1. All covered.

**Placeholder scan:** every edit step contains the exact old block and exact new block; every test step contains the actual Python; every command has expected output. No TBD/TODO.

**Type/name consistency:** test names (`test_sync_skills_write_to_org_docs`, `test_learning_skills_reference_mcp_tool`, `test_learning_skills_have_no_submodule_language`, `test_overlay_rule_reflects_plugin_distribution`), regex name (`_BARE_KIT_CONNECTOR_PATH`), and set names (`_WRITE_REDESIGNED_SKILLS`, `_MCP_REQUIRED_LEARNING_SKILLS`) are used consistently across Task 1 and the verification steps. The MCP tool names (`workato_docs_lookup` / `workato_docs_list`) match the existing skills and `CLAUDE.md`.

**Known fragility:** `_BARE_KIT_CONNECTOR_PATH` uses a fixed-width negative lookbehind `(?<!org/)` — valid in Python `re`. It deliberately does NOT match `connectors/docs/` (custom) or `org/docs/connectors/` (org). Verified the four migrated skills will contain zero bare `docs/connectors/` after the edits.
