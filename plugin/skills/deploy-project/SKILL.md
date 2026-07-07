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

### 2. Pre-promotion checklist (print every time)

The manifest carries code, not runtime state. Confirm with the user, per
`platform/environments.md`:

- [ ] Target-env **connection credentials** are entered (same connection names, different secrets)
- [ ] **Environment properties** are seeded in the target env
- [ ] **Lookup Table / Data Table rows** are seeded (schema deploys; records do not)
- [ ] **Custom connectors** are released in the target env
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
