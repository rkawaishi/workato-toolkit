# Recipe construction design patterns (kit canonical)

Catalog of patterns commonly used when building Recipes.
`/workato-create recipe` and `/plan` reference this when generating new Recipes.

This file is **kit canonical** and is updated only by kit maintainers (read-only).
General patterns learned by an organization are accumulated in `org/docs/patterns/recipe-patterns/_index.md`,
and `/workato-create recipe` and `/plan` read both (see `@.claude/rules/org-knowledge-overlay.md`).

## Pattern list

| Pattern name | File | When to apply |
|---|---|---|
| Pagination loop | pagination-loop.md | Fetching all records from an API (offset / token-based) |

## How to use patterns

- `/learn-pattern` - experts record and update patterns (writes to `org/docs/patterns/recipe-patterns/` or `projects/docs/patterns/`)
- `/workato-create recipe` - apply patterns when designing step composition
- `/plan` - propose applicable patterns when mapping spec.md into Workato configuration
