---
description: Read-only inspection of a test or prod environment — recipe run state, job health, error triage, definition diff against dev, and environment-config verification. Never writes; fixes travel dev → deploy. Japanese prompts are also supported.
allowed-tools: Bash, Read, Glob, Grep
disable-model-invocation: true
---

# /inspect-env

**Read-only.** This skill never mutates anything — it does not push, does not
release connectors, does not start or stop recipes, does not run deployments, and
does not write properties or table rows. It inspects a promoted environment through
the org's **read-only** test/prod API keys (`/issue-api-keys` matrix) and turns what
it sees into a classified diagnosis and a next action. Deploy success is where this
skill starts, not where verification ends.

## Usage

- `/inspect-env test` — post-promotion verification of test (S8-1)
- `/inspect-env prod` — production health check / incident triage (S8-1, S8-2)
- `/inspect-env prod --recipe-id <id>` — focus on one recipe

## 0. Resolve the target (read-only)

```bash
python3 scripts/workato-api.py --profile <org>-<env> profile show
```

Every helper call below carries `--profile <org>-<env>` — **it is a global flag and
must come before the subcommand** (placed after it, argparse rejects the call). If a
call is refused by the
read-only key, record which read was refused (that feeds the issuance-record review)
and fall back to asking the user to check that item in the UI. Consult
`workato_docs_lookup("platform/environments.md")` for the environment model when the
org's tier naming is unclear.

## 1. Recipe run state (S8-1)

```bash
python3 scripts/workato-api.py --profile <org>-<env> recipes list --folder-id <folder_id>
```

The target-env folder ID is not the dev `.workatoenv` value — take it from the
deployment record (`--profile <org>-<env> deploy status <id>` / `deploy list`) or
ask the user once and note it. Report three states distinctly — **deploy success
does not mean the business is running**:

1. **Running with jobs flowing** — healthy; go to step 2 for the success rate.
2. **Stopped** — deploy carries code, not run state. Starting a recipe in test/prod
   is a human UI action; list the recipes and where to click.
3. **Running but no first job yet** — the trigger hasn't fired. Explain what would
   fire it using the trigger-type injection matrix (per trigger type: webhook POST,
   table record, form submission, polling wait — the inline list in `/diagnose-jobs`
   §3 is the authoritative one until `/push-project --test` carries the full matrix).
   Injection in test/prod is a human action; in **prod**, synthetic test data means
   creating real records in production business systems — do not propose it unless
   the user **explicitly agrees**; prefer waiting for real business traffic.

## 2. Job health summary

```bash
python3 scripts/workato-api.py --profile <org>-<env> jobs list --recipe-id <id> --limit 20
python3 scripts/workato-api.py --profile <org>-<env> jobs get --recipe-id <id> --job-id <job-id>
```

Per recipe: last N job outcomes, failure rate, and — for failures — the error body.
Establish the **range**: since when, how many, which recipes. Bundle same-cause
failures into one finding. **If everything is failing at once, suspect unfinished
promotion-checklist items (auth, properties, seeds — step 5) before any per-recipe
diagnosis** — a wholesale failure is almost never N independent recipe defects.

## 3. Definition diff against dev (S8-2)

```bash
python3 scripts/workato-api.py --profile <org>-<env> sdk diff-project --project-dir projects/<name>
```

This copies the project to a **temp directory**, pulls into the copy under the
target profile, and diffs — read-only, the dev workspace is never modified (never
run a bare in-workspace pull for this).

**Known gap (verify on a real workspace — spec §6 OQ):** the temp copy carries the
dev `.workatoenv`, so the pull may resolve dev's folder ID instead of the target
environment's. If the diff output looks like "no differences" against a clearly
divergent env, or the pull errors on the folder: re-point the scratch copy first
(`workato projects use "<name>"` **inside the temp copy**, under the target
profile), or fall back to comparing the specific recipe definitions from the UI.
Report which mechanism was actually used — do not present a dev-vs-dev diff as a
dev-vs-prod one.

## 4. Classify (S8-2)

| Class | Signal | Next action |
|---|---|---|
| Definition diff / recipe defect | diff shows dev ≠ env, or the error points into the recipe | hotfix path: fix in dev (`/diagnose-jobs`) → `/deploy-project` — never patch the env directly |
| Environment difference | auth 401/403, missing properties, unseeded Lookup/Data Table, custom-connector release version, on-prem group, stopped recipes | hand the human the specific missing item (step 5) |
| External spec change | provider changed its response shape (definitions identical, errors say otherwise) | hotfix path, same as definition defects |
| Transient external failure | rate limit, provider outage | wait/monitor; hand over the analysis |

If the environment supports it, cross-check the **activity log** for recent manual
changes ("did someone touch this in the UI?") — availability with a read-only key is
still being verified on a real workspace; skip gracefully when absent.

For incident containment (stopping a runaway prod recipe), do not attempt it —
follow `/run-recipes`' prod-boundary guidance: recipe IDs, direct URLs, human stops
it in the UI.

## 5. Environment-config verification (S8-5 / S8-6)

The promotion checklist's two data items, verified rather than assumed:

- **Environment properties**: compare the names the recipes reference against the
  target env (`workato properties list` under the target profile — if the read-only
  key refuses it, ask the human to confirm the seeding list instead).
- **Lookup / Data Table seeding**: deploy moves schema, not rows. Check the tables
  the recipes depend on for presence/row counts where a read is possible; otherwise
  ask the human to confirm against the seeding list from `/deploy-project`.
  (`/deploy-project` today prints one-line checklist items; the named
  properties/seed **lists** are its planned upgrade — until that lands, build the
  list here from what the recipes reference.)

An unset property or an empty master table is an **environment difference** (class 2)
and routes back to the promotion checklist, not to a recipe fix.

## 6. Recovery follow-up (S7-3, prod side)

After a fix has been promoted and the environment is green again:

1. List the jobs that **failed during the incident window** (from step 2) — they are
   unprocessed business data and do not vanish when the recipe is fixed.
2. Rerunning is a **human** action in test/prod: print the job list and the UI rerun
   steps. Warn when the recipe is not idempotent (a rerun could double-process).
3. Only after this list is delivered does the investigation count as closed.

## Report

- Environment, range inspected, and per-recipe state (running / stopped / no first job).
- Findings bundled by root cause with their class and evidence (error bodies, diff).
- The recommended next action per finding (human UI step, hotfix path, or wait).
- Any reads the key refused (for the `/issue-api-keys` record) and any item that
  needs human UI confirmation.
- After recovery: the reclaim list (S7-3).

## Notes

- Pair with: `/deploy-project` (the only write path to test/prod),
  `/diagnose-jobs` (the dev fix loop), `/run-recipes` (dev run control + the
  prod-boundary guidance).
- This skill's value is honesty: report what is verified, what was refused, and
  what a human still has to confirm — never mark an environment healthy by
  assumption.
