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


def _split_frontmatter(text: str):
    """Return (meta, body). meta is a {key: value} dict from a leading YAML
    `---` block (empty if none); body is the doc without it. Kept deliberately
    tiny — the connector frontmatter is flat `key: value` lines only."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, text
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            meta = {}
            for ln in lines[1:i]:
                if ":" in ln:
                    k, _, v = ln.partition(":")
                    meta[k.strip()] = v.strip()
            body = "\n".join(lines[i + 1:]).lstrip("\n")
            if text.endswith("\n") and not body.endswith("\n"):
                body += "\n"
            return meta, body
    return {}, text  # unterminated — treat as no frontmatter


def _provenance_note(meta: dict) -> str:
    """One-line freshness/quality banner from frontmatter, or '' if none."""
    if not meta:
        return ""
    bits = []
    if meta.get("source"):
        bits.append(f"source={meta['source']}")
    if meta.get("synced_at"):
        bits.append(f"synced={meta['synced_at']}")
    if meta.get("tier"):
        bits.append(f"tier={meta['tier']}")
    return f"> _provenance: {', '.join(bits)}_\n\n" if bits else ""


def _heading_lines(text: str) -> list:
    """(line_index, level, title) for every real markdown heading — lines
    starting with '#' INSIDE fenced code blocks (bash comments etc.) are not
    headings and must not terminate sections or pollute heading lists."""
    out, in_fence = [], False
    for i, ln in enumerate(text.splitlines()):
        stripped = ln.lstrip()
        if stripped.startswith("```") or stripped.startswith("~~~"):
            in_fence = not in_fence
            continue
        if not in_fence and ln.startswith("#"):
            out.append((i, len(ln) - len(ln.lstrip("#")), ln.lstrip("#").strip()))
    return out


def _headings(text: str) -> list:
    return [title for _, _, title in _heading_lines(text)]


def _extract_section(text: str, section: str) -> Optional[str]:
    """Return the block from the heading matching `section` (case-insensitive
    substring) up to the next heading of the same or higher level."""
    lines = text.splitlines()
    headings = _heading_lines(text)
    start = level = None
    for i, lvl, title in headings:
        if section.lower() in title.lower():
            start, level = i, lvl
            break
    if start is None:
        return None
    end = len(lines)
    for j, lvl, _ in headings:
        if j > start and lvl <= level:
            end = j
            break
    return "\n".join(lines[start:end]).rstrip() + "\n"


def resolve_doc(
    kit_dir: Path, org_dir: Optional[Path], rel: str, section: Optional[str] = None
) -> str:
    """Return the doc for `rel`, applying the org overlay (org wins on conflict).

    - both present: org section first (authoritative), then kit baseline.
    - only one present: return it.
    - neither: NOT FOUND sentinel.
    - path traversal: INVALID PATH sentinel.
    - `section`: return only the matching heading's block (case-insensitive
      substring; applied to kit and org texts independently). On a miss,
      a SECTION NOT FOUND sentinel lists the available headings.
    """
    norm = _norm(rel)
    if norm is None:
        return f"INVALID PATH: {rel!r} (path traversal is not allowed)"

    kit_raw = _read(kit_dir, norm)
    org_raw = _read(org_dir, norm)

    if kit_raw is None and org_raw is None:
        return f"NOT FOUND: {norm} (checked kit docs and org/docs)"

    # Strip frontmatter from the served body (readers get prose, not raw YAML);
    # keep the provenance as a one-line banner. Prefer kit provenance (the
    # canonical baseline); fall back to org's when kit is absent.
    kit_meta, kit_text = _split_frontmatter(kit_raw) if kit_raw is not None else ({}, None)
    org_meta, org_text = _split_frontmatter(org_raw) if org_raw is not None else ({}, None)
    banner = _provenance_note(kit_meta or org_meta)

    if section:
        kit_sec = _extract_section(kit_text, section) if kit_text else None
        org_sec = _extract_section(org_text, section) if org_text else None
        if kit_sec is None and org_sec is None:
            available = _headings((org_text or "") + "\n" + (kit_text or ""))
            return (
                f"SECTION NOT FOUND: {section!r} in {norm}. "
                f"Available headings: {', '.join(available) or '(none)'}"
            )
        # A doc can exist yet lack the section — say so instead of the
        # misleading 'org-only / kit-only' framing of the whole-doc branches.
        if org_sec is not None and kit_sec is None and kit_text is not None:
            return (
                f"# {norm} § {section} (org overlay only — the kit doc has no "
                f"matching section)\n\n{org_sec}\n"
            )
        if kit_sec is not None and org_sec is None and org_text is not None:
            return (
                f"# {norm} § {section} (kit only — the org overlay has no "
                f"matching section)\n\n{kit_sec}\n"
            )
        kit_text, org_text = kit_sec, org_sec

    if org_text is not None and kit_text is not None:
        return (
            f"# {norm} (org overlay applied — the org version overrides the kit on conflict)\n\n"
            f"{banner}"
            f"## Organization (authoritative — org/docs/{norm})\n\n{org_text}\n\n"
            f"## Kit baseline (docs/{norm})\n\n{kit_text}\n"
        )

    if org_text is not None:
        return f"# {norm} (org-only — no kit baseline)\n\n{banner}{org_text}\n"

    return f"{banner}{kit_text}" if banner else kit_text


def list_docs(kit_dir: Path, org_dir: Optional[Path], prefix: str = "") -> list:
    """List available doc paths (union of kit + org), sorted & deduped, filtered by prefix."""
    found = set()
    for base in (kit_dir, org_dir):
        if base is None or not base.is_dir():
            continue
        for p in base.rglob("*.md"):
            rel = p.relative_to(base).as_posix()  # '/' on every platform
            if rel.startswith(prefix):
                found.add(rel)
    return sorted(found)


SEARCH_MAX_RESULTS = 50


def search_docs(
    kit_dir: Path, org_dir: Optional[Path], query: str, prefix: str = ""
) -> list:
    """Case-insensitive substring search across kit + org docs.

    Returns "path:line: text" strings (org hits are prefixed org/docs/),
    capped at SEARCH_MAX_RESULTS with a truncation notice.
    """
    q = query.lower()
    hits = []
    # org first: the overlay is authoritative, so the result cap must never
    # starve org hits in favor of kit ones.
    for base, label in ((org_dir, "org/docs/"), (kit_dir, "")):
        if base is None or not base.is_dir():
            continue
        for p in sorted(base.rglob("*.md")):
            rel = p.relative_to(base).as_posix()
            if not rel.startswith(prefix):
                continue
            try:
                lines = p.read_text(encoding="utf-8").splitlines()
            except (OSError, UnicodeError):
                continue
            # frontmatter is metadata, not content — don't return its lines as
            # search hits (line numbers below stay 1-based over the whole file).
            fm_end = 0
            if lines and lines[0].strip() == "---":
                for j in range(1, len(lines)):
                    if lines[j].strip() == "---":
                        fm_end = j + 1
                        break
            for i, ln in enumerate(lines, 1):
                if i <= fm_end:
                    continue
                if q in ln.lower():
                    hits.append(f"{label}{rel}:{i}: {ln.strip()}")
                    if len(hits) >= SEARCH_MAX_RESULTS:
                        hits.append(
                            f"... truncated at {SEARCH_MAX_RESULTS} matches — "
                            "narrow the query or prefix"
                        )
                        return hits
    return hits
