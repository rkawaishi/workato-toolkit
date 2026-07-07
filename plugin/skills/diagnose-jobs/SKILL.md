---
description: Detect failed or non-starting recipes in dev, classify the cause, and by default fix → re-push → re-verify in a loop until green. Hands what it cannot fix to the user with the diagnosis attached. Japanese prompts are also supported.
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
disable-model-invocation: true
---

# /diagnose-jobs

The dev-side diagnosis-and-fix loop (spec S7-1〜S7-4, S6-4, S5-2). Two entrances —
failed jobs and start errors — one discipline: classify, fix what the agent can fix,
hand over what it cannot, and never call "green" a finish line while business data
sits unprocessed.

## Usage

- `/diagnose-jobs` — diagnose the current project (both entrances), fix loop by default
- `/diagnose-jobs --recipe-id <id>` — one recipe only
- `/diagnose-jobs --no-fix` — diagnose and propose only (no edits, no push)
- `/diagnose-jobs tail` — follow new failures for a bounded window

## 0. Environment guard (mandatory)

```bash
python3 scripts/workato-api.py profile show
```

**The fix cycle is dev-only.** If the resolved profile does not end with `-dev`:
diagnosis (read-only job inspection) may continue, but do **not** edit, push, or
restart anything. Fixes for test/prod always travel dev → `/deploy-project`; for
read-only investigation of test/prod use `/inspect-env`.

## 1. Collect — two entrances

### (a) Failed jobs

The helper's `jobs list` is **per recipe** (`--recipe-id` is required). For a project
or folder scope, enumerate first:

```bash
# folder_id from .workatoenv
python3 scripts/workato-api.py recipes list --folder-id <folder_id>
# then, per recipe:
python3 scripts/workato-api.py jobs list --recipe-id <id> --status failed --limit 20
python3 scripts/workato-api.py jobs get --recipe-id <id> --job-id <job-id>
```

### (b) Start errors — works even when there are no jobs at all

A recipe that fails to **start** produces no jobs, so entrance (a) stays silent.
Enter diagnosis from either signal:

- a start error just returned by `/push-project --start|--test` or `/run-recipes`
  (use the error output verbatim), or
- the run-state list shows a recipe **stopped that should be running** — treat it as
  a suspected start failure and try a start via the helper to capture the error
  (dev only — on a test/prod profile switch to `/run-recipes`' prod-boundary
  guidance instead of attempting the start).

For entrance (b) the loop exit is **start success** (then proceed to test injection
and verification); for entrance (a) it is green verification.

## 2. Classify

Read the error body (`jobs get` output or the start error) and classify. Bundle
same-cause failures: N jobs with one root cause are **one** finding, not N reports.

| Class | Example | Agent can fix? |
|---|---|---|
| Datapill reference error | non-existent `path` | ✅ fix the recipe JSON |
| Field mismatch | wrong field name / UUID | ✅ fix the recipe JSON |
| Connection unauthenticated / expired / permission | 401/403 | ❌ ask the user to authenticate in the UI |
| External spec change | provider changed its response shape | ✅ adapt the recipe (prod-origin cases go through the hotfix path) |
| Transient external failure | rate limit, provider outage | ❌ hand over the analysis, wait for recovery |
| Expectation mismatch | job succeeded but the values are wrong | ✅ fix the mapping |

When a field-level cause is unclear, consult the connector's knowledge doc via
`workato_docs_lookup("connectors/<provider>.md")` (org overlay wins) before guessing.

## 3. Fix loop (default; suppressed by `--no-fix`)

For ✅ classes, loop until green (entrance (a)) or until the start succeeds
(entrance (b)):

1. Apply the fix to the local JSON.
2. Re-push: `workato push --restart-recipes` (covers the restart; do not route
   through a separate start).
3. Re-inject a test job per trigger type: webhook → curl POST, Data/Lookup Table
   trigger → create/update a test record, Workflow App → ask for a form submission,
   polling → ask for a source record and wait out the interval. Ask the user when
   the injection is a human action, and wait for their signal. (`/push-project
   --test` will carry the full trigger-type matrix once its planned update lands —
   until then this inline list is the authoritative one.)
4. Re-verify: job outcome **and** output values (a successful job with wrong data
   is a failure — S5-2). Expected values come from the project's spec / the user's
   request (the field-mapping table). **If no expected values exist, ask the user
   for them before verifying — never self-declare green.** If `jobs get` output is
   masked or unavailable, say so and hand the user the UI steps to verify instead.

**Loop discipline** (report this trail at the end):

- Record one line per iteration: what was changed → what happened.
- Never propose the **same fix twice**. A repeated hypothesis means the loop is
  spinning — stop and reclassify.
- **Cap: 5 iterations** by default, then stop and escalate (each iteration may cost
  the user a test-data request, so the cap is not negotiable upward without asking).
- If the classification flips to a ❌ class mid-loop (e.g. it was an expired
  connection all along), stop the loop and hand over.
- **Track seeded test records across iterations**: each round that injects a table
  record adds one — keep the record IDs. On green, delete the records you created
  (own records only — never truncate) **before** prompting for commit.
- On green (and after the cleanup), prompt for `git commit` of the fixed JSON
  (push does not touch git).

## 4. Handover — what the agent cannot fix (S7-4)

When the cap is reached, or the broken part is one the generator structurally cannot
write (complex formulas, UI-only settings, subtle mappings):

1. Hand the recipe to the user for a **UI fix, with the diagnosis attached** — name
   the suspected step(s) and setting(s), so the human does not start from zero. If
   test records were seeded, list them so the human's testing does not collide.
2. **From the moment of handover until the pull completes, do not push** — the
   remote now carries the human's fix and the local copy is stale; a push would
   silently erase their work.
3. On the user's "done" signal: `/pull-project` → present the **diff** (what the
   human changed) → `git commit`.
4. Feed the diff to `/learn-recipe` / the org knowledge overlay — the places the
   generator got wrong are the highest-value org knowledge (e.g. "this connector's
   X is configured in the UI").

## 5. After green — unreclaimed jobs (S7-3)

Green is not the finish line. Jobs that **failed before the fix** landed represent
unprocessed business data:

1. List them (period, count, per recipe) from the collection in step 1.
2. Rerunning is a UI action today — print the job list and the UI rerun steps.
   Warn when the recipe is not idempotent (a rerun could double-process).
3. Only after this is reported does the run count as complete.

## 6. tail mode (bounded)

Follow new failures while the user watches — **session-bound, never a resident
monitor**. Always bound it:

```bash
python3 scripts/workato-api.py jobs tail --recipe-id <id> --status failed --max-iterations 12
```

State the window ("~60s at the default 5s interval") and re-enter diagnosis when
something appears. For standing alerting, point at Workato's own alerts.

## Report

- Trail of the loop (one line per iteration) and the final state.
- Bundled findings by root cause, each with its class and what was done.
- Handovers (who needs to do what, with the diagnosis).
- Unreclaimed failed jobs and the rerun plan (S7-3).

## Notes

- Diagnosis reads are safe anywhere; **edits, pushes, and restarts are dev-only**.
- Pair with `/run-recipes` (run state), `/push-project --test` (injection matrix),
  `/inspect-env` (test/prod read-only investigation).
