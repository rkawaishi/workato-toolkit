---
description: One-time bootstrap of a Workato workspace repository — CLI check, materialize the bundled API helper and templates, directory skeleton, credential deny-lists, profile setup and verification. Run --update to refresh the materialized scripts after a plugin update. Japanese prompts are also supported.
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
disable-model-invocation: true
---

# /setup-workspace

Bootstrap a repository so AI agents can develop on Workato immediately. This covers the
**infrastructure**: the CLI, the bundled helper scripts, directory skeleton, credential
deny-lists, and profile verification. It is *not* the knowledge bootstrap
(`/onboard` learns from existing assets) and *not* key issuance (`/issue-api-keys`
designs per-environment API clients) — it ends by pointing at both.

## Usage

- `/setup-workspace` — full bootstrap (idempotent; safe to re-run)
- `/setup-workspace --update` — refresh only the materialized scripts/templates after a plugin update

## Procedure

### 1. Repo and CLI checks

- `git rev-parse --show-toplevel` — if not a git repository, offer `git init` first
  (the org knowledge overlay and the materialized scripts are meant to be committed).
- `workato --version` — if the Platform CLI is missing, guide:
  `pipx install workato-platform-cli` (then re-check).

### 2. Locate the bundled assets

Call the docs-overlay MCP tool **`workato_asset_path`** for each of:

- `workato-api.py`
- `ensure-workatoignore.sh`
- `workatoignore.template`

Each call returns the absolute path of the file bundled inside the plugin.
Fallback when the MCP is unavailable: fetch the same three files from
`https://raw.githubusercontent.com/rkawaishi/workato-toolkit/<release-tag>/plugin/scripts/workato-api.py`
(and siblings under `plugin/scripts/` / `plugin/templates/`) — pin a release tag, never `main`.

### 3. Materialize into the workspace (idempotent)

```bash
mkdir -p scripts templates
cp "<asset-path:workato-api.py>" scripts/workato-api.py
cp "<asset-path:ensure-workatoignore.sh>" scripts/ensure-workatoignore.sh
chmod +x scripts/ensure-workatoignore.sh
cp "<asset-path:workatoignore.template>" templates/workatoignore.template
```

When a target already exists, compare first (`cmp -s <src> <dst>`):

- identical → report "up to date", skip;
- different → show `python3 scripts/workato-api.py --version` (workspace copy) vs the
  bundled version and ask before overwriting — the workspace copy may carry org-local
  patches. With `--update`, this comparison-and-refresh is the whole run.

The workspace copies are git-managed, so the helper version is pinned with the repo.

### 4. Directory skeleton

```bash
mkdir -p org/docs/connectors org/docs/logic org/docs/platform org/docs/patterns \
         projects connectors
```

(`org/docs/` is the organization knowledge overlay — see the `org-knowledge-overlay`
rule, always-on.)

### 5. Credential deny-lists (write only when absent)

Place the defense-in-depth files from the toolkit README's "Security hardening" section:

- `.claude/settings.json` — `permissions.deny` entries for `master.key`,
  `settings.yaml`, `settings.yaml.enc`, `.resource-providers.yml`, `.env`, `.env.*`,
  `*.key`, `*.pem`, `*.secret`, `*.credential*` (merge into an existing file, never
  clobber other settings).
- `.cursorignore` and `.codexignore` — the same patterns, one per line.

`.workatoenv` is intentionally NOT excluded — it holds only IDs, no secrets.

### 6. Profiles

`workato profiles list` — if no profile exists, walk the user through `workato init`
for the **dev** workspace first, naming it `<org>-dev` per
`workato_docs_lookup("platform/cli-profiles.md")`. Do not create test/prod profiles here;
`/issue-api-keys` provisions those with correctly scoped keys.

### 7. Verify

```bash
python3 scripts/workato-api.py profile show
workato projects list --source remote --output-mode json
```

Both must succeed against the dev profile. Report the resolved workspace.

### 8. Next steps and commit

Print the follow-ups in order:

1. `/issue-api-keys` — per-environment Developer API clients (dev write, test/prod read-only)
2. `/pull-project --all` — bring remote projects local
3. `/onboard` — bootstrap the org knowledge base from the pulled assets

```bash
git add scripts/ templates/ org/ .claude/settings.json .cursorignore .codexignore
git commit -m "chore: bootstrap Workato workspace (toolkit setup-workspace)"
```

## Rules to follow

- Idempotent: re-running must never destroy org-local changes — every overwrite of a
  differing file goes through the version comparison and an explicit user choice.
- This skill writes only workspace files; it never touches the plugin's bundled tree.
- If `scripts/ensure-workatoignore.sh` or the helper goes missing later (fresh clone),
  any skill that needs it should send the user here: `/setup-workspace --update`.
