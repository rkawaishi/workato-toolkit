# Test suite map

Guards are organized **by subject**, not by the migration phase that introduced
them (issue #27). When adding a guard, put it in the file whose one-liner
matches; shared path constants live in `conftest.py`.

| File | What goes here |
|---|---|
| `test_repo_layout.py` | plugin/-vs-root boundary, frozen assets, marketplace/mcp wiring, test-suite naming conventions |
| `test_skills.py` | skill presence, frontmatter, MCP-reference and bare-path sweeps over `plugin/skills/` |
| `test_skills_service.py` | sentinel guards for the service-integration skills (setup-workspace / issue-api-keys / deploy-project) |
| `test_rules.py` | always-on rule presence and content guards (`plugin/rules/*.md`) |
| `test_agents.py` | subagent definitions (`plugin/agents/`) |
| `test_hooks.py` | hook scripts + hooks.json wiring, hook behavior (stdin-driven runs) |
| `test_docs.py` | knowledge-base tree shape (`plugin/docs/`) + docs served through the overlay |
| `test_overlay.py` | docs-overlay merge logic (pure `overlay.py`) |
| `test_asset_path.py` | `workato_asset_path` allowlist/traversal (pure `assets.py`) |
| `test_bundled_assets.py` | bundled helper/templates presence and contracts |
| `test_manifests.py` | plugin/marketplace manifest shape and versions |
| `test_derived_sync.py` | `sync_derived.py` generation, idempotence, freeze scope |
| `test_guards_stale_tokens.py` | cross-tree stale-token sweeps over user-facing docs (legacy distribution wording, README install surface) |
| `test_dev_env.py` | dev-session bootstrap, CI workflow shape (lint jobs, release gates) |
| `test_dev_docs.py` | dev/ document lifecycle (status frontmatter, index, conventions) |
| `helper/` | unit tests for `plugin/scripts/workato-api.py` |
