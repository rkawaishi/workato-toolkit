# Changelog

Notable changes to the workato-toolkit plugin. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions follow
[Semantic Versioning](https://semver.org/). A release tag `vX.Y.Z` must match
the `version` in `plugin/.claude-plugin/plugin.json` — `release.yml` enforces
this before publishing. Breaking changes (e.g. skill renames) are called out
explicitly under **Changed**/**Removed**.

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
- Development: dev-session bootstrap (#24), CI lint jobs + release version
  gate + this changelog (#25).

### Notes
- Claude Code is the only supported editor; Cursor / Codex / Gemini assets
  are frozen in-tree.
