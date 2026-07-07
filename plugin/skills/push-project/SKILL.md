---
description: Push local project changes to the Workato remote. Runs validation, pushes connections first, and guides the deploy end-to-end.
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
disable-model-invocation: true
---

# /push-project

Push local changes to the Workato remote and verify the recipes work.

## Usage

- `/push-project` — push the current project
- `/push-project <project-name>` — switch to the specified project and push
- `/push-project --start` — start the recipes after pushing
- `/push-project --test` — start the recipes and verify job success after pushing
- `/push-project --restart-recipes` — auto-restart any running recipes after push (for updates)
- `/push-project --delete` — delete assets that exist remotely but not locally
- `/push-project --validate-only` — only validate (do not push)

## Procedure

### 0. Environment guard (mandatory)

**Before any validation or push, confirm the push target is dev.** See the `workato-deployment-flow` rule (always-on) for the full rule.

```bash
python3 scripts/workato-api.py profile show
```

- **Hard-block: if the resolved profile name does not end with `-dev`, abort immediately.** This covers `-test`, `-prod`, `-production`, `-staging`, `-qa`, and any other non-dev suffix. Do not offer a confirmation prompt — the rule is inviolable.
- **Inside Claude Code this is also enforced mechanically**: the plugin's `validate-before-push` PreToolUse hook refuses `workato push` / `workato recipes start|stop` (exit 2) whenever the resolved profile is not `-dev`. Treat a hook block as final — do not retry with workarounds.
- The only way to proceed is for the user to either (a) switch to a `-dev` profile, or (b) rename their dev profile to follow the `<org>-dev` convention. Tell the user which option applies.
- Direct push to test/prod is forbidden; promotion goes through the Deploy feature (call `workato_docs_lookup` with path `platform/environments.md`).

### 1. Project validation

Validate the project's JSON files before pushing. With `--validate-only`, stop here.

#### 1a. JSON syntax check

Check the syntax of every JSON file under the project directory:

```bash
# Targets: *.recipe.json, *.connection.json, *.agentic_genie.json,
#          *.agentic_skill.json, *.mcp_server.json, *.lcap_app.json,
#          *.lcap_page.json, *.workato_db_table.json
for f in projects/<project-name>/*.json; do
  python3 -c "import json; json.load(open('$f'))" 2>&1 || echo "INVALID: $f"
done
```

Fix any errors before continuing.

#### 1b. `extended_output_schema` check

Confirm `extended_output_schema` is defined on these actions / triggers:

- **add_record / update_record / search_records**: field definitions for Data Table operations.
- **return_result**: result schema for Recipe Functions (required so datapills can be picked up by downstream steps).
- **Triggers in general**: especially `new_requests_realtime` should include Data Table fields in the schema.

```
# How to check: read the recipe JSON and verify extended_output_schema is present on each block.
# If missing, warn:
WARNING: step <keyword> in <recipe>.recipe.json is missing extended_output_schema.
  Datapills may not be visible in downstream steps.
```

#### 1c. Workflow App page component check

For `*.lcap_page.json`, check the `dataSource` on dropdown components:

```
# If dataSource is null, warn:
WARNING: dropdown "<label>" in <page>.lcap_page.json has dataSource: null.
  The selected value will not persist on push. Configure it in the UI or define dataSource in the JSON.
```

#### 1d. Workato CLI `recipes validate` (blocking)

**Inside Claude Code**: the plugin's `validate-before-push.sh` PreToolUse hook (`${CLAUDE_PLUGIN_ROOT}/bin/validate-before-push.sh`) runs whenever it detects `workato push`. It runs `workato recipes validate --path <file>` on every `*.recipe.json`, catching format issues before push.

**Other editors (support on hold)**: no auto-hook. Run `/validate-recipe` explicitly before push to verify the format.

- **Run time**: roughly 2 s per file (serial). On a large project, factor in the wait.
- **On failure**: print the error details and abort the push (exit 2).
- **Workspace constraint (warning only)**: if the workspace has an unreleased custom connector, the CLI's pre-check fails first and recipe-level validation never runs. In that case the warning "CLI validate skipped for N recipe(s): ... Release with 'workato sdk push' to enable deeper validation." appears, but push still proceeds. To enable deeper validation, release the custom connector with `workato sdk push`.

### 2. Detect new connections

Before pushing, inspect the `.connection.json` files in the project and detect any new connections that don't yet exist on the Workato remote.

How to detect:
- List the local `*.connection.json` files.
- Compare with the connections already retrieved by `workato pull` (i.e. existing on Workato).
- Identify newly created connection files.

### 3. Push (two-step or single-step)

**When there are new connections — two-step push:**

1. **Push only the connection files first**: either temporarily add the other files to `.workato-ignore`, or push from a directory containing only the connection files. **Never use `--delete`** here (it would delete existing remote assets).
2. Ask the user to authenticate:

```
Pushed new connections to Workato:
- <connection_name> (<provider>)

Authenticate them in the Workato UI:
1. Open the "<project>" project
2. Enter credentials for each connection

Tell me once authentication is done. I'll push the remaining assets next.
```

3. Once authentication is done, push every asset.

**No new connections — single-step push:**

```bash
workato projects use "<project-name>"
workato push
```

**With `--restart-recipes`:**

Use this when updating existing recipes and you need running recipes to auto-restart:

```bash
workato push --restart-recipes
```

This auto-restarts any running recipes after the push.
Use it to roll out logic changes, datapill fixes, or field additions to running recipes.
Not needed when pushing only new recipes.

**With `--delete`:**

Delete assets remotely that were removed locally:

```bash
workato push --delete
```

**Known limitation: the CLI's `--delete` cannot delete `agentic_skill` and `mcp_server`** (they show up as `Skipped`).
If you need to delete one, tell the user:

```
The CLI's --delete cannot remove MCP servers or skills (they end up Skipped).
Please delete the following in the Workato UI:
- <skills/mcp_server names to delete>

Re-push once they're removed.
```

### 4. Post-push deployment guidance

After a successful push, automatically display the relevant guidance based on the assets in the project.

#### Always shown: recipe start list

```
Push complete. Start the following recipes:
- <recipe_name_1>
- <recipe_name_2>

Start them with /run-recipes start --all (or --id <id> for one),
or re-run /push-project with --start / --test.
```

#### When there are new connections

```
Verify authentication for these connections:
- <connection_name> (<provider>)

Enter credentials in Workato UI > project > Connections.
```

#### When there is an MCP server (`*.mcp_server.json`)

```
MCP server setup:
1. Open the MCP server configuration screen in the Workato UI.
2. Confirm the skill list shows under tools.
3. Review each tool's description.
4. Copy the MCP server URL and configure it in the AI client (Claude Desktop, etc.).
5. Test by calling the tool from the AI client.
```

#### When there is a Workflow App (`*.lcap_app.json`, `*.lcap_page.json`)

```
Workflow App UI verification checklist:
1. The Workflow App shows the stages and pages.
2. The submission form displays its fields correctly.
3. Dropdown options are populated.
4. The review page allows approve / reject.
5. Test: submit a request from the form and walk through the full approval flow.
```

### 5. Start recipes (`--start` / `--test`)

Recipe start/stop/restart is **`/run-recipes`**' job — it carries the dev guard, the
`--all` loop, the restart ordering, and the prod-boundary handover. Do not re-teach
raw `workato recipes start` here. After a successful push:

```
Push complete. Start the recipes with:  /run-recipes start --all
(or --id <recipe-id> for one). A start failure hands off to /diagnose-jobs.
```

### 6. Inject a test job by trigger type (`--test`)

`--test` verifies end-to-end, which means a job actually has to **run**. Pushing and
starting does not create one — inject by trigger type (S5-1). This inline matrix is
authoritative until it is factored into a shared reference:

| Trigger type | How to make one job run | Who |
|---|---|---|
| **webhook** (realtime) | `curl -X POST` the recipe's webhook URL with a sample body | agent |
| **polling** | ask for a source record that meets the trigger condition, then wait one interval | human seeds, agent waits |
| **schedule** | wait for the next run, or temporarily shorten the interval and re-push (note to revert — dev only) | agent |
| **Workflow App form** | ask the user to submit the form (give the URL) | human |
| **MCP server / Genie** | ask the user to call the tool from the AI client | human |
| **Data Table / Lookup Table trigger** | create/update a test record in the table (S5-4 below); for New/updated triggers, updating an existing row too | agent (dev; rows API permitting) |
| **API endpoint** (API Platform) | `curl` the endpoint with a client token | agent (human provides token) |
| **other** (Event Streams consume, Recipe Function invocation, …) | fire from the upstream recipe that publishes / calls it | depends (fire the caller; exact mechanism is a real-workspace open question) |

When a step needs the user (form, polling seed, tool call), give a copy-pasteable
instruction with concrete values, then wait for their signal before checking jobs.

#### Data/Lookup Table–dependent recipes (S5-4)

If the recipe reads or writes a table (via an adapter **or** a formula lookup):

1. **Seed** the test records the recipe expects (Lookup Table rows via the Developer
   API; Data Table rows where the rows API is available, else ask the user to add
   them in the UI). Dev only — never seed test/prod tables.
2. **Fire / verify** — a Data Table row trigger fires on the record you just created;
   for a writing recipe, read the row back and compare to the expected values.
3. **Clean up at the end** — delete the records you created (track their IDs across
   any fix-loop iterations; delete at green, before the git commit). Remove only your
   own records; never `Truncate` (it wipes existing data).

Then check jobs:

```bash
# Failed jobs for a recipe
python3 scripts/workato-api.py jobs list --recipe-id <recipe-id> --status failed

# Job detail (error message)
python3 scripts/workato-api.py jobs get --recipe-id <recipe-id> --job-id <job-id>
```

### 7. Fix-error cycle

If a job fails, hand the cycle to **`/diagnose-jobs`** — it carries the full cause
classification (six classes, including external spec changes vs transient external
failures), the loop discipline (5-iteration cap, no same fix twice, per-iteration
trail), and the handover/round-trip rules. Inline summary for quick cases:

1. Run `python3 scripts/workato-api.py jobs get` to read the error.
2. Diagnose:
   - **Datapill reference error**: wrong `path` → fix the recipe JSON.
   - **Connection not configured**: guide the user through connection auth in the UI.
   - **Field mapping error**: fix the field name / UUID in `input`.
   - **External API error**: distinguish a provider spec change (adapt the recipe)
     from a transient failure (hand over and wait) — `/diagnose-jobs` §2.
3. Apply the fix and re-push.
4. Restart the recipe and verify the next job.
5. Repeat until success — **bounded**: same cap and no-repeat rule as
   `/diagnose-jobs` (do not loop indefinitely).

### 8. Report

- Push result.
- Validation warnings (if any).
- Recipe start status.
- Job success / failure (under `--test`).
- For any errors, the error content and suggested fixes.

## Notes

- Push overwrites the Workato remote.
- **Always push new connections first and authenticate them**: a recipe with an un-authenticated connection fails on push.
- For Workflow App triggers (`new_requests_realtime`, etc.), test by submitting the form.
- **`--delete` limitation**: `agentic_skill` and `mcp_server` cannot be deleted via CLI. Delete them manually in the UI.
- **`--restart-recipes`**: needed to roll out changes to running recipes. Not needed when pushing only new ones.

## Git management

**`/push-project` is a deploy to the Workato API; it has zero effect on git.** To also preserve local changes in your git remote, run git separately in the workspace repository:

```bash
git add projects/<project-name>/
git commit -m "<msg>"
git push origin
```

Do not assume "I ran /push-project, so the history is preserved."
