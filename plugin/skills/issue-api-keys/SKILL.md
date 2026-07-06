---
description: Design, issue, rotate, revoke, and audit per-environment Workato Developer API clients/keys (dev = write, test/prod = read-only). Use at new-workspace setup or when rotating agent credentials. Japanese prompts are also supported.
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
disable-model-invocation: true
---

# /issue-api-keys

Issue per-environment **Developer API clients** so the deployment policy becomes
physical: the agent's dev key can write, the test/staging and prod keys cannot —
even if every software guard fails. Also handles rotation, revocation, and audits.

## Usage

- `/issue-api-keys` — plan mode: interview, present the permission design, issue nothing
- `/issue-api-keys issue` — run the full issuance flow (plan → roles → issue → verify → record)
- `/issue-api-keys rotate <env>` — rotate one environment's key (e.g. `rotate dev`)
- `/issue-api-keys revoke <env>` — revoke one environment's client
- `/issue-api-keys audit` — compare remote clients against the org record

## System guard (read first)

This skill manages **Developer API clients only** (`/api/developer_api_clients` — the
credentials the CLI / API helper / CI authenticate with). Check
`workato_docs_lookup("platform/workato-api-systems.md")` for the decision flow. If the
user actually needs keys for *callers of APIs they publish on Workato* (API Platform),
point them to the Platform CLI's `workato api-clients` command group and stop — the two
systems must not be conflated.

## Procedure

### 0. Read the design guide and the org record

- `workato_docs_lookup("platform/developer-api-clients.md")` — returns the kit design
  guide (three-client scheme, permission matrix, role checklists, record template)
  merged with the org's issuance record overlay when one exists (org content wins).
  A previous issuance record changes the flow: rotation/audit instead of first issue,
  and recorded role IDs are reused.

### 1. Plan

Interview the user and present the resolved design before touching anything:

1. **Org prefix** (e.g. `acme`) — client names become `<org>-agent-<env>`, profiles `<org>-<env>`.
2. **Environment display names** — Workato's enum is `DEV`/`TEST`/`PROD`; record the
   org's own naming (e.g. Staging = `TEST`).
3. **Promotion policy** — A (default): dev key may create Deploy manifests to test via
   `/deploy-project`; B: no deployment privilege on agent keys, all promotion in the UI.
   Prod deployments are never created or approved by agents under either policy.
4. **Folder scope** — default `all_folders`; narrow to `--folder-ids` on request.
5. **IP allow-list** — optional.

Print the permission matrix from the design guide with the chosen options applied, plus
the client/profile naming table. In plan mode, stop here. In `issue` mode, get explicit
confirmation before proceeding.

### 2. Roles (one-time, in the UI)

Print the two role checklists from the design guide (*Agent Dev*, *Agent ReadOnly*) and
ask the user to create them under **Workspace admin > API clients > Roles**. This is a
legitimate UI request — custom role creation has no documented API. Then fetch the IDs:

```bash
python3 scripts/workato-api.py api-clients roles --profile <org>-admin
```

If the endpoint is unavailable (404), ask the user to read the role IDs from the UI
(the role's URL or detail screen) instead.

### 3. Bootstrap admin key

Client issuance needs one admin-privileged Developer API client (chicken-and-egg):

- If an admin profile already exists (`workato profiles list`), use it.
- Otherwise guide the user through creating one client in **Workspace admin > API
  clients** (UI) and registering it: `workato init --profile <org>-admin ...`.
- Verify with `python3 scripts/workato-api.py profile show --profile <org>-admin`.
- Offer to revoke or shelve the admin client after issuance — agents never keep it.

### 4. Issue (one client per environment)

Dry-run first, then create. `--register-profile` stores the token directly in the OS
keyring (service `workato-platform-cli`) and adds the CLI profile entry:

```bash
python3 scripts/workato-api.py api-clients create --profile <org>-admin \
  --name <org>-agent-dev  --environment DEV  --role-id <agent-dev-role-id> \
  --register-profile <org>-dev --dry-run   # then repeat without --dry-run

python3 scripts/workato-api.py api-clients create --profile <org>-admin \
  --name <org>-agent-test --environment TEST --role-id <agent-readonly-role-id> \
  --register-profile <org>-test

python3 scripts/workato-api.py api-clients create --profile <org>-admin \
  --name <org>-agent-prod --environment PROD --role-id <agent-readonly-role-id> \
  --register-profile <org>-prod
```

**Token safety (non-negotiable): Never print or echo the token.** Never pass it on a
command line, never write it to a file outside the helper's keyring / chmod-600 fallback
path, never commit it anywhere. If a token is ever displayed by accident, rotate it
immediately. The API shows a token exactly once, at creation — there is nothing to "look
up" later, which is by design.

### 5. Verify

- Read smoke on all three profiles:
  `python3 scripts/workato-api.py profile show --profile <org>-<env>` (each env).
- Guard smoke: confirm the deployment-flow rule refuses a push on `<org>-test` /
  `<org>-prod` (the `workato-deployment-flow` rule, always-on) — the read-only role makes
  this physical, the profile-name check keeps it legible.
- Optional dev write smoke: `workato push` of a scratch change, or skip if the user prefers.

### 6. Record

Write `org/docs/platform/developer-api-clients.md` using the template from the design
guide: client names/IDs, role names/IDs, environments, policy A/B, scope, issue dates,
rotation cadence. **No tokens in the record.** Commit it in the workspace repository:

```bash
git add org/docs/platform/developer-api-clients.md
git commit -m "docs(org): record Developer API client issuance"
```

## rotate / revoke / audit

- **rotate `<env>`** — old token dies immediately; new one lands in the keyring in the
  same run. Update the record's issue/rotate-by dates afterward:

```bash
python3 scripts/workato-api.py api-clients rotate --profile <org>-admin \
  --name <org>-agent-<env> --register-profile <org>-<env> --yes
```

- **revoke `<env>`** — delete the client, then mark it revoked in the record:

```bash
python3 scripts/workato-api.py api-clients delete --profile <org>-admin \
  --client-id <id> --yes
```

- **audit** — list remote clients and diff against the record; report strays (remote
  clients not in the record) and ghosts (recorded clients missing remotely):

```bash
python3 scripts/workato-api.py api-clients list --profile <org>-admin
```

## Rules to follow

- The bootstrap admin key belongs to the workspace admin, not to agents; `api-clients`
  mutations demand an explicit `--profile` for exactly this reason — never work around it.
- Agent keys never manage API clients (the matrix denies it); issuance always goes
  through the admin profile with the user present.
- Separate-workspace organizations (legacy model, no `environment` attribute): follow the
  fallback section of the design guide — one client per workspace, same roles, same
  profile names.
