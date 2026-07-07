#!/usr/bin/env python3
"""Backfill / refresh value-density frontmatter on kit connector docs (issue #12).

Idempotent: derives `source` and `tier` from each doc's body (via the shared
connector_doc_meta rules) and writes them into a leading YAML frontmatter block.
`synced_at` is preserved if it already holds a real date; otherwise it is written
as `unknown` (the real value is unknown for the bulk-generated corpus — the update
pipeline, issue #12 Phase 3, replaces it with an ISO date on a real re-sync).

Usage:
    python3 scripts/backfill_connector_frontmatter.py [--check]

--check exits non-zero if any doc would change (for CI / pre-commit); no writes.
"""
import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from connector_doc_meta import derive_meta, parse_frontmatter, strip_frontmatter  # noqa: E402

CONN = Path(__file__).resolve().parent.parent / "plugin" / "docs" / "connectors"
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _render(text: str) -> str:
    meta = derive_meta(text)
    existing = parse_frontmatter(text)
    synced = existing.get("synced_at", "")
    if not _DATE.match(synced or ""):
        synced = "unknown"
    _, body = strip_frontmatter(text)
    fm = f"---\nsource: {meta['source']}\nsynced_at: {synced}\ntier: {meta['tier']}\n---\n"
    return fm + body


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="report drift, write nothing")
    args = ap.parse_args()

    changed = []
    for p in sorted(CONN.glob("*.md")):
        if p.name == "_index.md":
            continue
        text = p.read_text(encoding="utf-8")
        new = _render(text)
        if new != text:
            changed.append(p.name)
            if not args.check:
                p.write_text(new, encoding="utf-8")

    if args.check:
        if changed:
            print(f"{len(changed)} connector docs need frontmatter backfill:")
            print("\n".join(f"  {n}" for n in changed[:20]))
            return 1
        print("all connector docs have up-to-date frontmatter")
        return 0
    print(f"backfilled {len(changed)} connector docs"
          + (f" (first: {changed[:5]})" if changed else " (none needed)"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
