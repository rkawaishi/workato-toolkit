---
description: Promote a project between Workato environments with the Deploy feature (dev→test→prod). Wraps the API helper's guarded deploy commands; prod runs require explicit human confirmation and approvals stay in the UI. Japanese prompts are also supported.
allowed-tools: Bash, Read, Glob, Grep
disable-model-invocation: true
---

# /deploy-project

The sanctioned promotion path. Pushing (`/push-project`) targets dev only — that rule is
unchanged and inviolable. Promotion to test/staging and prod happens through Workato's
**Deploy feature** (Recipe Lifecycle Management API): an auditable manifest from one
environment to the next, never a direct write.

## Usage

- `/deploy-project` — preview what a dev→test deploy would contain (read-only)
- `/deploy-project preview --to <test|prod>` — preview a specific transition
- `/deploy-project run --to <test|prod>` — execute the deploy (guards below)
- `/deploy-project status <id> [--wait]` — check / follow one deployment
- `/deploy-project list` — deployment history (audit)
- `/deploy-project rollback` — restore a prior release to the target (checklist below)

## Guards (mandatory, in this order)

1. The source environment is inferred from the resolved profile's `<org>-<env>` suffix.
   Only **(dev → test)** and **(test → prod)** transitions exist. Skip-tier (dev → prod),
   backward, and same-env transitions are refused by the helper *before any API call* —
   never work around the refusal.
2. `run --to prod` additionally requires the helper's `--yes` flag **and** an explicit
   confirmation from the user in this conversation, restating what will be deployed.
3. Check the promotion policy via `workato_docs_lookup("platform/developer-api-clients.md")`
   (the org's issuance record overlays the kit guide): under promotion **Policy B** agent
   keys hold no deployment privilege — refuse `run`, print the UI steps
   (project → Deploy → target environment), and stop.
4. **Never approve a deployment** on the user's behalf, never call an approve endpoint,
   and never treat approval UI steps as automatable. Prod approval belongs to the release
   manager in the Workato UI.

## Procedure

### 0. Read the environment model

- `workato_docs_lookup("platform/environments.md")` — tiers, Deploy feature, per-env differences
- `workato_docs_lookup("patterns/deployment-guide.md")` — per-asset deployment behavior

### 1. Preview (read-only)

```bash
python3 scripts/workato-api.py deploy preview --to test   # folder_id from .workatoenv
```

Show the user what the manifest would contain (recipes and assets in the resolved
folder). For a test → prod preview, pass `--profile <org>-test` **before the
subcommand** (`workato-api.py --profile <org>-test deploy preview --to prod` —
`--profile` is a global flag; placed after the subcommand it is rejected).

### 2. Pre-promotion checklist (print every time — as named lists, not yes/no)

The manifest carries code, not runtime state. Do not print bare "is it seeded?"
items — **generate the actual list** the human must act on, per
`platform/environments.md`:

- [ ] Target-env **connection credentials** are entered (same connection names, different secrets)
- [ ] **Environment properties** (S8-5): build the list from what the recipes
      reference vs the target env —

      ```bash
      workato properties list --profile <org>-dev   # native CLI (flag after the subcommand); the helper has no properties subcommand
      ```

      Present name / dev value / a blank for the target value. The agent cannot
      upsert test/prod properties (read-only keys); the human enters them in
      Tools > Environment properties. Changed values need a recipe restart.
- [ ] **Lookup Table / Data Table rows** (S8-6): schema deploys, records do not.
      For each table the recipes depend on, classify the seed requirement —
      **master** (carry all rows), **accumulating** (start empty), or
      **environment-dependent** (values differ per env) — and produce the named
      seed list (table / rows to carry). The human seeds test/prod; do not truncate
      or bulk-copy accumulating tables.
- [ ] **Custom connectors** are released in the target env (version matches)
- [ ] List of **recipes to (re)start** after the deploy is agreed

### 3. Run and wait

```bash
# dev → test (dev profile; description goes to the audit log)
python3 scripts/workato-api.py deploy run --to test --wait --description "<release note>"

# test → prod (test profile + human sign-off; approval stays in the UI)
# NOTE: --profile is a GLOBAL flag — it must come before the subcommand.
python3 scripts/workato-api.py --profile <org>-test deploy run --to prod --yes --wait \
    --description "<release note>"
```

`--wait` polls until the deployment reaches a terminal state. If the target requires
approval, the run parks as pending — tell the user whom to ask and stop; do not poll
forever and do not attempt to influence the approval.

### 4. Verify and report

```bash
python3 scripts/workato-api.py deploy status <deployment-id>
python3 scripts/workato-api.py deploy list --environment-type test --limit 5
```

- On success: report manifest id, state, and the still-open checklist items (connection
  auth, recipe starts) as the user's follow-ups in the target environment.
- On failure: surface the deployment state and check the common causes — unreleased
  custom connector, missing connection in the target, asset referenced but not included.
- For extra assurance, offer a read-only pull of the target environment into a scratch
  directory and a diff against the local project (pull is allowed against any profile;
  see the `workato-deployment-flow` rule, always-on).

## Rollback (S8-3)

When a promoted version turns out to be the problem, roll back — never by patching
the target env directly.

- **git is the release ledger.** The sanctioned rollback is: restore the previous
  release state into **dev** from git, then re-promote it through the normal guarded
  path (dev → test → prod, same checklist, same approvals). There is no direct-to-env
  shortcut, and prod approval stays human even for a rollback.
- If the platform's Deploy API exposes re-applying a past deployment, it may serve as
  a faster path to **test** — verify availability on a real workspace first (spec Open
  Question). It does not change the prod-approval rule.
- `packages` export/import, if used, is a **write** — only ever to restore **dev**;
  test/prod still go through Deploy. Never import straight into test/prod.
- **Recovery when git has no prior release** (a commit was missed): pull the target
  env's current definitions into a scratch dir (read-only), reconstruct the last-good
  state from there, and confirm with the user before promoting — this is the last
  resort, and the fix for next time is to commit on every push.

## Hotfix note (S8-4)

A production defect is fixed in **dev** (`/diagnose-jobs`) and re-promoted through
this same path — never edited in place in test/prod. **Emergencies run the exact
same checklist**; urgency is when the connection-auth / properties / seed / connector-
release steps are most likely to be skipped, so the checklist matters most then.
Close the loop with `/inspect-env` (recovery confirmed) and the unreclaimed-job
reclaim list.

## Report format

```
Deploy <project>: <source> → <target>
Manifest: <id>  State: <success|failed|pending approval>
Assets: <n> recipes, <n> connections, <n> tables
Follow-ups in <target>:
- authenticate connections: <list>
- start recipes: <list>
- seed properties/tables: <list or none>
```
