# P6 Runtime-Verification → Release Roadmap (consolidated)

> **For workers:** This is a ROADMAP plan, not a pure TDD plan. Phases A–B are mostly **manual runtime verification** across editors (install the plugin, observe) with pass/fail criteria + an on-fail action; Phases C–E are execution. Steps use checkbox (`- [ ]`). Each step is tagged **[manual]** (a human must run an editor), **[code]** (an automatable change), or **[ops]** (git/GitHub/release action). Execute A → B → C → D; E is independent.

**Goal:** Take `workato-toolkit` from "release-prepped" (P5 merged) to "verified & released as a native plugin on CC / Cursor / Codex (Gemini after §B)", and close the remaining context-hygiene item.

**Architecture:** Shared-tree plugin (see `docs/guides/architecture.md` + design spec `superpowers/2026-06-07-workato-toolkit-plugin-distribution-design.md`). Per-editor sidecars: `.claude-plugin/` `.cursor-plugin/` `.codex-plugin/` `.agents/plugins/marketplace.json` `.mcp.json` `.codex.mcp.json` `hooks/{hooks,cursor,codex}.hooks.json` `bin/session-start-rules`. No `gemini-extension.json` yet.

**Status of prior phases:** P1–P5 complete & merged (main `d8a335e`). P4 covered learning-WRITE only; **runtime verification was explicitly deferred to here**. P5 covered release *prep* only.

**Source of truth for this backlog:** P3c handover `next` section (`.claude/handovers/2026-06-07_2332.md`) + P4/P5 code-review follow-ups + issue #6.

---

## Phase A — Runtime verification (CC / Cursor / Codex)

Install the plugin from the GitHub remote in each editor and confirm the wiring actually fires. Do this against a **scratch workspace** (empty git repo with a dummy `master.key`, `settings.yaml`, and a `projects/` dir) so credential-guard and org/docs resolution can be observed.

- [ ] **A1 [manual] CC: marketplace add + install + skill fires.** `/plugin marketplace add rkawaishi/workato-toolkit` → `/plugin install workato-toolkit@workato-toolkit` → run `/ping`. **Pass:** ping skill responds. **On fail:** check `.claude-plugin/marketplace.json` (`source: "./"`) + `plugin.json`.

- [ ] **A2 [manual] CC: `${CLAUDE_PLUGIN_ROOT}` SessionStart injection fires.** Start a fresh CC session in the scratch workspace. **Pass:** the always-on Workato rules appear in context (the SessionStart hook `bin/session-start-rules` injected `AGENTS.md`). **On fail:** inspect `hooks/hooks.json` SessionStart entry + plugin-root var expansion.

- [ ] **A3 [manual] CC: docs-overlay MCP loads + `workato_docs_lookup` callable.** In the CC session, confirm the `workato-docs` MCP server started (`.mcp.json`, needs `uv`+`fastmcp`) and call `workato_docs_lookup("connectors/clearbit.md")`. **Pass:** returns merged kit+org content. **On fail:** check `uv` availability on the user's machine + `.mcp.json` command.

- [ ] **A4 [manual+code] allowed-tools vs MCP (review finding #1).** Run a skill that reads via the MCP (e.g. `/learn-recipe`) and confirm `workato_docs_lookup` is *not* blocked by the skill's `allowed-tools` (skills currently list only `Read,Write,Edit,Glob,Grep[…]`, no `mcp__…`). **Pass (no gate):** call succeeds → document that session-level MCP isn't gated by skill allowed-tools; no change. **On fail (gated):** **[code]** add the docs-overlay MCP tool names to each skill's `allowed-tools` frontmatter (learn-recipe, learn-pattern, sync-connectors, auto-learn, create-recipe, plan, analyze, tasks, push-project — every skill that calls it) and regenerate nothing (skills aren't derived). Add a test guard.

- [ ] **A5 [manual] CC: credential-guard hook fires.** Ask the agent to `cat master.key`. **Pass:** blocked by `bin/block-credential-read.sh` (PreToolUse). **On fail:** check `hooks/hooks.json` PreToolUse wiring + `credential-patterns.txt` path resolution (`../`).

- [ ] **A6 [manual] Cursor: install + `.mdc` alwaysApply + hooks + `./bin/` resolution.** Install via Cursor Plugins (`source: rkawaishi/workato-toolkit`). **Pass:** a `/skill` runs; the aggregate `workato-project.mdc` rule is always-applied; `cursor.hooks.json` hooks fire and resolve `./bin/` scripts. **On fail:** record which of (.mdc load / hooks accept / relative bin path) broke.

- [ ] **A7 [manual] Codex: marketplace discovery + install + skill (`$skill`) fires.** **Verify the real CLI syntax first** — the README currently documents `codex plugin marketplace add rkawaishi/workato-toolkit` but design §6.1 says Codex uses **auto-discovery of `.agents/plugins/marketplace.json`**, so the documented command may be wrong (P5 review finding). **Pass:** plugin installs and `$ping` works. **On fail / wrong command:** **[code]** correct the Codex install steps in `README.md` + `docs/guides/` to the real mechanism; update `.agents/plugins/marketplace.json` `source` if it points local instead of the GitHub remote.

- [ ] **A8 [manual+code] Codex: SessionStart support (P3c TODO ①).** Determine whether Codex honors a SessionStart hook. **Pass (supported):** rules inject via `bin/session-start-rules`; keep `codex.hooks.json` SessionStart entry. **On fail (unsupported):** **[code]** remove the SessionStart entry from `hooks/codex.hooks.json` and document that Codex relies on `AGENTS.md` discovery instead; add/adjust a manifest test.

- [ ] **A9 [manual] Codex: `$PLUGIN_ROOT` MCP + credential guard.** Confirm `.codex.mcp.json` (`${PLUGIN_ROOT}`) starts the docs MCP and the Bash-only credential guard blocks `cat master.key`. **Pass:** both work. **On fail:** record the gap (Codex guard is Bash-only by design — accept).

- [ ] **A10 [code] auto-learn Chrome MCP tool-name casing (P4 out-of-scope note).** `skills/auto-learn/SKILL.md` `allowed-tools` lists `mcp__Claude_in_Chrome__*` but the runtime exposes `mcp__claude-in-chrome__*` (lowercase/hyphen). Fix the casing once confirmed against the running Chrome MCP. **Pass:** auto-learn's browser tools resolve. Add a guard if practical.

- [ ] **A11 [ops] Record results.** Capture pass/fail per editor in a short `docs/guides/` note or the next handover; list any conditional [code] fixes applied. Phase A is done when CC + Cursor + Codex all pass A1–A9 (with fixes committed).

---

## Phase B — Gemini enablement (design §6.2.4, currently "coming soon")

- [ ] **B1 [code] Add `gemini-extension.json`** at repo root declaring the extension (name, version, `contextFileName: GEMINI.md`, skills dir). Mirror the other manifests; align version to the current release.

- [ ] **B2 [manual] Verify 4-manifest coexistence + shared `skills/` read on Gemini.** `gemini extensions install rkawaishi/workato-toolkit --ref <tag>`. **Pass:** Gemini loads `GEMINI.md` (always-on rules) + reads shared `skills/` + the other editors are unaffected (each ignores foreign manifests). **On fail (design §6.2.4 fallback):** split Gemini into a separate branch/repo; do NOT block CC/Cursor/Codex release.

- [ ] **B3 [code] Flip "coming soon" → supported** in `README.md` + `docs/guides/README.md` + `docs/guides/skills-reference.md` once B2 passes. Add a Gemini quickstart if warranted. Update the P5 `_LEGACY`/coverage guards if they assert Gemini status.

---

## Phase C — Release execution (depends on Phase A green)

- [ ] **C1 [ops] Confirm release version.** Manifests are at `0.1.0` (P5). Decide first public tag (`v0.1.0`).

- [ ] **C2 [ops] Cut the tag.** `git tag v0.1.0 && git push origin v0.1.0` (from `main`). **Pass:** `release.yml` runs green (derived-sync scoped check + `pytest tests/` + GitHub Release published). **On fail:** read the Actions log; fix; delete+re-tag.

- [ ] **C3 [manual] Fresh-install smoke test from the GitHub remote** in each of CC / Cursor / Codex at tag `v0.1.0` (a clean machine/profile, not the dev checkout). **Pass:** install + `/ping` + one `workato_docs_lookup` call succeed. This is the real "CC marketplace → GitHub remote" switch confirmation (P2-deferred item).

- [ ] **C4 [ops] Document pinning.** Confirm README's pin guidance (Gemini `--ref`, tag-based for others) matches what actually works post-release.

---

## Phase D — Old repo deprecation (separate repo: `/Users/ryotaro/workspace/workato-dev-kit`)

- [ ] **D1 [ops] Add a deprecation banner** to `workato-dev-kit/README.md` top: "Frozen — development moved to `rkawaishi/workato-toolkit`; install as a plugin (link)." Keep code frozen (security-only changes).
- [ ] **D2 [ops] (optional) Archive** the dev-kit repo on GitHub once the toolkit release is confirmed working, or leave it read-only with the banner. Confirm with the user before archiving (irreversible-ish, outward-facing).

---

## Phase E — Context hygiene: issue #6 (independent)

- [ ] **E1 [decision]** Pick the CLAUDE.md/rules reduction approach from issue #6 (move heavy format-reference rules to on-demand docs / condense in place / both). This changes product behavior (always-on → on-demand), so it needs a user decision.
- [ ] **E2 [code]** Execute the chosen option **on `rules/*.md`** (the source), then `python3 scripts/sync_derived.py` to regenerate `CLAUDE.md`/`AGENTS.md`/`GEMINI.md`/`.mdc`; commit derived together; `sync-check.yml` guards drift. If moving rules to docs, ensure the docs-overlay MCP serves the new paths and add pointer text so discoverability is preserved.

---

## Notes / risks carried in

- **Codex install command** in README is **unverified** (A7) — highest-confidence "might be wrong" item.
- **MCP `allowed-tools`** (A4) may or may not gate session-level MCP; verify before mass-editing frontmatter.
- Phase A is **gating** for Phase C — do not tag a release until CC/Cursor/Codex pass.
- Gemini (B) and issue #6 (E) are **non-blocking** for the 3-editor release.
- The `superpowers/` plan docs (incl. this one) are intentionally **uncommitted**, matching P1–P5.
