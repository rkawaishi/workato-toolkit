---
description: Create any Workato asset — recipe, Genie (AI agent), MCP server, Workflow App, or custom connector — as JSON/Ruby files ready to push. The asset type is the subcommand; run without one to have it inferred from your request or plan.md. Japanese prompts are also supported.
allowed-tools: Read, Write, Edit, Glob, Grep, Bash, WebFetch, Agent
---

# /workato-create

Creates Workato assets. One skill, one pipeline; the asset type is a
subcommand whose specifics live in a reference file loaded on demand.

## Usage

- `/workato-create <type> [args]` — create an asset of the given type
- `/workato-create` — infer the type from the request / plan.md task tag, confirm, proceed

| Subcommand | Produces | Reference (read AFTER routing) |
|---|---|---|
| `recipe` | `*.recipe.json` + `*.connection.json` | [references/recipe.md](references/recipe.md) |
| `genie` | `*.agentic_genie.json` + skills + skill recipes | [references/genie.md](references/genie.md) |
| `mcp-server` | `*.mcp_server.json` + skills + skill recipes (no Genie) | [references/mcp-server.md](references/mcp-server.md) |
| `workflow-app` | `*.lcap_app.json` + Data Tables + Pages + recipes | [references/workflow-app.md](references/workflow-app.md) |
| `connector` | `connectors/<name>/connector.rb` + scaffolding | [references/connector.md](references/connector.md) |

Type-specific arguments keep their old semantics — e.g.
`/workato-create recipe <project>/<NNN>-<slug>` pulls context from `plan.md`
(this is how `/implement` invokes it), `/workato-create connector <api-name>`.

**Read exactly one reference file per asset.** Do not load the others; the
whole point of the split is that only the routed type's specifics enter
context. Composite assets recurse through the pipeline: `genie` /
`workflow-app` create their recipes by applying `references/recipe.md` per
recipe (same pipeline, no separate skill invocation).

## Common pipeline (every type)

1. **Context** — when `<project>/<NNN>-<slug>` is supplied or inferable, read
   `projects/<project>/specs/<NNN>-<slug>/plan.md` and take its sections as
   defaults (each reference lists which sections it consumes). No plan.md →
   the reference's interview flow.
2. **Reference** — read `references/<type>.md`; run its interview /
   design steps.
3. **Reuse check** — if `projects/CATALOG.md` exists, propose matching shared
   connections / Recipe Functions before creating new ones.
4. **Knowledge** — consult connector/domain knowledge via `workato_docs_lookup`
   (the reference names the exact paths).
5. **Generate via the `workato-builder` subagent** — pass it: the asset type,
   the finalized design (or the plan.md pointer), the target file paths, and
   the instruction to fetch its generation reference itself via
   `workato_asset_path("workato-create/references/<type>.md")`.
   (`mcp-server` is the one special case: dispatch it as asset type `genie`
   and have the builder fetch BOTH `genie.md` and `mcp-server.md`.) The subagent
   generates, validates, writes, and returns a short summary — large JSON/Ruby
   never enters this conversation. (Only if subagent dispatch is unavailable,
   follow the reference's generation sections inline.)
6. **Deploy guidance** — walk the user through push / auth / UI verification
   as the reference specifies.
7. **Learning loop** — after UI adjustments: pull → `/learn-recipe`; new
   construction patterns → `/learn-pattern`. Do not skip when the plan's
   `## Unlearned Actions` has entries.

## Git management

Generated files live in the workspace repository — commit them there
(`projects/<project>/…`, or `connectors/<name>/` for connectors):

```bash
git add <generated paths shown by the reference>
git commit -m "Add <type>: <name>"
git push origin
```

`workato push` / `sdk push` deploy to the Workato API and have zero effect on
git — do both.
