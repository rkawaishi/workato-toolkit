# dev/ — development documents

Design specs, implementation plans, and session handovers for building this
plugin. Nothing here ships to users.

## Lifecycle convention

Every file under `plans/` and `specs/` carries YAML frontmatter
(guarded by `tests/test_dev_docs.py`):

```yaml
---
status: draft | active | done | superseded
superseded_by: <issue URL or doc path>   # required when superseded
---
```

- **draft** — written, not yet approved/started.
- **active** — currently being executed. At most a couple at a time.
- **done** — executed to completion. **Record verification results by
  appending a section to the plan itself** (precedent:
  `2026-07-06-cc-only-plugin-separation-plan.md`), then flip the status.
- **superseded** — no longer reflects reality (direction changed, or the
  living items moved to issues). Point `superseded_by` at the successor.
  Superseded docs are kept, not deleted — they are the decision record.

`handovers/` files are point-in-time records; they never get a status.

## Issue vs spec — where does a decision go?

- **Issue only**: the decision and its rationale fit one screen, touch one
  component, and need no diagrams/comparison tables (most backlog items).
- **`specs/` + pointer issue**: cross-component designs, option comparisons,
  anything a future session must re-read to understand the architecture.
- Plans that execute a spec go to `plans/`; a plan for issue-sized work is
  optional.

## Naming

`YYYY-MM-DD-<slug>-{design|plan|prfaq}.md` (date = creation date).

## Index

| Doc | Status |
|---|---|
| specs/2026-06-07 plugin-distribution-design | done |
| specs/2026-06-07 plugin-distribution-prfaq | done |
| specs/2026-07-06 cc-only-plugin-dev-separation-design | done |
| specs/2026-07-06 workato-integration-skills-design | done |
| plans/P1 distribution skeleton … plans/P5 release prep (7 files) | done |
| plans/P6 runtime-release roadmap | superseded → [#32](https://github.com/rkawaishi/workato-toolkit/issues/32) |
| plans/2026-07-06 cc-only separation / integration skills | done |

(One row per doc when statuses diverge; keep this table honest when adding
docs — the frontmatter is the source of truth, this table is the reading aid.)
