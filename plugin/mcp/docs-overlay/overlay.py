"""Pure docs-overlay logic: merge kit docs with org docs (org wins).

No FastMCP / env dependency — callers pass resolved directories.
"""
from pathlib import Path
from typing import Optional


def _norm(rel: str) -> Optional[str]:
    """Normalize a relative doc path. Return None if it escapes the root."""
    rel = rel.strip().lstrip("/")
    if not rel.endswith(".md"):
        rel = rel + ".md"
    parts = [p for p in Path(rel).parts if p not in ("", ".")]
    if any(p == ".." for p in parts):
        return None
    return str(Path(*parts)) if parts else None


def _read(base: Optional[Path], rel: str) -> Optional[str]:
    if base is None:
        return None
    p = base / rel
    if p.is_file():
        return p.read_text(encoding="utf-8")
    return None


def resolve_doc(kit_dir: Path, org_dir: Optional[Path], rel: str) -> str:
    """Return the doc for `rel`, applying the org overlay (org wins on conflict).

    - both present: org section first (authoritative), then kit baseline.
    - only one present: return it.
    - neither: NOT FOUND sentinel.
    - path traversal: INVALID PATH sentinel.
    """
    norm = _norm(rel)
    if norm is None:
        return f"INVALID PATH: {rel!r} (path traversal is not allowed)"

    kit_text = _read(kit_dir, norm)
    org_text = _read(org_dir, norm)

    if kit_text is None and org_text is None:
        return f"NOT FOUND: {norm} (checked kit docs and org/docs)"

    if org_text is not None and kit_text is not None:
        return (
            f"# {norm} (org overlay applied — the org version overrides the kit on conflict)\n\n"
            f"## Organization (authoritative — org/docs/{norm})\n\n{org_text}\n\n"
            f"## Kit baseline (docs/{norm})\n\n{kit_text}\n"
        )

    if org_text is not None:
        return f"# {norm} (org-only — no kit baseline)\n\n{org_text}\n"

    return kit_text


def list_docs(kit_dir: Path, org_dir: Optional[Path], prefix: str = "") -> list:
    """List available doc paths (union of kit + org), sorted & deduped, filtered by prefix."""
    found = set()
    for base in (kit_dir, org_dir):
        if base is None or not base.is_dir():
            continue
        for p in base.rglob("*.md"):
            rel = str(p.relative_to(base))
            if rel.startswith(prefix):
                found.add(rel)
    return sorted(found)
