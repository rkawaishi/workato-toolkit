# Design philosophy and architecture

This document explains the design decisions of the workato-toolkit and the thinking behind them.

## Core philosophy: complete Workato development inside an AI editor

Workato automation development is normally done in the web UI, but this has several problems:

- **No reproducibility** — UI operations are hard to capture as documented steps and tend to depend on individual knowledge
- **No reviewability** — diffing JSON is difficult
- **Knowledge does not accumulate** — know-how like "this field takes this value" stays in individual memory

This toolkit uses Claude Code to perform **Recipe JSON generation, validation, deployment, and learning** from the codebase.

### Supported editor

**Claude Code is the only officially supported editor.** The plugin is one shared tree — `skills/`, `docs/`, `bin/`, `agents/`, `rules/` — read directly from the installed plugin: skills as `SKILL.md`, always-on rules injected by the SessionStart hook (`bin/session-start-rules` delivers the generated `AGENTS.md`), hooks wired through `hooks/hooks.json`.

Per-editor assets for Cursor / Codex / Gemini (`.mdc` rules, `.toml` agents, `GEMINI.md`, alternate hooks/manifests) remain in the tree but are **frozen** — not generated, maintained, or verified.

> **Knowledge-base reads go through the docs-overlay MCP** (`workato_docs_lookup` / `workato_docs_list`), not local file paths. The MCP resolves the plugin's bundled docs from its own location, and merges in your workspace's `org/docs/` overlay.

For setup instructions, see the [Claude Code quickstart](quickstart-claude-code.md).

## Repository structure

The toolkit is installed as a native plugin **at the editor level**, not vendored into your repo. Your workspace repository therefore holds only your own assets:

```
my-org-workato/               ← organization's workspace repository (working root)
├── projects/                 ← organization's recipes
│   └── <project-name>/
│       ├── specs/
│       ├── Recipes/
│       └── ...
├── connectors/               ← organization's custom connectors
│   └── <name>/connector.rb
└── org/docs/                 ← organization's accumulated knowledge (overlay; git-shared with your team)
```

The plugin itself bundles the shared tree (`skills/`, `docs/`, `bin/`, `agents/`, `rules/`, hooks, and the docs-overlay MCP) and is updated with `/plugin update workato-toolkit`.

### Separation of framework and organization data

| Aspect | Framework (bundled in the plugin) | Organization data (projects/ connectors/ org/docs/) |
|---|---|---|
| Change frequency | When skills improve | Daily development work |
| Sharing scope | Across team and organization | Project-specific |
| Confidentiality | Low (general knowledge) | High (connection settings, business logic) |
| How it evolves | PRs to the `workato-toolkit` repository | Commits to the workspace repository |

The plugin's bundled knowledge base is read-only and is served through the docs-overlay MCP.

## Knowledge hierarchy

When AI generates a Recipe, it consults knowledge in the following priority order:

```
1. docs/connectors/         ← Pre-built connector specs (highest priority, kit canonical)
                              + org/docs/connectors/  ← org-side corrections/additions (read alongside)
2. connectors/docs/         ← custom connector specs
3. docs/logic/              ← how to compose logic steps
                              + org/docs/logic/       ← org-side corrections (read alongside)
4. docs/platform/           ← platform features
                              + org/docs/platform/    ← org-side corrections (read alongside)
5. always-on rules          ← JSON format rules (delivered with the plugin)
6. docs/patterns/recipe-patterns/      ← Recipe construction patterns (kit canonical, via the MCP)
   + org/docs/patterns/recipe-patterns/ ← patterns recorded by the org (write target)
   + projects/docs/patterns/           ← legacy (read-only)
7. docs/patterns/           ← deployment guides, etc.
```

In case of conflict, **the org side wins** (see the `org-knowledge-overlay` rule, always-on). Kit docs (items 1–4, 6–7) are read through the docs-overlay MCP, which merges them with the workspace `org/docs/` overlay.

This hierarchy is ordered "concrete → abstract". Connector-specific field names and data types are most important; general patterns are used as supporting material.

## Learning cycle

The biggest feature of this toolkit is that **knowledge grows the more you use it**.

```
                    ┌──────────────────────┐
                    │  Adjust in Workato UI │
                    └──────────┬───────────┘
                               ▼
              Pull JSON with /pull-project
                               │
                    ┌──────────▼───────────┐
                    │  /learn-recipe       │
                    │  /learn-pattern      │── reflected in knowledge
                    │  /sync-connectors   │
                    └──────────┬───────────┘
                               ▼
           Knowledge accumulates in org/docs/
                               │
                    ┌──────────▼───────────┐
                    │  /create-recipe      │
                    │  /plan               │── used for the next build
                    └──────────────────────┘
```

Workato JSON contains many fields that can only be set via the UI and many undocumented structures. Running the adjust-in-UI → pull → learn cycle accumulates this tacit knowledge in the knowledge base.

For details, see the [knowledge management guide](knowledge-management.md).

## Spec-driven development

Each feature in each project is managed under `projects/<project>/specs/<NNN>-<slug>/` across three files:

- **`spec.md`** — user experience and business requirements (WHAT/WHY, no Workato terminology)
- **`plan.md`** — Workato composition (HOW, Data Table / Recipe / Connection / applied patterns / Unlearned Actions)
- **`tasks.md`** — executable tasks (`[P]` parallel marker + tags like `[recipe]` / `[page]` / `[learn]`)

Proceed in the order `/spec` → `/clarify` → `/plan` → `/tasks` → `/analyze` → `/implement`. For resilience to interruption, Open Questions are persisted in spec.md and can be resumed with `/clarify`.

> The legacy single-file DESIGN.md format is migrated into specs/ via `/design migrate`. `/design new` is retired (see the Deprecation phase in [lifecycle and responsibility map](lifecycle.md)).

## Skill system

Skills cover each phase of the development lifecycle:

| Phase | Skills | Role |
|---|---|---|
| **Setup** | `/setup-workspace`, `/issue-api-keys` | Workspace bootstrap and per-environment agent keys |
| **Specification** | `/spec`, `/clarify` | Create spec.md and resolve Open Questions |
| **Design** | `/plan`, `/tasks`, `/analyze` | Generate plan.md / tasks.md and check consistency |
| **Build** | `/implement`, `/create-recipe`, `/create-workflow-app`, `/create-genie`, `/create-connector` | Asset generation |
| **Validation** | `/validate-recipe` | JSON structure check |
| **Sync** | `/push-project`, `/pull-project` | Sync with Workato (dev) |
| **Promotion** | `/deploy-project` | dev→test→prod promotion via the Deploy feature |
| **Learning** | `/learn-recipe`, `/learn-pattern`, `/sync-connectors` | Knowledge accumulation |
| **Organization** | `/catalog` | Inventory of shared assets |
| **Legacy** | `/design migrate` | Migration tool from legacy DESIGN.md → specs/ |

For details on each skill, see the [skill reference](skills-reference.md).

## Rule system

The toolkit's always-on rules are auto-applied according to path patterns:

| Rule | Target path | Content |
|---|---|---|
| `workato-recipe-format.md` | `Recipes/**` | Recipe JSON structure and field specifications |
| `workato-agentic-format.md` | `Agents/**` | Genie/Skill/MCP JSON specifications |
| `workato-page-components.md` | `Pages/**` | Page component specifications |
| `workato-connector-sdk.md` | `connectors/**` | Connector SDK format |
| `workato-project-structure.md` | `projects/**` | Project structure rules (including criteria for shared assets) |
| `workato-cli.md` | (during CLI operations) | CLI command reference |

Claude Code automatically references the matching rule when editing a file and generates the correct JSON structure.

### Notes for toolkit developers (derived files)

The canonical sources are `rules/*.md`. The single generated file is `AGENTS.md` (the SessionStart payload); frozen per-editor sidecars are never regenerated. After editing a canonical source, regenerate:

```bash
python3 scripts/sync_derived.py
```

Commit the canonical edit and its regenerated derived files together. CI ([.github/workflows/sync-check.yml](../.github/workflows/sync-check.yml)) re-runs the generator and fails on drift.
