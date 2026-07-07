# Skills reference

A reference summarizing the purpose, usage, and options of every skill.

> **For the "when to invoke / what to read / what to write" responsibility map, see [Lifecycle and responsibility map](lifecycle.md).** This reference focuses on the standalone usage of each skill.

## How to invoke a skill

| Editor | How to invoke |
|---|---|
| **Claude Code** | Type `/skill-name` in the prompt |

Skills ship inside the plugin and load automatically from the installed plugin; update them with `/plugin update workato-toolkit`.

## Setup phase (once per workspace)

### /setup-workspace — bootstrap the workspace repository

One-time infrastructure bootstrap: Platform CLI check, materialization of the bundled API
helper and templates (via the docs-overlay MCP's `workato_asset_path`), `org/` directory
skeleton, credential deny-lists, dev-profile setup and verification.

```
/setup-workspace              # Full bootstrap (idempotent)
/setup-workspace --update     # Refresh the materialized scripts after a plugin update
```

Ends by pointing at `/issue-api-keys`, `/pull-project --all`, and `/onboard`.

### /issue-api-keys — per-environment Developer API clients

Design, issue, rotate, revoke, and audit the Developer API clients that agents and CI
authenticate with: dev = write, test/prod = read-only, so the dev-only push policy is
enforced by the keys themselves. Tokens go straight into the OS keyring and are never
displayed.

```
/issue-api-keys               # Plan mode: present the permission design only
/issue-api-keys issue         # Full flow: roles → issue → verify → record
/issue-api-keys rotate <env>  # Rotate one environment's key
/issue-api-keys revoke <env>  # Revoke one environment's client
/issue-api-keys audit         # Compare remote clients against the org record
```

The permission matrix and role checklists live in `platform/developer-api-clients.md`
(via `workato_docs_lookup`); the issuance record goes to
`org/docs/platform/developer-api-clients.md`.

## Onboarding phase (first run)

### /onboard — bootstrap the knowledge base from existing assets

For a workspace that already has Workato projects and custom connectors before the kit was adopted. A **thin orchestrator** that pulls everything and runs the learn / sync / catalog skills so `docs/` and `org/docs/` start out populated with the organization's real patterns, built-in actions and schemas.

```
/onboard                          # Onboard every remote project and connector
/onboard --projects "<a>","<b>"   # Limit to specific projects
/onboard --resume                 # Continue an interrupted run
/onboard --dry-run                # Show the plan only
```

- Sequences `/pull-project --all` → `/sync-connectors --all` → `/learn-recipe` (per project) → `/learn-pattern` → `/catalog scan`. It never reimplements them.
- Resumable: progress is tracked per step / per project in `org/onboarding-report.md`, which also becomes the final summary.
- CLI / API only — no browser required. Use `/auto-learn` afterward for browser-based deep dives on heavily-used connectors.

## Specification and design phases

### /spec — create feature requirements

Organize the business requirements (WHAT/WHY) in business language and generate `spec.md`. Workato vocabulary is forbidden.

```
/spec <project-name>       # Create spec.md from an interview
```

**Interview items:**
1. Who wants to do what (in business language)
2. What flow they have in mind
3. Who is involved
4. What needs to happen for success
5. Whether there are existing tools or data sources

**Output:** `projects/<project>/specs/<NNN>-<slug>/spec.md` (User Stories, Success Criteria, Out of Scope, Open Questions)

Add `specs/` to `.workatoignore` so that `workato pull` does not remove it.

### /clarify — resolve Open Questions

Walk through `## Open Questions` in spec.md one item at a time with the user and reflect the answers into the spec body. Also serves as a resume command after interruptions or context exhaustion.

```
/clarify <project>/<NNN>-<slug>
```

### /plan — translate into Workato configuration (HOW)

Cross-read spec.md with `projects/CATALOG.md` / `.resource-providers.yml` / the pattern catalog, and write the concrete Workato configuration (Data Table / Recipe / Connection / Stage Transitions / Reused Assets / New Components / Unlearned Actions) into `plan.md`.

```
/plan <project>/<NNN>-<slug>
```

**Key points:**
- Halts if `## Open Questions` remains (run `/clarify` first)
- State reuse of existing shared assets explicitly under `## Reused Assets`
- Record actions that are missing from the documentation in the `## Unlearned Actions` table (they become `[learn]` tasks via `/tasks`)

### /tasks — decompose into executable tasks

Decompose plan.md into executable tasks in `tasks.md`, attaching the parallel marker `[P]` and type tags such as `[recipe]` / `[page]` / `[data-table]` / `[connection]` / `[mcp]` / `[connector]` / `[learn]` / `[test]`.

```
/tasks <project>/<NNN>-<slug>
```

### /analyze — consistency check

Verify the consistency of `spec.md` ↔ `plan.md` ↔ `tasks.md` in read-only mode and report contradictions, gaps, and duplicates.

```
/analyze <project>/<NNN>-<slug>
```

### /design — deprecated (migration tool only)

> ⚠️ `/design` has been migrated to the spec-driven workflow. Do not use it for new projects.

Only `/design migrate` remains useful as a standard-operation subcommand:

```
/design migrate <project>  # Migrate an existing DESIGN.md into specs/<NNN>-<slug>/{spec,plan,tasks}.md
/design <project>          # Display legacy DESIGN.md (compatibility mode with warning)
/design update             # Update legacy DESIGN.md (compatibility mode with warning)
```

- `/design new` has been **retired** (if invoked, refuse and direct the user to `/spec`)
- For projects with an existing DESIGN.md, convert it to `specs/` early via `/design migrate`
- See the Deprecation phase in [Lifecycle and responsibility map](lifecycle.md) for details

---

## Build phase

### /workato-create recipe — generate recipe JSON

Decide the recipe's purpose, trigger, and actions interactively, and generate `.recipe.json` and `.connection.json`.

```
/workato-create recipe             # Generate a recipe interactively
```

**Workflow:**
1. Confirm the recipe's purpose, trigger, and actions
2. Search the shared asset catalog (`CATALOG.md`) for reusable connections and Recipe Functions
3. Check field specs in the connector knowledge base (`docs/connectors/`)
4. Interview the user to determine input field values
5. Propose applicable patterns from the pattern catalog (`docs/patterns/recipe-patterns/`)
6. Generate the JSON and guide the user through deployment

**Three categories of field values:**
- **Auto-determined**: values that can be fixed from the knowledge base
- **Needs confirmation**: values that can be inferred but require user confirmation
- **Connection-dependent**: values that can only be known after connection authentication (e.g. `pick_list` in object definitions)

### /workato-create workflow-app — build a Workflow App

Build a Workflow App such as an approval workflow in JSON.

```
/workato-create workflow-app       # Build a Workflow App interactively
```

**Assets generated:**
- Data Table schemas (`.data_table.json`)
- Page definitions (`.page.json`) — request form, review screen, completion screen
- App definition (`lcap_app.json`) — stage transitions and page bindings
- Related recipes — delegated to `/workato-create recipe`

**The only UI operation**: enabling the Workflow App (Settings → Workflow Apps)

See [Workflow App build guide](workflow-apps.md) for details.

### /workato-create genie — generate a Genie & MCP

Generate an AI agent (Genie) and its skills, and optionally an MCP server.

```
/workato-create genie              # Generate a Genie configuration interactively
```

**Assets generated:**
- `.agentic_genie.json` — Genie definition (instructions, AI model settings)
- `.agentic_skill.json` — skill definition (parameters, trigger settings)
- `.mcp_server.json` — MCP server definition (optional)
- Skill recipes — delegated to `/workato-create recipe`

See [Genie & MCP build guide](genie-and-mcp.md) for details.

### /workato-create connector — generate a custom connector

Scaffold a Connector SDK project and generate `connector.rb`.

```
/workato-create connector          # Generate a custom connector interactively
```

**Files generated:**
- `connector.rb` — main connector definition
- `settings.yaml` — credential template
- `Gemfile` — dependencies
- `.gitignore` — excludes secrets
- `README.md` — setup instructions

See [Custom connector development guide](connector-development.md) for details.

---

## Validation phase

### /validate-recipe — JSON structure validation

Validate recipe and Genie JSON files and report issues.

```
/validate-recipe <file>            # Validate a specific file
/validate-recipe <project-name>    # Validate the whole project
```

**Validation targets and main checks:**

| File type | Checks |
|---|---|
| `.recipe.json` | Required fields, step number continuity, UUID format, datapill reference resolution, filter conditions |
| `.agentic_genie.json` | Required fields, skill reference consistency, presence of instructions |
| `.agentic_skill.json` | Required fields, recipe reference, trigger type |
| `.connection.json` | Required fields |

**Output format:** ✅ OK / ⚠️ Warning / ❌ Error

---

## Sync phase

### /pull-project — pull from Workato

Pull project assets from the Workato remote to local.

```
/pull-project                     # Pull the current project
/pull-project --all               # Pull all remote projects
/pull-project --list              # List remote projects
```

**Post-pull actions:**
- Report changed files
- If new patterns are found, suggest running `/learn-recipe`

### /push-project — push to Workato

Push local changes to the Workato remote. Runs validation before pushing.

```
/push-project                     # Validate → push
/push-project --start             # Start recipes after push
/push-project --test              # Run a test and check the job after push
/push-project --restart-recipes   # Restart existing running recipes
/push-project --delete            # Delete assets that have been removed from the remote
```

**Push flow:**
1. JSON syntax check (all assets)
2. Existence check for `extended_output_schema`
3. Detect new connections → **two-phase push**
   - Phase 1: push connections only → authenticate in the UI
   - Phase 2: push the remaining assets
4. Execute the push
5. Guide for the follow-up steps per asset type

**Reason for the two-phase push:** if a connection is unauthenticated, the recipe's `pick_list` fields cannot be resolved and the push fails.

See [Deployment procedure guide](deployment.md) for details.

---

## Promotion phase

### /deploy-project — promote between environments

Promote a project dev→test→prod with Workato's Deploy feature (auditable manifests, not
direct writes). Wraps the API helper's transition-guarded `deploy` commands; skip-tier and
backward transitions are refused, prod runs require explicit human confirmation, and
deployment approval always stays with the release manager in the UI.

```
/deploy-project                        # Preview a dev→test deploy (read-only)
/deploy-project preview --to <env>     # Preview a specific transition
/deploy-project run --to <test|prod>   # Execute (guarded)
/deploy-project status <id> [--wait]   # Check / follow one deployment
/deploy-project list                   # Deployment history (audit)
```

Prints the per-environment checklist (connection credentials, environment properties,
table seeds, connector releases, recipe starts) on every run.

---

## Learning phase

### /learn-recipe — learn from recipes

Parse pulled recipe JSON and append findings directly to the knowledge base.

```
/learn-recipe <file>       # Learn from a specific recipe
/learn-recipe <project>    # Learn from the whole project
```

**Learning targets and write destinations:**

| Finding | Destination |
|---|---|
| Field information (`extended_output_schema`, etc.) | `org/docs/connectors/<provider>.md` |
| New provider / action | `org/docs/connectors/` or `org/docs/platform/` |
| New finding about JSON structure | `org/docs/learned-patterns.md` |
| datapill pattern | `org/docs/logic/data-pills.md` |
| Deployment-related finding | `org/docs/patterns/deployment-guide.md` |

### /learn-pattern — record a construction pattern

Record expert knowledge in the pattern catalog.

```
/learn-pattern             # Record a pattern interactively
```

**Pattern structure:**
- Usage conditions (when to apply this pattern)
- Recipe structure diagram
- Step composition details
- Design decision points
- Known pitfalls

**Destination:** `org/docs/patterns/recipe-patterns/<name>.md` (both generic and org-domain consolidated here; the distinction is expressed in the "Scope" section of the pattern body)

See [Knowledge management guide](knowledge-management.md) for details.

### /sync-connectors — sync connector information

Gather information about pre-built and custom connectors and update the documentation.

```
/sync-connectors <provider>        # Sync a specific connector
/sync-connectors --custom          # Sync custom connectors only
/sync-connectors --all             # Sync all connectors
```

**Pre-built connectors:**
- Fetch trigger/action metadata via the Workato API
- Create or update `org/docs/connectors/<provider>.md`

**Custom connectors:**
- Parse `connectors/*/connector.rb` via the Ruby DSL parser
- Create or update `connectors/docs/<name>.md`

### /auto-learn — autonomously collect all ops from the Workato UI

Drive the Workato UI through the Claude in Chrome extension to actively collect input / output fields for every operation (trigger / action) of a single connector per run and append them to `org/docs/connectors/<provider>.md`.

```
/auto-learn <provider>                 # Learn all ops
/auto-learn <provider> --triggers-only # Triggers only
/auto-learn <provider> --actions-only  # Actions only
/auto-learn <provider> --force         # Overwrite even already-learned ops
```

**Design principles (important):**
- **No interaction**: try every op in a single invocation. If there is no basis for a decision, defaults → skip + log
- **Fail soft**: a single op failure must not stop the whole run
- **UI only**: new fetch / XHR calls to the Workato internal API are prohibited (passive observation of responses caused by UI operations is allowed)
- **Coverage over completeness**: leave fine corrections to `/learn-recipe` afterward

**Prerequisites:**
- The [Claude in Chrome](https://chrome.google.com/webstore) extension is installed and connected
- Works only with Claude Code (Cursor / Codex / Gemini do not have Chrome MCP)

While `/sync-connectors` performs metadata collection (API-based), `/auto-learn` is the counterpart that fetches the actual fields and dynamic schemas through UI operations.

---

## Cleanup phase

### /catalog — catalog shared assets

Scan the organization's shared projects and catalog reusable assets.

```
/catalog                   # Scan shared assets and generate the catalog
```

**Scan targets:**
- Connections (name, provider)
- Recipe Functions (with input/output schemas)
- Workflow Apps
- MCP servers

**Output:** `projects/CATALOG.md` — referenced by `/workato-create recipe` and `/plan` to suggest reuse of existing assets.

**Scope control:** configure `global` / `team:<name>` / `private` in `projects/CATALOG_CONFIG.yaml`. `private` projects are not included in the catalog.
