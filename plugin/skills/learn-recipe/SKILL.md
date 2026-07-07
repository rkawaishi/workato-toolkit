---
description: Analyze recipe JSON and accumulate field info / pattern findings into the organization knowledge layer (`org/docs/`). Learn from pulled recipes to grow the org knowledge base. Japanese prompts are also supported.
allowed-tools: Read, Write, Edit, Glob, Grep
---

# /learn-recipe

Analyze recipe JSON and append every finding directly into the **organization knowledge layer `org/docs/`**.
We don't accumulate findings in an intermediate file — we grow each doc directly.

Write destinations, dedup, and git conventions: follow the `org-knowledge-overlay` rule (always-on).

## Usage

- `/learn-recipe <file-path>` — analyze a specific recipe
- `/learn-recipe <project-name>` — analyze every recipe in a project
- `/learn-recipe` — analyze every recipe across every project

## What we learn

Where each finding goes is defined by the destination table in the `org-knowledge-overlay` rule (always-on).

### 1. Field info (most important)

Extract input/output field schemas from each step.

Sources:
- `extended_output_schema` — action / trigger output fields
- `extended_input_schema` — action / trigger input fields
- `input` — the actual input value (including datapill references)
- `parameters_schema_json` — Genie / Function parameters (JSON string)
- `result_schema_json` — Genie / Function result (JSON string)
- `input.input.schema` — Custom Action request schema
- `input.output` — Custom Action response schema

Format:
```markdown
### <action_name>

#### Input fields
| Field | Type | Required | Description |
|---|---|---|---|
| field_name | type | Yes/- | label |

#### Output fields
| Field | Type | Description |
|---|---|---|
| field_name | type | label |
| parent.child | type | label (nested) |
```

### 2. New providers / actions

When you find an unknown `provider`/`name` combination in a recipe (i.e. an action that doesn't appear in `workato_docs_lookup("connectors/<provider>.md")`).

### 3. JSON-structure findings

New discoveries about recipe JSON structure (new keywords, unknown fields, unusual constructs, etc.) — anything observed within the org's recipes.

### 4. Datapill patterns

New datapill notations or reference patterns.

### 5. Deploy-related findings

New behavior observed on push/pull (field reset, schema expansion, version change, etc.).

### 6. Findings that don't fit elsewhere

Anything that doesn't match the categories above.

## Analysis procedure

1. Read the target `.recipe.json`.
2. Walk every step recursively.
3. For each step:
   a. Check whether `provider` and `name` are known (call `workato_docs_lookup` with path `connectors/<provider>.md` — it returns kit + org merged).
   b. If `extended_output_schema` / `extended_input_schema` is present, extract the field info.
   c. Record any new structural patterns.
4. Apply the dedup procedure from the `org-knowledge-overlay` rule (always-on), then append only the new findings.

## Output

After analysis, report:
- The number of files analyzed.
- The list of updated docs (all under `org/docs/`) with a summary of what was appended.
- Any newly discovered patterns.

## Reconciling Unlearned Actions

When run against a project, scan every feature's `plan.md` and `tasks.md` under `projects/<project-name>/specs/` and reconcile entries that correspond to the `provider` / `action` you just learned (see the recipe lifecycle guide via `workato_docs_lookup("guides/lifecycle.md")`).

### `## Unlearned Actions` table in plan.md

For each `projects/<project-name>/specs/<NNN>-<slug>/plan.md`:

1. Check for a `## Unlearned Actions` table.
2. If a row matches the just-learned `provider` / `action`, **delete the row**.
3. When every row is deleted, leave the table in place with a note "(learned)" — keep it as a history record.

### `[learn]` tasks in tasks.md

For each `projects/<project-name>/specs/<NNN>-<slug>/tasks.md`:

1. Find unfinished tasks (`- [ ]`) tagged `[learn]` that mention `provider/action`.
2. Check them off as `- [x]`.
3. Update `Last updated`.

### Reporting

```
Unlearned Actions reconciliation:
- Rows removed from plan.md: <N> (in <feature> etc.)
- Tasks checked off in tasks.md: <M> (in <feature> etc.)

Features still carrying unfinished Unlearned Actions:
- <project>/specs/<NNN>-<slug>: <remaining count>
```

> **Backwards compatibility**: the legacy `## Unlearned Actions` in `projects/<project-name>/DESIGN.md` is **not read** (hard-cutover in Phase B). If a project still only has DESIGN.md, run `/spec migrate` first to convert into `specs/`.

## Git management

Follow the `org-knowledge-overlay` rule (always-on). This skill additionally touches `projects/<name>/specs/` (Unlearned-Actions reconciliation) — include it in the same commit (`git add org/docs/ projects/<name>/specs/`).
