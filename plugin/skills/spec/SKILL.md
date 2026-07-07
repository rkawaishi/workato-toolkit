---
description: Capture a feature's requirements (UX, WHAT/WHY) in spec.md, resolve its Open Questions one at a time (clarification mode), and convert legacy DESIGN.md projects via `/spec migrate`. No technical detail — that lives in `/plan`. Japanese prompts are also supported.
allowed-tools: Read, Write, Edit, Glob, Grep, Bash
---

# /spec

Write a feature's **requirements (WHAT/WHY)** to `projects/<project>/specs/<NNN>-<slug>/spec.md`, and resolve every `Open Questions` item before the feature moves on to `/plan`.

This is the first step of the spec-driven workflow. Do not touch the technology stack (Workato configuration); only fix the user experience and business requirements. Mapping to technology is `/plan`'s responsibility.

## Usage

- `/spec <project>` — create a spec.md for a new feature (the sequence number and kebab-case slug are confirmed during the interview)
- `/spec <project>/<NNN>-<slug>` — update an existing spec.md; if unchecked `Open Questions` remain, enter **clarification mode** (see below) and resolve them
- `/spec migrate <project>` — convert a legacy `DESIGN.md` into `specs/<NNN>-<slug>/{spec,plan,tasks}.md` (see below)

## Workflow

```
/spec → /plan → /tasks → /analyze → /implement
  ↑
you are here (clarification happens inside /spec)
```

After `/spec` creates or updates a spec, if any `Open Questions` remain, continue into **clarification mode** in the same session (or stop and resume later with `/spec <project>/<NNN>-<slug>`). Only when none remain, point at `/plan`.

## Procedure (creating a spec)

### 1. Identify the feature

- If `<project>` is missing, ask for the project name.
- If the argument is `<project>/<NNN>-<slug>` and that spec.md exists, switch to **update mode**; if it still has unchecked `Open Questions`, go straight to clarification mode.
- Otherwise `ls projects/<project>/specs/` and pick the **next sequence number** based on existing features (`001`, `002`, ...).
- Confirm a short kebab-case slug with the user.
  - Examples: `it-onboarding`, `expense-approval`, `slack-digest`.
- Final path: `projects/<project>/specs/<NNN>-<slug>/spec.md`.

### 2. UX interview

**Use business language, not technical jargon.** Don't ask everything at once; follow up based on the answers.

```
Tell me about this feature:

1. **Who wants to do what?**
   e.g. submit IT onboarding for a new hire; file an expense for approval

2. **What flow do you have in mind?**
   e.g. fill a form → manager approves → IT team is notified

3. **Who is involved?**
   e.g. requester, manager (approver), IT team (executor)

4. **What does success look like in the end?**
   e.g. a Jira ticket is created and the IT team can start work

5. **Are there existing tools or data sources?**
   e.g. manager info lives in Google Sheets; notifications go to Slack
```

### 3. Summarize and confirm the user experience

Turn the interview into **user stories** and confirm with the user.

```
## User experience (draft)

### Requester
1. Open the form
2. Fill in the details and submit
3. Status changes to "awaiting approval"
4. Receive a notification when approved

### Approver
1. Receive an approval request (notification with buttons)
2. Review and approve or reject
3. Can also act from another channel (e.g. a task page)

### Downstream
- On approval: create an external ticket → notify
- On rejection: notify the requester

Does this match what you have in mind? Anything to add or change?
```

### 4. Extract Open Questions (mandatory for resumability)

Whatever **could not be confirmed** during the interview must be written into `Open Questions`. Clarification mode (below) resolves these.

Typical unresolved items:
- One approver or many? Is hierarchical approval needed?
- Can a rejected request be resubmitted?
- Notifications via Slack, email, or both?
- How long is request data retained?
- Do we need to dedupe against existing accounts?

**Important**: items where there is a tentative answer but it still needs confirmation also go in Open Questions (with a note saying so). Only fully settled items go into the main body.

### 5. Write spec.md

Use the template below. **Do not use Workato terminology** (no Recipe, Datapill, Connection, etc.).

### 6. Next-step guidance

```
✓ Created spec.md: projects/<project>/specs/<NNN>-<slug>/spec.md

<N> Open Questions remain — let's resolve them now, one at a time.
(You can also stop here and resume later with /spec <project>/<NNN>-<slug>.)

(Only if no Open Questions remain)
You can proceed directly to /plan <project>/<NNN>-<slug>.
```

When Open Questions remain, continue directly into clarification mode.

## Resolving Open Questions (clarification mode)

Resolve the unresolved items in spec.md's `## Open Questions` section **one at a time** and reflect each answer in the body of spec.md. This mode runs automatically after creating a spec that still has Open Questions, or explicitly via `/spec <project>/<NNN>-<slug>` on an existing spec.

Closing every ambiguity here, before moving to design, avoids rework downstream.

**Key to resumability**: even if the interview's working state is lost to context exhaustion or an interruption, as long as Open Questions remain in the file you can resume with `/spec <project>/<NNN>-<slug>`.

### 1. Read spec.md

- Read `projects/<project>/specs/<NNN>-<slug>/spec.md`.
- Extract unchecked items (`- [ ] ...`) from the `## Open Questions` section.
- If everything is checked, say "All Open Questions are resolved. Proceed to `/plan`." and stop.

### 2. Ask one question at a time

Present **one question at a time**. Don't batch — answer quality drops when you do.

```
<N> Open Questions remain. Let me confirm them one at a time.

[1/N] <question>

Possible options (if any):
- A: <option>
- B: <option>
- C: Other (free text)

Please answer.
```

### 3. Reflect the answer

As soon as you have an answer, **update spec.md immediately**:

1. Check off the matching Open Question item (`- [x]`).
2. Update the relevant section of the spec body based on the answer.
   - Approver scope decided → update the corresponding role in User Stories.
   - Notification channel decided → update External Touchpoints.
   - Constraint found → add to Constraints / Non-functional.
   - Confirmed out of scope → move to Out of Scope.
3. Append `<YYYY-MM-DD>: <decision> — <reason>` to `## Decisions`.
4. Update `Last updated`.

### 4. Add derived Open Questions

If an answer reveals **new ambiguities**, append them to Open Questions immediately (you can keep resolving them in the same session).

Example:
```
Q: Is there a single approver or multiple?
A: One manager + a department head when needed.
→ New Open Question: "Under what conditions is department-head approval required? Amount / category / role?"
```

### 5. Wrap-up after everything is resolved

When every Open Question is checked off:

```
✓ All Open Questions resolved (<N> total).

Key decisions:
- <summarize 3–5 important entries from Decisions>

Next, proceed to /plan <project>/<NNN>-<slug> to map this into Workato configuration.
```

### Tips for asking

**Turn yes/no questions into multiple choice**

```
✗ "Is resubmission allowed?" (open-ended)
○ "After a rejection, do you allow resubmission? A: yes (edit + resubmit), B: yes (only as a new request), C: no"
```

**Ask in business scenarios, not technology choices**

```
✗ "Is the Slack notification channel public or private?"
○ "When an approval request lands, who needs to see it? Only the approver / the whole department / the whole company?"
```

**Accept "I don't know"**

If the user says "I can't decide right now":
- Keep the item in Open Questions but rewrite it as `- [ ] <question> (deferred: undecided as of <YYYY-MM-DD>)`.
- Treat it in `/plan` as a **placeholder + Decision Required**.
- The user can re-run `/spec <project>/<NNN>-<slug>` later.

### Reflection rules

| Question kind | Section to update |
|---|---|
| User behavior or experience | User Stories |
| Success conditions / observable points | Success Criteria |
| External services we integrate with | External Touchpoints |
| Performance, security, operational requirements | Constraints / Non-functional |
| What we are not going to do | Out of Scope |
| Why we decided this way | Decisions |

**Prohibited**: do not introduce technical terms (Recipe, Datapill, Workflow App, etc.) into spec.md. Mapping to technology is `/plan`'s responsibility.

## /spec migrate <project> (legacy DESIGN.md conversion)

**Best-effort split** of an existing legacy `projects/<project>/DESIGN.md` into the spec-driven workflow artifacts (`spec.md` / `plan.md` / `tasks.md`). Because mapping cannot be fully mechanical, write ambiguous points into `Open Questions` / `Open Issues` so the user can continue in clarification mode.

The former standalone design skill (view / update / new) is retired entirely; only this migration mode survives, as a mode of `/spec`.

### Preconditions

1. Read `projects/<project>/DESIGN.md`. If missing, "No DESIGN.md found. Create a spec with `/spec <project>`." and abort.
2. If `projects/<project>/specs/` already exists and is non-empty, confirm:
   ```
   Artifacts already exist under specs/:
   - specs/001-foo/spec.md
   - specs/001-foo/plan.md

   What do you want to do?
   1. Abort (manual merge recommended)
   2. Generate in parallel as specs/002-migrated/
   3. Overwrite specs/001-foo/ (destructive, not recommended)
   ```

### Determining the destination

- Feature slug: confirm with the user (defaults to `main` or derived from the project name).
- Sequence number: **follows the precondition outcome**:
  - `specs/` missing or empty → `001`.
  - Existing specs/ and **option 2 (generate in parallel)** chosen → max sequence under `specs/` + 1 (e.g. with `001-foo/` present, use `002`).
  - Existing specs/ and **option 3 (overwrite)** chosen → reuse the existing sequence number you target (e.g. choosing `specs/001-foo/` keeps `001`).
- Final path: `projects/<project>/specs/<NNN>-<slug>/{spec,plan,tasks}.md` (`<NNN>` is the sequence determined above).

### Section mapping

Route each DESIGN.md section per:

| DESIGN.md section | Destination | Notes |
|---|---|---|
| `# <title>` | spec.md `# <title>` + plan.md `# <title> — Plan` + tasks.md `# <title> — Tasks` | Shared title |
| `## Status`, `Last updated` | `## Metadata` of each artifact | Propagate to spec/plan/tasks |
| Role-by-role steps under `## User Experience` | spec.md `## User Stories` | Copy nearly as-is |
| `## Architecture` `### Applied Patterns` | plan.md `## Applied Patterns` | Preserve pattern names and reference links |
| `## Architecture` `### Reused existing assets` | plan.md `## Reused Assets` | Asset names and uses |
| `## Architecture` `### New components` `- **Data Table**:` | plan.md `## New Components` `### Data Tables` | Includes field list |
| `## Architecture` `### New components` `- **Stages**:` | plan.md `## Stage Transitions` | Render as a transition diagram |
| `## Architecture` `### New components` `- **External integrations**:` | plan.md `## New Components` `### Connections` or spec.md `## External Touchpoints` | Provider-only goes to spec; technical detail to plan |
| `## Architecture` `### New components` `- **Recipe composition**:` | plan.md `## New Components` `### Recipes` | Split by main / Function / handler |
| `## Implementation Checklist` | tasks.md `## Tasks` | Infer and attach kind tags (see below) |
| `## Unlearned Actions` table | plan.md `## Unlearned Actions` table + `[learn]` tasks in tasks.md | Reflect in both |
| `## Decisions` | UX-flavoured → spec.md `## Decisions` / technical → plan.md `## Decisions` | Judge from text; when in doubt, send to spec |
| `## Open Issues` | plan.md `## Open Issues` | Post-deploy verification items go to plan |

### Kind tags for the Implementation Checklist

Attach exactly one kind tag to every generated tasks.md item. The canonical tag registry — which tag exists and which skill owns it — lives in **`/tasks`' kind-tag table**; infer the best-matching tag from each checklist item's wording (e.g. table/schema wording → `[data-table]`, form/screen wording → `[page]`, recipe wording → `[recipe]` / `[function]`). When no tag fits, use `[manual]` and also append the item to `Open Issues` for manual review.

Dependencies are inferred best-effort (e.g. `[recipe]` after `[data-table]` and `[connection]`). For low-confidence cases, note `(depends: ?)` so `/analyze` can flag it.

### Generating Open Questions / Open Issues

Write any items you cannot mechanically determine into one of:

- spec.md `## Open Questions`:
  - Unclear User Story roles.
  - Success Criteria not present in DESIGN.md (needs interview).
  - Out of Scope not made explicit (needs confirmation).
- plan.md `## Open Issues`:
  - Resources not fetched (should be fetched in `/plan` Step 2).
  - Pattern-application items with low confidence.
  - Unclear stage transitions.
- tasks.md may always contain `[manual]` items that need manual review.

### Post-migration processing

1. **Rename DESIGN.md to `DESIGN.md.legacy.<YYYY-MM-DD>`** (do not delete; keep for later reference).
2. Ensure `projects/<project>/.workatoignore` exists by running the kit helper (creates it from the base template, or appends only missing entries — idempotent, never removes lines):

   ```bash
   bash scripts/ensure-workatoignore.sh "projects/<project>"
   ```

   The template already covers `DESIGN.md`, `DESIGN.md.legacy.*` and `specs/`.

### Result message

```
✓ Migrated: projects/<project>/

Generated files:
- specs/001-<slug>/spec.md         (<N> Open Questions)
- specs/001-<slug>/plan.md         (<M> Open Issues)
- specs/001-<slug>/tasks.md        (<T> tasks; <K> are [manual] and need review)

Renamed:
- DESIGN.md → DESIGN.md.legacy.<YYYY-MM-DD>

Next actions:
1. /spec <project>/001-<slug>     — resolve Open Questions (clarification mode)
2. /analyze <project>/001-<slug>  — verify consistency
3. /implement <project>/001-<slug> — continue implementation

Recommended review:
- Do the spec.md User Stories preserve the intent of DESIGN.md?
- Are the tasks.md kind tags reasonable? (If [manual] dominates, reclassify.)
```

### Migration prohibitions

- **Do not delete DESIGN.md**: rename only. Never lose the source.
- **Do not overwrite specs/**: if specs/ already exists, take explicit user confirmation.
- **Do not carry unclear technical terms into spec.md**: if Workato terms (Recipe, datapill, Workflow App, etc.) leaked into User Experience in DESIGN.md, paraphrase them into business language for spec.md (when uncertain, file as Open Questions).

## spec.md template

```markdown
# <Feature name>

## Metadata
- Status: Draft
- Created: <YYYY-MM-DD>
- Last updated: <YYYY-MM-DD>
- Project: <project-name>
- Feature ID: <NNN>-<slug>

## Why
<The business problem, what you want to solve, what value you want. 1–3 paragraphs.>

## User Stories

### <Role 1> (e.g. Requester)
1. <step>
2. <step>
3. <step>

### <Role 2> (e.g. Approver)
1. <step>
2. <step>

### <Role 3> (e.g. Executor)
1. <step>

## Success Criteria
<!-- What constitutes success, written as observable conditions. -->
- [ ] <condition 1>
- [ ] <condition 2>

## External Touchpoints
<!-- External services or data sources we integrate with. Use business names ("ticketing system"), not vendor names; technology choices come in `/plan`. -->
- <service>: <purpose>
- <service>: <purpose>

## Constraints / Non-functional
<!-- Performance, security, operational requirements. Only when applicable. -->
- <constraint>

## Out of Scope
<!-- Explicit non-goals for this feature; what is deferred to a later one. -->
- <item>

## Open Questions
<!-- Unresolved items, addressed in clarification mode. This checklist is the resumption point. -->
- [ ] <question 1>
- [ ] <question 2>

## Decisions
<!-- Important decisions made during the interview, with the reasoning. For future reference. -->
- <YYYY-MM-DD>: <decision> — <reason>
```

## Rules to follow

- **No Workato terminology**: spec.md is technology-agnostic. Don't use words like Recipe, Connection, Datapill, Workflow App — translate them into business terms.
- **Persist Open Questions**: never leave unresolved points only in conversational context — write them to the file. The ability to resume via `/spec <project>/<NNN>-<slug>` after an interruption depends on this.
- **One at a time (clarification mode)**: batching makes answers shallow. Always close the loop on each question — including the file update — before moving to the next.
- **Update the file each time**: do not interview 5 items and write all the changes at the end. Save spec.md after each answer (interruption insurance).
- **Decisions get reasons**: not just `decided on A`, but `decided on A — B is too expensive and C needs user training`.
- **Do not touch DESIGN.md during normal spec work**: if the project still has a legacy DESIGN.md, create spec.md as a new file anyway. Converting DESIGN.md is `/spec migrate`'s job.

## `.workatoignore` management

Every project needs a `.workatoignore` so `workato pull` does not wipe local-only artifacts and `workato push` does not deploy them. The kit ships a base template at `templates/workatoignore.template` (it already covers `specs/`).

When you create spec.md, ensure `projects/<project>/.workatoignore` exists by running the kit helper:

```bash
bash scripts/ensure-workatoignore.sh "projects/<project>"
```

It creates `.workatoignore` from the base template when absent, or appends only the missing entries otherwise (idempotent, never removes lines). Because the template already lists `specs/`, no spec-specific entry is needed.

## Git management

```bash
git add projects/<project-name>/specs/<NNN>-<slug>/spec.md projects/<project-name>/.workatoignore
git commit -m "spec(<project>/<slug>): initial spec"
git push origin
```

After clarification mode, use `git commit -m "spec(<project>/<slug>): resolve open questions"`.
After `/spec migrate`, also stage `projects/<project-name>/DESIGN.md*` and `projects/<project-name>/specs/` with `git commit -m "Migrate legacy design: <project-name>"`.

`workato push` will not deploy spec.md to Workato (it's excluded by `.workatoignore`).
