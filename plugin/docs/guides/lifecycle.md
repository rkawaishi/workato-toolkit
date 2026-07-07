# Lifecycle and responsibility map

A consolidated reference for **when, by whom, and for what purpose** each skill is invoked, and each docs file is read or written.

The "knowledge lookup priority" in the always-on rules defines the **reading order**, while this document presents the bigger picture including **write timing and responsibilities**. Use it as a map for "remembering the skill you should actually run before falling back to grep."

## Overall flow

Proceed in the order `/spec` → `/implement` along the spec-driven workflow.

```
[Specification]   /spec                   → Write user experience and requirements in spec.md (technology-neutral),
                                            then resolve Open Questions in clarification mode (same skill)
                     ↓
[Design]          /plan                   → Write Workato configuration in plan.md (HOW)
                  /tasks                  → Decompose into executable tasks in tasks.md ([P]/[recipe]/[learn] tags)
                  /analyze                → Verify spec ↔ plan ↔ tasks consistency (read-only)
                     ↓
[Preparation]     /catalog                → Survey existing reusable assets (skip if already referenced in plan)
                  /sync-connectors        → Fetch metadata for connectors to be used
                     ↓
[Build]           /implement              → Read tasks.md and dispatch to the skills below
                  /workato-create recipe          → Read plan.md and generate a recipe
                  /workato-create workflow-app    → Read plan.md and generate a full Workflow App
                  /workato-create genie           → Generate Genie / MCP
                  /workato-create connector       → Generate a custom connector
                     ↓
[Validation]      /validate-recipe        → Validate JSON structure
                     ↓
[Sync]            /push-project                  → Push to the Workato remote (with validation)
                  (Adjust pick_list etc. in the UI)
                  /pull-project                  → Pull adjustments back locally
                     ↓
[Promotion]       /deploy-project         → Promote dev→test→prod via Deploy manifests (approvals stay human)
                     ↓
[Learning]        /learn-recipe           → Enrich org/docs/ from the adjusted recipe
                                            and tidy plan.md.Unlearned and tasks.md.[learn]
                  /learn-pattern          → Record a reusable construction pattern in org/docs/patterns/recipe-patterns/
                     ↓
[Cleanup]         /catalog                → Reflect newly shared assets in the catalog
                  /tasks --update         → Regenerate remaining tasks (optional)
```

> **The legacy design skill has been removed**: existing projects written in the legacy `DESIGN.md` format are converted to `specs/` via `/spec migrate <project>` and then join this flow. The legacy view/update compatibility modes are retired along with the rest of the old skill.

## Skill responsibility map

A list of "when each skill is invoked, what it reads, and what it writes."

### Setup phase (once per workspace)

| Skill | When to invoke | Reads | Writes |
|---|---|---|---|
| `/setup-workspace` | Adopting the toolkit in a repo, or after a plugin update (`--update`) | plugin bundled assets (via the `workato_asset_path` MCP tool) | `scripts/workato-api.py`, `scripts/ensure-workatoignore.sh`, `templates/workatoignore.template`, `org/` skeleton, credential deny-lists |
| `/issue-api-keys` | New workspace, key rotation, audits | `platform/developer-api-clients.md` (via `workato_docs_lookup`), `org/docs/platform/developer-api-clients.md` | Developer API clients (remote), CLI profiles/keyring, `org/docs/platform/developer-api-clients.md` |

### Specification phase

| Skill | When to invoke | Reads | Writes |
|---|---|---|---|
| `/spec <project>` | At project / feature start | (interview) | `projects/<name>/specs/<NNN>-<slug>/spec.md` (new) |
| `/spec <project>/<NNN>-<slug>` | When Open Questions remain in spec.md (clarification mode), or when resuming after an interruption | `spec.md` (`## Open Questions`) | `spec.md` (body + Open Questions checked off) |
| `/spec migrate <project>` | When converting a project that only has the legacy DESIGN.md into the spec-driven format | `projects/<name>/DESIGN.md` | `projects/<name>/specs/<NNN>-<slug>/{spec,plan,tasks}.md`, `DESIGN.md` → `DESIGN.md.legacy.<date>` |

### Design phase

| Skill | When to invoke | Reads | Writes |
|---|---|---|---|
| `/plan <project>/<NNN>-<slug>` | After Open Questions are resolved | `spec.md`, `projects/CATALOG.md`, `.resource-providers.yml`, `docs/patterns/recipe-patterns/`, `org/docs/patterns/recipe-patterns/`, `projects/docs/patterns/` (legacy) | `plan.md` (new) |
| `/tasks <project>/<NNN>-<slug>` | After plan.md is finalized | `plan.md` | `tasks.md` (new, with `[P]` / `[recipe]` etc. tags) |
| `/analyze <project>/<NNN>-<slug>` | Consistency check before `/implement` | `spec.md`, `plan.md`, `tasks.md` | None (read-only report) |

> **Legacy DESIGN.md**: migrate to `specs/` early via `/spec migrate <project>` (see the Specification phase above). The retired design skill's view/update compatibility modes are gone.

### Preparation phase

| Skill | When to invoke | Reads | Writes |
|---|---|---|---|
| `/catalog` | At session start (reuse check) | `projects/CATALOG.md` | None |
| `/catalog scan` | After shared assets are added or changed | All projects under `projects/`, `projects/CATALOG_CONFIG.yaml` | `projects/CATALOG.md` |
| `/sync-connectors <provider>` | Immediately before using an unknown connector | Workato API | `org/docs/connectors/<provider>.md` |
| `/sync-connectors --custom <name>` | After custom connector development | `connectors/<name>/connector.rb` | `connectors/docs/<name>.md` |

### Build phase

| Skill | When to invoke | Reads | Writes |
|---|---|---|---|
| `/implement <project>/<NNN>-<slug>` | After tasks.md is finalized | `tasks.md`, `plan.md`, `spec.md` (reference only) | `tasks.md` (check-off and FAILED marks) |
| `/workato-create recipe <project>/<NNN>-<slug>` | Invoked from `/implement` via [recipe]/[function]/[handler] tasks | `plan.md`, `docs/connectors/<provider>.md`, `connectors/docs/<name>.md`, `docs/logic/`, `docs/patterns/recipe-patterns/`, `org/docs/patterns/recipe-patterns/`, `projects/docs/patterns/` (legacy), `projects/CATALOG.md`, the `workato-recipe-format` rule (always-on) | `projects/<name>/Recipes/*.recipe.json`, `*.connection.json`; if needed, append to plan.md's Unlearned Actions and tasks.md's `[learn]` tasks |
| `/workato-create workflow-app <project>/<NNN>-<slug>` | Invoked from `/implement` via [page]/[data-table] tasks | `plan.md`, `docs/platform/workflow-apps.md`, `docs/patterns/deployment-guide.md`, the `workato-agentic-format` rule (always-on) | `projects/<name>/Data Tables/*.data_table.json`, `Pages/*.page.json`, `lcap_app.json`, `Recipes/*.recipe.json` |
| `/workato-create genie` | When creating a new AI agent (`[genie]` tasks; MCP servers are `[mcp]` → `/workato-create mcp-server`) | `plan.md` (optional), `docs/platform/agent-studio.md`, `docs/platform/mcp.md`, the `workato-agentic-format` rule (always-on) | `projects/<name>/Agents/*.agentic_genie.json`, `*.agentic_skill.json`, `*.mcp_server.json` |
| `/workato-create connector <api-name>` | Invoked via a `[connector]` task. Connectors are shared assets and are not tied to a project; the caller's `plan.md` Connections information is passed as arguments | `docs/connector-sdk/connector-rb.md`, `docs/connector-sdk/overview.md`, the `workato-connector-sdk` rule (always-on), API documentation (WebFetch) | `connectors/<name>/connector.rb`, `settings.yaml`, `Gemfile` |

### Validation and sync phases

| Skill | When to invoke | Reads | Writes |
|---|---|---|---|
| `/validate-recipe` | Before push, after editing JSON | The project's JSON files, the always-on rules | None (validation report only) |
| `/push-project` | Before deploy | The project's assets | Workato remote (does not modify local) |
| `/pull-project` | After UI adjustments, at handover time | Workato remote | Assets under `projects/<name>/` (overwritten) |
| `/deploy-project` | Releasing to test/prod (after dev verification) | `platform/environments.md` (via `workato_docs_lookup`), the org promotion policy record | Deploy manifests (remote; approvals stay human) |

### Learning phase

| Skill | When to invoke | Reads | Writes |
|---|---|---|---|
| `/learn-recipe` | Immediately after `/pull-project`, or after implementing previously unlearned actions | `projects/<name>/Recipes/*.recipe.json`, `projects/<name>/specs/*/plan.md` / `tasks.md` (the targets to tidy for learned actions), and the kit canonical `docs/<...>` as a cross-reference | `org/docs/connectors/<provider>.md` (input/output/snippet additions), `org/docs/logic/data-pills.md`, `org/docs/patterns/deployment-guide.md`, `org/docs/learned-patterns.md`; in addition, `projects/<name>/specs/*/plan.md` (remove relevant rows from the Unlearned Actions table) and `tasks.md` (check off `[learn]` tasks) |
| `/learn-pattern` | When you notice a reusable construction pattern | Reference recipes (optional), existing `docs/patterns/recipe-patterns/` (kit) + `org/docs/patterns/recipe-patterns/` (org) + `projects/docs/patterns/` (legacy, if present) | `org/docs/patterns/recipe-patterns/<name>.md` (single write target; distinguish generic vs. org-domain in the pattern body) |

## docs responsibility map

A list of "who writes and who reads" for each docs directory.

### Framework side (the `workato-toolkit` plugin)

The kit canonical `docs/` is **written only by kit maintainers** (via PRs to the `workato-toolkit` repository); the sync skills and user learning results accumulate on the `org/docs/` side (see the `org-knowledge-overlay` rule (always-on)).

| Path | Writer | Reader | Contents |
|---|---|---|---|
| `docs/connectors/<provider>.md` | Kit maintainers (PR) | `/workato-create recipe`, `/workato-create workflow-app`, `/workato-create genie` | Pre-built connector trigger/action/field specs (kit canonical) |
| `docs/connector-sdk/` | Manual | `/workato-create connector` | Connector SDK reference |
| `docs/logic/` | Manual | `/workato-create recipe`, `/workato-create workflow-app` | datapill syntax, formulas, loops, error handling, triggers |
| `docs/platform/` | Manual | `/workato-create workflow-app`, `/workato-create genie`, `/plan` | Data Table, Lookup Table, Agent Studio, MCP, Workflow App |
| `docs/patterns/recipe-patterns/` | Manual (kit maintainers) | `/workato-create recipe`, `/plan`, `/learn-pattern` (cross-reference at load time) | Recipe construction patterns (kit canonical, read-only) |
| `docs/patterns/deployment-guide.md` | Manual | `/push-project`, `/workato-create workflow-app` | Deployment procedures, common errors |
| `docs/patterns/shared-assets.md` | Manual | `/workato-create recipe`, `/catalog`, `/plan` | Shared asset design policy |
| `docs/patterns/workspace-management.md` | Manual | `/plan`, `/catalog` | Workspace structure and naming conventions |
| Always-on rules | Manual | All skills | JSON format, per-path rules |
| `learned-patterns.md` (kit bundle) | Manual (kit maintainers' temporary buffer) | Manual (triage work) | Kit canonical buffer. Users use `org/docs/learned-patterns.md` |

### Organization side (`connectors/`, `projects/`, `org/`)

| Path | Writer | Reader | Contents |
|---|---|---|---|
| `connectors/docs/<name>.md` | `/sync-connectors --custom` | `/workato-create recipe`, `/workato-create workflow-app` | Custom connector trigger/action/field specs |
| `connectors/<name>/connector.rb` | `/workato-create connector`, manual | `/sync-connectors --custom` | Custom connector implementation |
| `projects/<name>/specs/<NNN>-<slug>/spec.md` | `/spec` (creation + clarification mode) | `/plan`, `/analyze`, Claude at session start | Feature requirements (WHAT/WHY, no Workato vocabulary) |
| `projects/<name>/specs/<NNN>-<slug>/plan.md` | `/plan` | `/tasks`, `/analyze`, `/workato-create recipe`, `/workato-create workflow-app`, `/learn-recipe` (tidies Unlearned Actions) | Workato configuration (HOW). Includes the Unlearned Actions table |
| `projects/<name>/specs/<NNN>-<slug>/tasks.md` | `/tasks`, `/implement` (check-off), `/learn-recipe` (`[learn]` completion) | `/analyze`, `/implement` | Executable tasks (with `[P]` / type tags) |
| `projects/<name>/DESIGN.md` / `DESIGN.md.legacy.*` | (no writer — legacy format) | `/spec migrate`, manual review | **Deprecated**. Not generated for new projects; convert via `/spec migrate` |
| `projects/<name>/Recipes/*.json` | `/workato-create recipe`, `/pull-project` | `/learn-recipe`, `/validate-recipe`, `/push-project` | Recipe body |
| `projects/CATALOG.md` | `/catalog scan` | `/workato-create recipe`, `/plan` | List of organization shared assets (Recipe Function, Connection) |
| `projects/CATALOG_CONFIG.yaml` | Manual | `/catalog` | Scope settings (global / team / private) |
| `projects/docs/patterns/` | Legacy (no writer; record new entries in `org/docs/patterns/recipe-patterns/`) | `/workato-create recipe`, `/plan`, `/learn-pattern` (read only) | Org-domain patterns recorded in older versions (backward compatibility) |
| `org/docs/connectors/<provider>.md` | `/learn-recipe` | `/workato-create recipe`, `/workato-create workflow-app`, `/workato-create genie` | Corrections / additions to the kit version, org-specific field information |
| `org/docs/logic/`, `org/docs/platform/`, `org/docs/patterns/deployment-guide.md` | `/learn-recipe` | All create-family skills | Corrections / additions to the kit version |
| `org/docs/patterns/recipe-patterns/` | `/learn-pattern` | `/workato-create recipe`, `/plan` | Recipe construction patterns recorded by the organization (both generic and org-domain consolidated here) |
| `org/docs/learned-patterns.md` | `/learn-recipe` (fallback when the destination is undecided) | Manual (triage work) | Org-side temporary buffer |

## Lifecycle principles

### 1. docs-first

Build skills (`/workato-create recipe`, etc.) must **read the docs first**.

- If the information is in the documentation, implement directly from it
- If the information is missing:
  1. Implement as a best-effort implementation (including UI verification)
  2. Append to the **`## Unlearned Actions`** table in the feature's `plan.md`, and add a matching `[learn]` task to `tasks.md` (or record it as a GitHub Issue in this repo)
  3. After implementation, run `/learn-recipe` to enrich the docs. The corresponding entries in plan.md / tasks.md are tidied automatically at the same time
  4. Manually review anything that remains

### 2. Do not grep other projects

Do not grep under `projects/<other-project>/Recipes/` to dig out sample JSON.
Logic, naming, and datapill references that are specific to individual projects leak in as noise, and gaps in the knowledge base stop being visible.

**Exception**: pattern learning is fine (`/learn-pattern` references `docs/patterns/recipe-patterns/`, `org/docs/patterns/recipe-patterns/`, and `projects/docs/patterns/` (legacy)). However, grepping to obtain input/output schemas is not allowed.

### 3. Separation of learning responsibilities

| Learning content | Skill to use | Write target |
|---|---|---|
| Connector field specs (from the official API/SDK) | `/sync-connectors` | `docs/connectors/` (kit canonical), `connectors/docs/` (custom) |
| Connector field specs (from a recipe the org has used) | `/learn-recipe` | `org/docs/connectors/` |
| Reusable construction patterns | `/learn-pattern` | `org/docs/patterns/recipe-patterns/` (both generic and org-domain consolidated here) |
| New findings about JSON structure | `/learn-recipe` | `org/docs/learned-patterns.md` (use this for findings you may later upstream to the kit) |
| datapill reference patterns | `/learn-recipe` | `org/docs/logic/data-pills.md` |

**Key point**: learning skills do not create intermediate files; they append directly to the relevant document. Only `org/docs/learned-patterns.md` is tolerated as a staging area, and even that should be triaged promptly. Learning skills do not write into the kit canonical `docs/` (only kit maintainers and the sync skills do).

### 4. Build skills do not write docs

Build skills like `/workato-create recipe` only generate assets under `projects/`; they do not write to `docs/connectors/` or `docs/patterns/`.
Knowledge writes are the responsibility of the **learning skills** (`/learn-recipe`, `/learn-pattern`, `/sync-connectors`). This separation prevents incorrect information from leaking into the docs as a side effect of building.

## Typical scenarios

### Scenario A: New project (using a connector for the first time)

```
/spec <project>                       # Create spec.md (business requirements, technology-neutral)
                                      # ... and resolve Open Questions in clarification mode
                                      # (resume anytime with /spec <project>/001-<slug>)
/plan <project>/001-<slug>            # Create plan.md (CATALOG / pattern / resource lookup)
/tasks <project>/001-<slug>           # Create tasks.md (tagged task decomposition)
/analyze <project>/001-<slug>         # spec ↔ plan ↔ tasks consistency check
/sync-connectors <provider>           # Fetch metadata for unlearned connectors
/implement <project>/001-<slug>       # Dispatch tasks to /workato-create recipe etc.
/validate-recipe <project>            # Validate JSON structure (usually triggered inside /implement)
/push-project --start                 # Deploy + start (via the [push] task)
(Adjust pick_list etc. in the UI)
/pull-project                         # Pull adjustments (via the [pull] task)
/learn-recipe <project>               # Enrich docs + tidy plan.md / tasks.md [learn] entries
```

### Scenario B: New feature with a known connector

```
/spec <project>                       # For existing projects, the sequence becomes 002, 003...
                                      # (clarification mode resolves Open Questions in the same run)
/plan <project>/<NNN>-<slug>
/tasks <project>/<NNN>-<slug>
/analyze <project>/<NNN>-<slug>
/implement <project>/<NNN>-<slug>
/push-project --start
```

If connector information is already in place, `/sync-connectors` and `/learn-recipe` are not needed.

### Scenario C: Building a custom connector

```
/spec <project>                       # Define the feature that uses the connector
.../tasks                             # tasks.md will include a [connector] task
/implement <project>/<NNN>-<slug>     # /workato-create connector is invoked from the [connector] task
(Implement and test with the Workato SDK)
/sync-connectors --custom <name>      # Update connectors/docs/<name>.md
(Continue /implement to the [recipe] tasks)
```

### Scenario D: Handover (understanding an existing project)

```
/pull-project --all                   # Pull all projects locally
ls projects/<project>/specs/          # Check the feature list
cat projects/<project>/specs/<NNN>-<slug>/spec.md   # Read the requirements
cat .../plan.md                       # Read the Workato configuration
/learn-recipe <project>               # Enrich docs from the implementation
/catalog scan                         # Inventory shared assets
```

### Scenario E: Migrating a legacy DESIGN.md project

```
/spec migrate <project>               # DESIGN.md → specs/001-<slug>/{spec,plan,tasks}.md
/spec <project>/001-<slug>            # Resolve the Open Questions emitted during migration
/analyze <project>/001-<slug>         # Consistency check
# From here, follow Scenario A / B
```

## When you are about to move outside this map

- "Let me grep `projects/<other-project>/Recipes/` to investigate input/output" → **stop**. Read `docs/connectors/<provider>.md`, or run `/sync-connectors` if it does not exist
- "Let me append to `docs/connectors/` while building" → **stop**. Build skills do not write docs. Leave it to `/learn-recipe`
- "Skip the spec and jump straight to implementation" → **stop**. Going through `/spec` → `/plan` → `/tasks` prevents leftover Open Questions and missed Unlearned Actions. Even a one-line `/spec` is fine; tighten it in clarification mode
- "Move to `/plan` while Open Questions remain" → **stop**. Resolve them first via `/spec <project>/<NNN>-<slug>` (clarification mode), then `/plan`. `/plan` halts when it detects unresolved questions
- "Just write DESIGN.md and call it done" → **stop**. The DESIGN.md format is retired. Start from `/spec`. If there is an existing DESIGN.md, convert it with `/spec migrate` to `specs/` and join this flow
- "It's a new connector but let me just try implementing it" → OK, but record it in **plan.md's Unlearned Actions and tasks.md's `[learn]` task**, and run `/learn-recipe` afterward (it tidies automatically)
