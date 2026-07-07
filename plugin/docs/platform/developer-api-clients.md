# Developer API clients — per-environment agent keys

> Which system? This page is about **Developer API clients**
> (`/api/developer_api_clients/*`) — the credentials that the Platform CLI, the API
> helper, MCP servers, and CI use to operate Workato itself. It is **not** about the
> `workato api-clients` CLI command, which manages **API Platform** clients (caller-side
> auth for APIs you publish). When unsure, walk the decision flow in
> `platform/workato-api-systems.md` (via `workato_docs_lookup`) first.

## Why per-environment keys

The toolkit's deployment policy is *push to dev only; promote to test/prod through the
Deploy feature* (see `platform/environments.md` via `workato_docs_lookup`). Profile naming
(`<org>-dev` / `<org>-test` / `<org>-prod`) lets agents refuse unsafe pushes, but a
convention is only a convention. Scoping each environment's API client to the privileges
that environment actually needs makes the policy **physical**: an agent holding the test
or prod key *cannot* write, even if every software guard fails.

## The three-client scheme

| Client name | `environment` | Role (privilege group) | Registered as CLI profile |
|---|---|---|---|
| `<org>-agent-dev` | `DEV` | Agent Dev (write) | `<org>-dev` |
| `<org>-agent-test` | `TEST` | Agent ReadOnly | `<org>-test` |
| `<org>-agent-prod` | `PROD` | Agent ReadOnly | `<org>-prod` |

Client creation payload (`POST /api/developer_api_clients`):
`name`, `api_privilege_group_id` (the role), `environment` (`DEV`|`TEST`|`PROD`),
`all_folders` **or** `folder_ids[]`, optional `ip_allow_list[]`. The token is returned
**only once**, in the create response (`token.value`) — it cannot be fetched again.

Folder scope default: `all_folders: true` (agents create new projects). Narrow with
`folder_ids` when the organization wants the agent confined to specific projects.

## Permission matrix

| Capability | `<org>-agent-dev` (DEV) | `<org>-agent-test` (TEST) | `<org>-agent-prod` (PROD) |
|---|---|---|---|
| Projects / folders read (pull, export) | ✅ | ✅ | ✅ |
| Projects write (push / import) | ✅ | ❌ | ❌ |
| Recipes start / stop | ✅ | ❌ | ❌ |
| Connections create / update | ✅ | ❌ | ❌ |
| Data Tables create / change | ✅ | ❌ | ❌ |
| Lookup Tables create / change | ✅ | ❌ | ❌ |
| Environment properties upsert | ✅ | ❌ | ❌ |
| Custom connector SDK push / release | ✅ | ❌ | ❌ |
| Jobs read (monitoring, diagnosis) | ✅ | ✅ | ✅ |
| Tables read (Data / Lookup rows, for `/inspect-env`) | ✅ | ✅ | ✅ |
| Connections read (auth state, for diagnosis) | ✅ | ✅ | ✅ |
| Environment properties read (seed verification) | ✅ | ✅ | ✅ |
| Activity log read (who changed what) | ✅ | ✅ | ✅ |
| Deployments read (status / history) | ✅ | ✅ | ✅ |
| Deployments create (promote to next env) | Policy choice | Policy choice | ❌ always |
| Developer API clients manage | ❌ | ❌ | ❌ (bootstrap admin key only) |

**Promotion policy** (the organization picks one and records it):

- **Policy A (default, recommended)** — the dev key holds *Deployments create*, so agents
  can run `/deploy-project run --to test`. This is still the Deploy feature: an auditable
  manifest, not a direct write. test → prod stays human (UI), and prod approval is always
  human under every policy.
- **Policy B (conservative)** — no agent key holds *Deployments create*; every promotion
  happens in the UI. Agents may still read deployment status/history.

## Role definitions (created once, in the UI)

Roles ("API client roles" / privilege groups) are managed in
**Workspace admin > API clients > Roles**. Custom role creation is not exposed through a
documented API, so create these two roles in the UI. Privilege labels vary slightly by
Workato release — match the categories, not the exact strings.

**Agent Dev** (assign to the DEV client):
- Projects / folders: read + write (import/export)
- Recipes: read, write, start, stop
- Connections: read, write
- Data Tables: read, write
- **Lookup Tables: read, write** (a distinct privilege scope from Data Tables —
  omitting it and granting a broad "tables" write anyway is the gap the ReadOnly
  role below must avoid)
- Environment properties: read, write
- Connector SDK: read, write, release
- Jobs: read
- Deployments: read (+ create under Policy A)

**Agent ReadOnly** (assign to the TEST and PROD clients):
- Projects / folders: read (export)
- Recipes: read
- Jobs: read
- Data Tables **read**, Lookup Tables **read** (rows, for `/inspect-env` seed
  verification — read only, never write)
- Connections **read** (auth state), Environment properties **read** (seed
  verification), Activity log **read**
- Deployments: read
- Nothing else. In particular: **no table writes** (Data or Lookup), no
  import/write, no recipe lifecycle, no connection writes, no property writes,
  no SDK. If the platform bundles table read and write into one privilege,
  prefer denying it and confirming seeds in the UI over granting write.

## Issuing (API helper)

Use `/issue-api-keys` — it drives these commands and records the result. Under the hood:

```bash
# Discover role IDs (falls back to reading them in the UI if the endpoint 404s)
python3 scripts/workato-api.py --profile <org>-admin api-clients roles

# Dry-run, then issue one client per environment
python3 scripts/workato-api.py --profile <org>-admin api-clients create \
    --name <org>-agent-dev --environment DEV --role-id <agent-dev-role-id> \
    --register-profile <org>-dev --dry-run
python3 scripts/workato-api.py --profile <org>-admin api-clients create \
    --name <org>-agent-dev --environment DEV --role-id <agent-dev-role-id> \
    --register-profile <org>-dev
```

Token handling: the API shows the token exactly once. `--register-profile` stores it
straight into the OS keyring (service `workato-platform-cli`) and adds the profile to
`~/.workato/profiles` — it is never printed, never placed on a command line, and never
written to the repository. Without keyring the helper falls back to a chmod-600 file
under `~/.workato/pending-tokens/` and prints only the path.

## Bootstrap (the chicken-and-egg key)

Creating API clients itself requires an admin-privileged Developer API client. Once per
workspace:

1. A workspace admin creates one client manually in **Workspace admin > API clients**
   (UI) with a role that includes member/API-client administration, or reuses an existing
   admin profile.
2. Register it as `<org>-admin` (`workato init --profile <org>-admin ...`).
3. After issuing the three agent clients, either keep `<org>-admin` off agent machines or
   revoke the client until the next rotation.

Agents never hold or use the admin key in day-to-day work; `api-clients` mutations demand
an explicit `--profile` for exactly this reason.

## Rotation, revocation, audit

- **Rotate** (periodic or on suspicion of exposure):
  `python3 scripts/workato-api.py --profile <org>-admin api-clients rotate
  --name <org>-agent-dev --register-profile <org>-dev --yes` — delete + same-name
  re-create; the old token dies immediately and the new one lands in the keyring in the
  same run.
- **Revoke**: `api-clients delete --profile <org>-admin --client-id <id> --yes`.
- **Audit**: `api-clients list --profile <org>-admin` and compare against the org record
  (below); flag clients that exist remotely but not in the record, and vice versa.

## Org record

`/issue-api-keys` writes the design record to the workspace overlay at
`org/docs/platform/developer-api-clients.md`. Template:

```markdown
# Developer API clients — org record

Environment display names: dev=Dev, TEST=Staging, PROD=Prod
Promotion policy: A (dev→test by agent via Deploy; test→prod human)
Folder scope: all_folders
IP allow-list: (none)

| Client | ID | Environment | Role (id) | Profile | Issued | Rotate by |
|---|---|---|---|---|---|---|
| acme-agent-dev | 77 | DEV | Agent Dev (547) | acme-dev | 2026-07-06 | 2027-01-06 |
| acme-agent-test | 78 | TEST | Agent ReadOnly (548) | acme-test | 2026-07-06 | 2027-01-06 |
| acme-agent-prod | 79 | PROD | Agent ReadOnly (548) | acme-prod | 2026-07-06 | 2027-01-06 |

Bootstrap admin client: acme-admin (id 12, held by <name>, not on agent machines)
```

**Never put tokens in this file** — it holds names, IDs, and policy only.

## Separate-workspace fallback (legacy model)

Organizations on the older model — one *workspace* per environment instead of integrated
environments — will find the API rejects the `environment` attribute. In that case issue
one client **per workspace** with the same two roles, each workspace needing its own
bootstrap admin key, and register them under the same `<org>-<env>` profile names. The
permission matrix is unchanged.

## Per-developer keys (related pattern)

This page covers **workspace-level agent keys**. Issuing *personal* keys to developers so
that "UI access = CLI access" is the complementary pattern: a Slack-triggered broker
recipe that looks up the requester's project grants and issues a client scoped to exactly
those folders (see the key-broker recipe pattern; actions map 1:1 to the endpoints above).
Use that for humans; use this page's scheme for agents and CI.

## Related

- `platform/workato-api-systems.md` (via `workato_docs_lookup`) — the four "API client" systems disambiguated
- `platform/environments.md` (via `workato_docs_lookup`) — environment tiers and the Deploy feature
- `platform/cli-profiles.md` (via `workato_docs_lookup`) — profile naming and the push/pull matrix
- `@.claude/rules/workato-deployment-flow.md` — the inviolable dev-only push rule
