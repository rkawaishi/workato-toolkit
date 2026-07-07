"""Derive value-density metadata for a kit connector doc (issue #12, Phase 1).

Pure functions — no I/O — so both the backfill script and the test guard import
the same derivation rules. A connector doc's quality `tier` and provenance
`source` are inferred from its content:

- tier A: has per-action field details (Input/Output fields sections)
- tier B: no field details, but the Triggers/Actions table has filled
          Description cells (the API gave descriptions)
- tier C: bare generated table only — Description cells empty

- source manual: shows hand enrichment (field details, a Learning summary,
                 or free-form Notes prose) — someone worked on it
- source api:    bare generated tables only

`synced_at` is deliberately NOT derived: the real value is unknown for the
bulk-generated docs, so the backfill writes `unknown` and the update pipeline
(issue #12 Phase 3) replaces it with a real ISO date. The guard accepts either.
"""
import re

VALID_SOURCES = ("api", "manual", "learned")
VALID_TIERS = ("A", "B", "C")


def strip_frontmatter(text: str):
    """Return (meta_lines, body). meta_lines is the raw YAML block WITHOUT the
    fences (empty list if no frontmatter). A frontmatter block is a leading
    '---' line, YAML lines, and a closing '---'."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return [], text
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            body = "\n".join(lines[i + 1:])
            if text.endswith("\n"):
                body += "\n"
            return lines[1:i], body.lstrip("\n")
    # no closing fence — treat as no frontmatter (don't eat the whole file)
    return [], text


def parse_frontmatter(text: str) -> dict:
    """Parse the simple `key: value` frontmatter into a dict (values stay str)."""
    meta_lines, _ = strip_frontmatter(text)
    out = {}
    for ln in meta_lines:
        m = re.match(r"\s*([A-Za-z_]+)\s*:\s*(.*?)\s*$", ln)
        if m:
            out[m.group(1)] = m.group(2)
    return out


def _has_field_details(body: str) -> bool:
    # per-action input/output field sections, or a dedicated Field details block
    return bool(
        re.search(r"^#+\s*(Input|Output) fields\b", body, re.MULTILINE)
        or re.search(r"^#+\s*Field details\b", body, re.MULTILINE)
    )


def _has_hand_prose(body: str) -> bool:
    return bool(
        re.search(r"^#+\s*(Learning summary|Notes)\b", body, re.MULTILINE)
    )


def _description_cells_filled(body: str) -> bool:
    """True if any Triggers/Actions table row has a non-empty final (Description)
    cell. Table rows look like `| Name | internal | batch | desc |` — the header
    and separator rows are skipped."""
    for ln in body.splitlines():
        s = ln.strip()
        if not s.startswith("|") or s.startswith("|--") or set(s) <= {"|", "-", " ", ":"}:
            continue
        cells = [c.strip() for c in s.strip("|").split("|")]
        if len(cells) < 2:
            continue
        header_like = cells[0].lower() in ("name",) or "internal name" in " ".join(cells).lower()
        if header_like:
            continue
        # the description is the last cell; ignore bracket-only markers like [deprecated]
        desc = cells[-1]
        desc_clean = re.sub(r"\[[^\]]*\]", "", desc).strip()
        if desc_clean:
            return True
    return False


def derive_tier(body: str) -> str:
    if _has_field_details(body):
        return "A"
    if _description_cells_filled(body):
        return "B"
    return "C"


def derive_source(body: str) -> str:
    if _has_field_details(body) or _has_hand_prose(body):
        return "manual"
    return "api"


def derive_meta(text: str) -> dict:
    """Derive {source, tier} from a doc's body (frontmatter stripped first)."""
    _, body = strip_frontmatter(text)
    return {"source": derive_source(body), "tier": derive_tier(body)}
