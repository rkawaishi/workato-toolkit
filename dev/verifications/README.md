# dev/verifications/ — runtime verification records

Results of verifications that only a real environment can answer: self-install
smokes, release fresh-install checks, subagent context probes (issue #22),
Workato-API behavior probes. Automated guards live in `tests/`; this directory
is for what a human (or an interactive session) observed.

## Convention

- One file per verification run: `YYYY-MM-DD-<topic>.md`
  (e.g. `2026-07-10-self-install-smoke.md`).
- Contents: **what was verified** (checklist with pass/fail per item),
  **environment** (editor version, OS, plugin ref/commit), **observations**
  (verbatim where surprising), **follow-ups** (issues filed).
- Start from the checklist that `scripts/self-install-smoke.sh` prints
  (section 3) or the relevant issue's checklist (e.g. #32 Phase A).
- Never record tokens or workspace credentials.

These are point-in-time records like `dev/handovers/` — no status frontmatter.
