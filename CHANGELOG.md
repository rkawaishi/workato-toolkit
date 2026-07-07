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
- Development: dev-session bootstrap (#24), CI lint jobs + release version
  gate + this changelog (#25).

### Changed
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

### Notes
- Claude Code is the only supported editor; Cursor / Codex / Gemini assets
  are frozen in-tree.
