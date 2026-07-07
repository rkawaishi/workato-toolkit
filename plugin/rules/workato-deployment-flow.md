---
paths:
  - "projects/**"
  - ".workatoenv"
---

# Workato deployment flow (inviolable)

## The rule

**Push always targets dev.** Promotion to test or prod must go through Workato's **Deploy** feature (UI or Recipe Lifecycle Management API).

> Never run `workato push` against a `<org>-test` or `<org>-prod` profile.
> Never script around deployment approvals.
> If unsure which environment a profile points at, **default to dev**.

This rule applies to AI agents and human developers alike. It exists because:

- A direct push to test or prod skips release-manager review.
- A direct push leaves no manifest, so the deployment cannot be audited or rolled back.
- A direct push silently overwrites whatever is currently running in that environment.

## Pre-flight checks before every push

Run these in order. **Abort the push if any check fails. There is no confirmation-prompt escape hatch — the rule is inviolable.**

> **Mechanical enforcement (Claude Code):** the plugin's `validate-before-push`
> PreToolUse hook resolves the profile itself (`--profile` flag → `.workatoenv`
> `workspace_id` → `current_profile`) and refuses `workato push` and
> `workato recipes start|stop` with exit 2 when the resolved profile does not
> end in `-dev`. The steps below explain the reasoning and remain the manual
> procedure where hooks are unavailable.

1. **Read `.workatoenv`** and extract `workspace_id`.
2. **Resolve the profile** via `python3 scripts/workato-api.py profile show`.
3. **Confirm the profile name ends with `-dev`.** Anything else — `-test`, `-prod`, `-production`, `-staging`, `-qa`, or any non-`-dev` suffix — is a hard stop. Abort and tell the user:

   ```
   Refusing to push: the resolved profile is <profile-name>, which does not match the dev convention (<org>-dev).
   Push must target dev. Options:
     (a) Switch to a dev profile: workato profiles use <org>-dev
     (b) If <profile-name> is in fact your dev workspace, rename it to follow the <org>-dev convention.
   To promote to test/prod, use the Deploy feature in the Workato UI.
   ```

   Do **not** ask the user for confirmation to proceed. The convention exists specifically so that AI agents can reason about the target environment from the profile name alone; honoring custom names ad-hoc defeats the safety guarantee.

4. **Confirm `workspace_id` matches a dev workspace.** If your organization tags workspaces (e.g. in a comment field), verify the tag says dev.

## When the user asks "push to prod"

Do not do it. Reply with:

```
Direct push to prod is not allowed. To release to prod:

1. Push to dev (workato push, with the <org>-dev profile).
2. Verify in the dev workspace.
3. Promote dev → test with the Deploy feature: /deploy-project run --to test
   (or the UI: open the project and click Deploy → test). Get QA sign-off.
4. Promote test → prod: /deploy-project run --to prod from a <org>-test profile,
   or the UI. The release manager's approval happens in the Workato UI and stays manual.

See @docs/platform/environments.md for the full Deploy flow.
```

## When you must read from test or prod

Reading (pull, list) is allowed against any profile because it does not mutate the remote. Use it sparingly — for example, to diff dev against prod when investigating a release issue:

```bash
# Allowed
workato pull --profile <org>-prod   # into a scratch directory

# Forbidden
workato push --profile <org>-prod
```

## CLI/API operations the rule covers

| Operation | Against `<org>-dev` | Against `<org>-test` | Against `<org>-prod` |
|---|---|---|---|
| `workato push` | ✅ | ❌ refuse | ❌ refuse |
| `workato push --delete` | ✅ (with care) | ❌ refuse | ❌ refuse |
| `workato push --restart-recipes` | ✅ | ❌ refuse | ❌ refuse |
| `workato pull` | ✅ | ✅ | ✅ |
| `workato recipes start --all` | ✅ | ❌ refuse | ❌ refuse |
| `python3 scripts/workato-api.py sdk push` | ✅ | ❌ refuse | ❌ refuse |
| `POST /api/deployments/{id}/approve` | n/a | ❌ never script | ❌ never script |

## Related

- `@docs/platform/environments.md` — environment roles and the Deploy feature
- `@docs/platform/cli-profiles.md` — profile naming and push/pull matrix
- `@.claude/rules/workato-cli.md` — Platform CLI commands
- `@.claude/rules/workato-cli-autonomy.md` — when the CLI is the right answer
