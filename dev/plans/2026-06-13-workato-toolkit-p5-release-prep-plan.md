---
status: done
---

# P5 Release-Prep Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `workato-toolkit` releasable as a native plugin for Claude Code / Cursor / Codex — a tag-triggered release workflow, a plugin-native README + install/security docs, version-bumped manifests, and a clean break of all guides from the old submodule/`setup.sh` distribution model.

**Architecture:** The repo is already a shared-tree plugin (design §3). P5 adds the release/CI surface and rewrites user-facing docs from the frozen submodule model to the plugin model. No code/skill behavior changes. Verification is doc-token guards + manifest/version guards + a release-workflow shape guard (pytest), mirroring the existing `tests/test_*_migration.py` style.

**Tech Stack:** GitHub Actions (`release.yml`), JSON manifests, Markdown docs, Python `pytest` guards.

**Scope (locked 2026-06-13):**
- IN: `release.yml`; README install rewrite (CC + Cursor + Codex official, Gemini "coming soon"); security/ignore snippets (`permissions.deny` + `.codexignore`/`.cursorignore`/`.geminiignore`); version bump (0.0.1 → 0.1.0); refresh all 7 guides + README off the submodule/`setup.sh`/`sync_agents.py`/`framework/` model; refresh `credential-patterns.txt` header.
- OUT (separate effort): editing the separate `workato-dev-kit` repo's deprecation notice; cutting the actual git tag / running the release. Gemini manifest (`gemini-extension.json`) — deferred to P4 runtime verification per design §6.2.4.

---

## Shared content (referenced by tasks — use verbatim)

### S1 — Canonical plugin install blocks

**Claude Code**
```
/plugin marketplace add rkawaishi/workato-toolkit
/plugin install workato-toolkit@workato-toolkit
```

**Cursor**
```
# Cursor → Settings → Plugins → Add marketplace
#   source: rkawaishi/workato-toolkit
# then install "workato-toolkit"
```

**Codex CLI**
```
codex plugin marketplace add rkawaishi/workato-toolkit
codex plugin add workato-toolkit
```

**Gemini CLI** — *Coming soon* (pending runtime verification; will be `gemini extensions install rkawaishi/workato-toolkit --ref vX.Y.Z`).

### S2 — Canonical update blocks

**Claude Code:** `/plugin update workato-toolkit`
**Codex CLI:** `codex plugin update workato-toolkit`
**Cursor:** update from the Plugins panel.

Pin a version with a release tag where supported (Gemini `--ref vX.Y.Z`). The plugin bundles `skills/`, `docs/`, `bin/`, `agents/`, `rules/`, hooks, and the docs-overlay MCP — there is **no submodule, no `setup.sh`, and no symlinks** to maintain.

### S3 — Security snippets (the plugin cannot ship a deny-list; users add these to their workspace)

The bundled credential-guard **hook** is the primary defense and ships with the plugin. As defense-in-depth, add these to your workspace repo so the agent cannot read secret files even outside the hook:

**Claude Code** — `.claude/settings.json`:
```json
{
  "permissions": {
    "deny": [
      "Read(./**/master.key)",
      "Read(./**/settings.yaml)",
      "Read(./**/settings.yaml.enc)",
      "Read(./**/.resource-providers.yml)",
      "Read(./**/.env)",
      "Read(./**/.env.*)",
      "Read(./**/*.key)",
      "Read(./**/*.pem)",
      "Read(./**/*.secret)",
      "Read(./**/*.credential*)"
    ]
  }
}
```

**Codex / Cursor / Gemini** — create `.codexignore` / `.cursorignore` / `.geminiignore` at the workspace root with the same patterns:
```gitignore
master.key
settings.yaml
settings.yaml.enc
.resource-providers.yml
.env
.env.*
*.key
*.pem
*.secret
*.credential*
```
> `.workatoenv` is intentionally NOT excluded — it holds only project/folder/workspace IDs (no tokens) and must stay readable.

### S4 — Forbidden legacy tokens (the doc-refresh objective)

After P5, no file under `docs/guides/` and no `README.md` may contain any of:
`submodule`, `setup.sh`, `sync_agents.py`, `framework/`, `kit/setup.sh`, `@local`.
(Guides describe the plugin model only; old-submodule migration guidance is out of scope — it belongs in the frozen `workato-dev-kit` repo.)

---

## File Structure

- Create: `.github/workflows/release.yml` — tag-triggered: verify derived sync, run tests, publish GitHub Release.
- Create: `tests/test_release_p5.py` — guards for: no legacy tokens in docs; manifest versions bumped+consistent; release workflow shape; README install coverage.
- Modify: `.claude-plugin/plugin.json`, `.codex-plugin/plugin.json`, `.cursor-plugin/plugin.json` — `version` → `0.1.0`.
- Modify: `README.md` — full plugin-native rewrite (install S1, update S2, security S3, status).
- Modify (rewrite off submodule → plugin): `docs/guides/quickstart-claude-code.md`, `docs/guides/quickstart-cursor.md`, `docs/guides/architecture.md`.
- Modify (targeted edits): `docs/guides/lifecycle.md`, `docs/guides/knowledge-management.md`, `docs/guides/skills-reference.md`, `docs/guides/README.md`.
- Modify: `credential-patterns.txt` — header comment refresh (consumed by the hook + documented as ignore snippets; `setup.sh` no longer generates them).

> Plans live in `superpowers/` (untracked, matching P1–P4); this file is intentionally not committed.

---

## Task 1: Test guards (RED)

**Files:**
- Create: `tests/test_release_p5.py`

- [ ] **Step 1: Write the guards**

```python
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GUIDES = ROOT / "docs" / "guides"
README = ROOT / "README.md"

# S4 legacy distribution tokens — must be gone from user-facing docs.
_LEGACY = re.compile(r"submodule|setup\.sh|sync_agents\.py|framework/|@local")

EXPECTED_VERSION = "0.1.0"


def _doc_files():
    return [README] + sorted(GUIDES.glob("*.md"))


def test_no_legacy_distribution_refs_in_docs():
    offenders = []
    for p in _doc_files():
        for i, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
            if _LEGACY.search(line):
                offenders.append(f"{p.relative_to(ROOT)}:{i}: {line.strip()}")
    assert not offenders, "legacy submodule/setup.sh refs remain:\n" + "\n".join(offenders)


def _load(rel):
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


def test_manifest_versions_bumped_and_consistent():
    cc = _load(".claude-plugin/plugin.json")["version"]
    codex = _load(".codex-plugin/plugin.json")["version"]
    assert cc == EXPECTED_VERSION, f"CC version {cc} != {EXPECTED_VERSION}"
    assert codex == EXPECTED_VERSION, f"Codex version {codex} != {EXPECTED_VERSION}"


def test_release_workflow_shape():
    wf = (ROOT / ".github" / "workflows" / "release.yml").read_text(encoding="utf-8")
    assert "on:" in wf and "tags:" in wf, "release.yml must trigger on tags"
    assert "scripts/sync_derived.py" in wf, "release.yml must verify derived sync"
    assert "pytest" in wf, "release.yml must run the test suite"
    assert "release" in wf.lower(), "release.yml must publish a release"


def test_readme_covers_plugin_install():
    text = README.read_text(encoding="utf-8")
    # the three official editors' marketplace/install entry points
    assert "/plugin marketplace add rkawaishi/workato-toolkit" in text
    assert "codex plugin marketplace add rkawaishi/workato-toolkit" in text
    assert "Cursor" in text
    # Gemini is deferred, not dropped
    assert "Gemini" in text and "soon" in text.lower()
    # security defense-in-depth is documented
    assert "permissions" in text and "deny" in text
    assert ".codexignore" in text
```

- [ ] **Step 2: Run to verify they FAIL**

Run: `python3 -m pytest tests/test_release_p5.py -v`
Expected: FAIL — `test_no_legacy_distribution_refs_in_docs` (guides/README still have submodule text), `test_manifest_versions_bumped_and_consistent` (0.0.1), `test_release_workflow_shape` (file missing → error), `test_readme_covers_plugin_install` (README is P1 stub).

- [ ] **Step 3: Commit the failing guards**

```bash
git add tests/test_release_p5.py
git commit -m "test(p5): add release-prep guards (RED) — no legacy refs, version bump, release.yml, README install"
```

---

## Task 2: release.yml

**Files:**
- Create: `.github/workflows/release.yml`

- [ ] **Step 1: Write the workflow**

```yaml
name: release

on:
  push:
    tags:
      - "v*"

permissions:
  contents: write

jobs:
  release:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.x"

      - name: Verify derived files are in sync
        run: |
          python3 scripts/sync_derived.py
          git diff --exit-code

      - name: Run test suite
        run: python3 -m pytest -q

      - name: Publish GitHub Release
        uses: softprops/action-gh-release@v2
        with:
          generate_release_notes: true
```

- [ ] **Step 2: Run the release-shape guard**

Run: `python3 -m pytest tests/test_release_p5.py::test_release_workflow_shape -v`
Expected: PASS.

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/release.yml
git commit -m "ci(p5): add release.yml — verify derived sync + tests, publish GitHub Release on tag"
```

---

## Task 3: Version bump manifests

**Files:**
- Modify: `.claude-plugin/plugin.json` (`"version": "0.0.1"` → `"0.1.0"`)
- Modify: `.codex-plugin/plugin.json` (`"version": "0.0.1"` → `"0.1.0"`)
- Modify: `.cursor-plugin/plugin.json` (add `"version": "0.1.0"` after `"name"`)

- [ ] **Step 1: Edit the three manifests**

`.claude-plugin/plugin.json` and `.codex-plugin/plugin.json`: change `"version": "0.0.1"` to `"version": "0.1.0"`.

`.cursor-plugin/plugin.json`: insert `"version": "0.1.0",` immediately after the `"name": "workato-toolkit",` line (Cursor only requires `name`, but keep versions aligned across editors).

- [ ] **Step 2: Run manifest guards**

Run: `python3 -m pytest tests/test_manifests.py tests/test_release_p5.py::test_manifest_versions_bumped_and_consistent -v`
Expected: PASS (existing `test_cc_plugin`/`test_codex_plugin` still green; new version guard green).

- [ ] **Step 3: Commit**

```bash
git add .claude-plugin/plugin.json .codex-plugin/plugin.json .cursor-plugin/plugin.json
git commit -m "chore(p5): bump plugin manifests to 0.1.0"
```

---

## Task 4: README plugin-native rewrite

**Files:**
- Modify: `README.md` (full replacement of body below the title)

- [ ] **Step 1: Replace README.md with the plugin-native version**

```markdown
# workato-toolkit

Workato (enterprise iPaaS) development toolkit for AI coding agents, distributed as a native plugin.
Officially supports **Claude Code**, **Cursor**, and **Codex CLI**. Gemini CLI is coming soon.

The toolkit bundles skills, the Workato knowledge base (300+ connectors, logic, platform, patterns),
always-on rules, a credential-guard hook, and a docs-overlay MCP server — all from one shared tree.
There is no submodule and nothing to symlink.

## Install

### Claude Code
```
/plugin marketplace add rkawaishi/workato-toolkit
/plugin install workato-toolkit@workato-toolkit
```

### Cursor
```
# Cursor → Settings → Plugins → Add marketplace
#   source: rkawaishi/workato-toolkit
# then install "workato-toolkit"
```

### Codex CLI
```
codex plugin marketplace add rkawaishi/workato-toolkit
codex plugin add workato-toolkit
```

### Gemini CLI
Coming soon (pending runtime verification). It will be:
`gemini extensions install rkawaishi/workato-toolkit --ref vX.Y.Z`.

After install, run the `ping` skill to verify the toolkit is loaded.

## Updating

- **Claude Code:** `/plugin update workato-toolkit`
- **Codex CLI:** `codex plugin update workato-toolkit`
- **Cursor:** update from the Plugins panel.

Pin to a release tag where your editor supports it (e.g. Gemini `--ref vX.Y.Z`).

## Security hardening (recommended)

The plugin ships a credential-guard hook that blocks an agent from surfacing secret-file
contents. Because a plugin cannot distribute an editor deny-list, add defense-in-depth to
**your workspace repo**:

### Claude Code — `.claude/settings.json`
```json
{
  "permissions": {
    "deny": [
      "Read(./**/master.key)",
      "Read(./**/settings.yaml)",
      "Read(./**/settings.yaml.enc)",
      "Read(./**/.resource-providers.yml)",
      "Read(./**/.env)",
      "Read(./**/.env.*)",
      "Read(./**/*.key)",
      "Read(./**/*.pem)",
      "Read(./**/*.secret)",
      "Read(./**/*.credential*)"
    ]
  }
}
```

### Codex / Cursor / Gemini — `.codexignore` / `.cursorignore` / `.geminiignore`
Create the matching file at your workspace root:
```gitignore
master.key
settings.yaml
settings.yaml.enc
.resource-providers.yml
.env
.env.*
*.key
*.pem
*.secret
*.credential*
```
> `.workatoenv` is intentionally NOT excluded — it holds only project/folder/workspace IDs (no tokens).

## Documentation

Per-editor quickstarts and architecture live in [`docs/guides/`](docs/guides/). Knowledge-base
docs are served on demand through the docs-overlay MCP (`workato_docs_lookup` / `workato_docs_list`).

## License
MIT
```

- [ ] **Step 2: Run README + token guards**

Run: `python3 -m pytest tests/test_release_p5.py::test_readme_covers_plugin_install -v`
Expected: PASS. (The no-legacy-token guard will still fail until the guides are done — that is expected; this step only proves the README is correct.)

- [ ] **Step 3: Commit**

```bash
git add README.md
git commit -m "docs(p5): rewrite README for plugin install (CC/Cursor/Codex) + security snippets"
```

---

## Task 5: Rewrite quickstart-claude-code.md to the plugin model

**Files:**
- Modify: `docs/guides/quickstart-claude-code.md`

This guide is currently submodule-centric (sections: submodule add + `setup.sh`; "Updating the framework (when using submodule)"; worktree/submodule interaction; "submit a PR to workato-dev-kit"). Rewrite to the plugin model. The objective gate is S4 (zero legacy tokens).

- [ ] **Step 1: Replace the install section** (lines ~18–40, the `git submodule add … / bash kit/setup.sh` block and the `docs/ → kit/docs/` symlink tree) with S1 (Claude Code) and a one-line note: "The plugin bundles everything; there are no symlinks or a `kit/` directory in your workspace."

- [ ] **Step 2: Replace the "Updating the framework" section** (lines ~64–72) with S2 (Claude Code update line).

- [ ] **Step 3: Remove the worktree/submodule section** (lines ~182–215, "`git worktree add` does not populate submodules …" through the shared-`.git/modules/kit` note). Under the plugin model the plugin is install-global, not per-worktree — replace the whole block with: "Worktrees need no special handling — the plugin is installed at the editor level, not vendored into the repo."

- [ ] **Step 4: Fix the contribute note** (line ~169, "submit a PR to workato-dev-kit") → "open a PR against `rkawaishi/workato-toolkit`."

- [ ] **Step 5: Verify no legacy tokens remain in this file**

Run: `grep -nE "submodule|setup\.sh|sync_agents\.py|framework/|@local" docs/guides/quickstart-claude-code.md || echo clean`
Expected: `clean`.

- [ ] **Step 6: Commit**

```bash
git add docs/guides/quickstart-claude-code.md
git commit -m "docs(p5): rewrite quickstart-claude-code for plugin install"
```

---

## Task 6: Rewrite quickstart-cursor.md to the plugin model

**Files:**
- Modify: `docs/guides/quickstart-cursor.md`

Same shape as Task 5 but Cursor-flavored, and Cursor's submodule story was the heaviest (the `.cursor/` real-copy + re-run-`setup.sh` rationale at lines ~21–303). Under the plugin model Cursor reads the shared tree directly, so the entire copy/re-copy rationale is obsolete.

- [ ] **Step 1: Replace the install block** (lines ~21–40) with S1 (Cursor) + the no-symlink note from Task 5 Step 1.

- [ ] **Step 2: Replace the update block(s)** (lines ~69–74 and ~299–303) with S2 (Cursor).

- [ ] **Step 3: Delete the "Cursor copies, not symlinks" rationale** (lines ~74, ~225–235, ~266–275) — no longer true; the plugin delivers files natively. Replace with: "Cursor loads the plugin's skills and `.mdc` rules directly from the installed plugin; there is nothing to copy or re-sync."

- [ ] **Step 4: Remove the worktree/submodule section** (lines ~239–303) — same replacement as Task 5 Step 3.

- [ ] **Step 5: Fix the contribute note** (line ~205) → "open a PR against `rkawaishi/workato-toolkit`."

- [ ] **Step 6: Resolve the `:242` meta-mention** (the worktree-submodule paragraph) — removed by Step 4; confirm it is gone.

- [ ] **Step 7: Verify + commit**

Run: `grep -nE "submodule|setup\.sh|sync_agents\.py|framework/|@local" docs/guides/quickstart-cursor.md || echo clean`
Expected: `clean`.
```bash
git add docs/guides/quickstart-cursor.md
git commit -m "docs(p5): rewrite quickstart-cursor for plugin install (drop copy/re-sync model)"
```

---

## Task 7: Rewrite architecture.md to the plugin model

**Files:**
- Modify: `docs/guides/architecture.md`

Currently describes the submodule + per-editor symlink/copy distribution (the table at lines ~19–27, "added as a `kit/` submodule" at ~37, the `docs/ → kit/docs/` tree at ~46–48, "`kit/` is referenced read-only as a submodule" at ~74).

- [ ] **Step 1: Replace the distribution table** (lines ~19–27) with the shared-tree plugin model from design §2–§3: one shared `skills/`/`docs/`/`bin/`/`agents/`/`rules/` tree read by every editor; per-editor differences limited to manifests, hooks JSON (3 variants), Cursor `.mdc`, and context files. Cite the docs-overlay MCP for knowledge-base reads.

- [ ] **Step 2: Replace the workspace-layout tree** (lines ~37–48) — remove the `kit/` submodule + symlinks; show that the plugin is installed at the editor level and the workspace holds only `projects/`, `connectors/`, and `org/docs/`.

- [ ] **Step 3: Update the framework-vs-org table** (lines ~67–74) — "Framework (kit/)" → "Framework (bundled in the plugin, read-only, served via the docs-overlay MCP)"; drop "referenced read-only as a submodule."

- [ ] **Step 4: Verify + commit**

Run: `grep -nE "submodule|setup\.sh|sync_agents\.py|framework/|@local" docs/guides/architecture.md || echo clean`
Expected: `clean`.
```bash
git add docs/guides/architecture.md
git commit -m "docs(p5): rewrite architecture guide for shared-tree plugin model"
```

---

## Task 8: Targeted edits to lifecycle / knowledge-management / skills-reference / guides README

**Files:**
- Modify: `docs/guides/lifecycle.md` (line 111)
- Modify: `docs/guides/knowledge-management.md` (lines 15, 64)
- Modify: `docs/guides/skills-reference.md` (line 16)
- Modify: `docs/guides/README.md` (line 12)

- [ ] **Step 1: lifecycle.md:111** — `### Framework side (\`workato-dev-kit\` repo)` → `### Framework side (the \`workato-toolkit\` plugin)`.

- [ ] **Step 2: knowledge-management.md:15** — replace the sentence "Files under `.claude/rules/` … pre-generated by the kit maintainer with `python3 scripts/sync_agents.py` … `git submodule update --remote kit && bash kit/setup.sh`." with: "Always-on rules ship inside the plugin and are delivered automatically (SessionStart hook for CC/Codex, `.mdc` for Cursor, `GEMINI.md` for Gemini). Update the toolkit with your editor's plugin-update command — no sync to run."

- [ ] **Step 3: knowledge-management.md:64** — "**Users do not edit the kit canonical `docs/` directly** (that would mean changing the kit submodule)." → "**Users do not edit the plugin's bundled `docs/` directly** (it is read-only); corrections go to the workspace `org/docs/` overlay."

- [ ] **Step 4: skills-reference.md:16** — replace the `sync_agents.py` / `setup.sh` / `git submodule update --remote kit` sentence with: "Skills ship inside the plugin and load automatically; update them with your editor's plugin-update command."

- [ ] **Step 5: guides/README.md:12** — replace the `framework/claude/` + `scripts/sync_agents.py` + `bash kit/setup.sh` Note with: "> **Note:** Skills, rules, and the knowledge base ship inside the plugin. Always-on rules are delivered automatically per editor; knowledge-base docs are served on demand through the docs-overlay MCP. See [Design and architecture](architecture.md)."

- [ ] **Step 6: Verify + commit**

Run: `grep -rnE "submodule|setup\.sh|sync_agents\.py|framework/|@local" docs/guides/lifecycle.md docs/guides/knowledge-management.md docs/guides/skills-reference.md docs/guides/README.md || echo clean`
Expected: `clean`.
```bash
git add docs/guides/lifecycle.md docs/guides/knowledge-management.md docs/guides/skills-reference.md docs/guides/README.md
git commit -m "docs(p5): drop submodule/sync_agents wording from lifecycle/knowledge/skills/guides-README"
```

---

## Task 9: Refresh credential-patterns.txt header

**Files:**
- Modify: `credential-patterns.txt` (header comment, lines ~1–12)

The pattern list itself is correct and stays. Only the "Consumed by" header is stale (it names `setup.sh` and `framework/…` paths).

- [ ] **Step 1: Replace the header "Consumed by" block** with:
```
# workato-toolkit — credential and secret patterns (single source of truth).
#
# Consumed by:
#   - bin/block-credential-read.sh   (PreToolUse credential-guard hook; bundled
#                                      in the plugin for every editor)
#   - the security snippets in README.md (permissions.deny for Claude Code;
#     .codexignore / .cursorignore / .geminiignore for the other editors)
```
Keep everything from the "Bash enforcement model" paragraph onward unchanged.

- [ ] **Step 2: Verify the hook still resolves patterns**

Run: `python3 -m pytest tests/test_rules_agents_hooks_migration.py -q`
Expected: PASS (no behavior change; header-only edit).

- [ ] **Step 3: Commit**

```bash
git add credential-patterns.txt
git commit -m "docs(p5): refresh credential-patterns header (plugin hook + README snippets, not setup.sh)"
```

---

## Task 10: Full suite + final review

**Files:** none (verification only)

- [ ] **Step 1: Run the entire suite**

Run: `python3 -m pytest -q`
Expected: all green, including every `tests/test_release_p5.py` guard. If `test_derived_files_in_sync_with_source` fails, run `python3 scripts/sync_derived.py`, inspect `git diff`, commit.

- [ ] **Step 2: Confirm zero legacy tokens across docs**

Run: `grep -rnE "submodule|setup\.sh|sync_agents\.py|framework/|@local" docs/guides/ README.md || echo clean`
Expected: `clean`.

- [ ] **Step 3: Final code review**

Run `/code-review` against `main...HEAD`. Address CONFIRMED/PLAUSIBLE findings. (Per the project lesson, `/codex:review` cannot see committed diffs — use local `/code-review`.)

- [ ] **Step 4: Open the PR** (do not merge until reviewed)

```bash
git push -u origin feat/p5-release-prep
gh pr create --title "P5: release prep — release.yml, plugin-native README/guides, version bump" --body "Adds release workflow, rewrites all install docs off the submodule model to the plugin model, bumps manifests to 0.1.0, documents credential-guard security snippets. Out of scope: dev-kit deprecation notice and cutting the actual tag."
```

---

## Self-Review

**Spec coverage (design §5 + handover P5 backlog):**
- `release.yml` → Task 2. ✓
- README install, 3 editors + Gemini coming-soon → Task 4. ✓
- `permissions.deny` / `.codexignore` / `.cursorignore` / `.geminiignore` snippets → S3, Task 4. ✓
- Codex file-read protection (Bash-only guard supplement) → documented via S3 `.codexignore` + credential-patterns header (Task 9). ✓
- Old submodule install refresh → Tasks 5–8 (7 guides) + README (Task 4). ✓
- `quickstart-cursor.md:242` meta-mention → Task 6 Step 6. ✓
- CC marketplace → GitHub remote: already encoded (`marketplace add rkawaishi/workato-toolkit`, `source: "./"`); README/Task 4 make it the only documented path; the actual switch completes when the tag is cut (out of scope). ✓ (noted)
- 旧 repo deprecation 告知 → OUT of scope (separate repo) per 2026-06-13 decision. ✓ (intentionally excluded)
- Gemini manifest → OUT of scope per design §6.2.4. ✓ (intentionally deferred)

**Placeholder scan:** release.yml, README, security snippets, version values, and all test code are given verbatim. The three rewrite tasks (5–7) specify exact sections by line range + the replacement content and are gated by the S4 token guard (objective pass/fail) — no "TBD".

**Type/name consistency:** `EXPECTED_VERSION = "0.1.0"` matches Task 3's bump; `_LEGACY` token set matches S4 and every Task 5–9 verify-grep; README assertions in Task 1 match the exact strings written in Task 4 (`/plugin marketplace add rkawaishi/workato-toolkit`, `codex plugin marketplace add rkawaishi/workato-toolkit`, `.codexignore`, `Gemini`/`soon`, `permissions`/`deny`).
