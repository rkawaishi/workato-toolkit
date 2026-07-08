# Changelog

Notable changes to the workato-toolkit plugin. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions follow
[Semantic Versioning](https://semver.org/). A release tag `vX.Y.Z` must match
the `version` in `plugin/.claude-plugin/plugin.json` AND have a `## [X.Y.Z]`
section here — `release.yml` enforces both before publishing (move the
`[Unreleased]` content under a versioned heading when cutting a release).
Breaking changes (e.g. skill renames) are called out explicitly under
**Changed**/**Removed**.

## [Unreleased]

Initial public release preparation (`0.1.0` pending runtime verification —
see issue #10 / P6 Phase A).

### Added
- Plugin distribution: skills, knowledge base served via the docs-overlay MCP
  (`workato_docs_lookup` / `workato_docs_list` / `workato_asset_path`),
  always-on rules injected by the SessionStart hook, credential-guard and
  validate-before-push hooks.
- Service-integration skills: `/setup-workspace`, `/issue-api-keys`,
  `/deploy-project`; bundled `workato-api.py` helper materialized into the
  workspace.
- Operations skills (operations-lifecycle spec, #44): `/run-recipes` — recipe
  run-state overview and start/stop/restart via the guarded helper; mutations
  are dev-only, with UI guidance + the hotfix path on test/prod profiles.
  `/diagnose-jobs` — dev-side diagnosis-and-fix loop with two entrances
  (failed jobs, start errors), six cause classes, a capped default fix →
  re-push → re-verify cycle (`--no-fix` to suppress), UI-fix handover with
  pull-back round-trip, and unreclaimed-job reporting.
  `/inspect-env` — read-only test/prod inspection: run state vs deploy
  success, job health, temp-copy definition diff against dev, four-class
  triage, environment-config (properties/table-seed) verification, and the
  post-recovery reclaim list.
- Development: dev-session bootstrap (#24), CI lint jobs + release version
  gate + this changelog (#25).
- Knowledge-base value density (#12, Phase 1): every kit connector doc carries
  frontmatter (`source` / `synced_at` / `tier`) so freshness and quality are
  detectable. Tier/source are derived from content (shared rules in
  `scripts/connector_doc_meta.py`, backfilled by
  `scripts/backfill_connector_frontmatter.py`), and a test guard keeps the
  recorded values matching the body. The docs-overlay MCP strips frontmatter
  from served bodies, shows a one-line provenance banner instead, and omits
  frontmatter lines from search results.

### Changed
- Operations-lifecycle integration (#44): `/push-project --test` gains the
  trigger-type injection matrix (webhook / polling / schedule / Workflow App /
  MCP-Genie / table-trigger / API-endpoint) plus the table seed→verify→cleanup
  cycle, and defers recipe start/stop to `/run-recipes`. `/deploy-project` gains
  a rollback checklist (git as the release ledger) and hotfix note, and turns the
  properties/table checklist items into generated named lists. `/workato-create`
  recipes now reference Environment properties instead of hardcoding
  environment-dependent values. The Developer API client permission matrix adds a
  Lookup Tables write row (closing a ReadOnly-role gap) and explicit
  table/connections/activity-log/properties read rows. `--profile` usages
  corrected to precede the subcommand (it is a global flag).
- **BREAKING**: the four asset-creation skills are consolidated into one —
  `/create-recipe`, `/create-genie`, `/create-workflow-app`,
  `/create-connector` are replaced by `/workato-create
  <recipe|genie|mcp-server|workflow-app|connector>` (MCP-server creation is
  now its own subcommand). Type-specific procedures load on demand from
  `references/<type>.md`; the workato-builder subagent fetches its generation
  reference via `workato_asset_path`. (#18)
- **BREAKING**: `/clarify` and `/design` are merged into `/spec` — the
  Open-Questions resolution loop is now `/spec`'s clarification mode
  (`/spec <project>/<NNN>-<slug>`), and legacy DESIGN.md conversion is
  `/spec migrate <project>`; the retired design skill's view/update/new
  modes are dropped. The pipeline is now `/spec` → `/plan` → `/tasks` →
  `/analyze` → `/implement`. (#20)
- User-facing docs and skills now state Claude Code–only support everywhere;
  the Cursor quickstart guide was removed (other-editor assets remain frozen
  in-tree). A test guard keeps multi-editor support claims out of shipped
  content. (#11)

### Fixed
- docs-overlay MCP server failed to start whenever the workspace (or this
  repo) contains a `pyproject.toml` — `uv run` tried to adopt it as the
  project. Both `.mcp.json` launch definitions now pass `--no-project`.
  (Found by the self-install smoke, #28.)
- workato-builder subagent dependency (#22): the generation references pointed
  the builder at format-spec rules by naming them "(always-on)", which a
  subagent cannot load. The four format rules (`workato-recipe-format`,
  `workato-agentic-format`, `workato-connector-sdk`,
  `workato-project-structure`) are now reachable via
  `workato_asset_path("rules/<rule>.md")` — the same self-resolving mechanism
  the builder already uses for its generation references, keeping `rules/` the
  single source of truth. The runtime check (can a subagent call MCP tools at
  all?) is added to the self-install smoke's manual checklist for #32 Phase A.

### Notes
- Claude Code is the only supported editor; Cursor / Codex / Gemini assets
  are frozen in-tree.
