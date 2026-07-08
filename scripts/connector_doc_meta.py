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


_KV = re.compile(r"^\s*[A-Za-z_][\w-]*\s*:\s*.*$")


def _looks_like_frontmatter(inner) -> bool:
    """A leading `---`…`---` block is frontmatter only if every non-blank inner
    line is a `key: value` pair. This keeps a document that opens with a `---`
    horizontal rule (prose between two rules) from being eaten as metadata."""
    non_blank = [ln for ln in inner if ln.strip()]
    return bool(non_blank) and all(_KV.match(ln) for ln in non_blank)


def strip_frontmatter(text: str):
    """Return (meta_lines, body). meta_lines is the raw YAML block WITHOUT the
    fences (empty list if no frontmatter). A frontmatter block is a leading
    '---' line, `key: value` lines, and a closing '---'."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return [], text
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            inner = lines[1:i]
            if not _looks_like_frontmatter(inner):
                return [], text  # a '---' horizontal rule, not frontmatter
            body = "\n".join(lines[i + 1:])
            if text.endswith("\n"):
                body += "\n"
            return inner, body.lstrip("\n")
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


def _cells(row: str):
    return [c.strip() for c in row.strip().strip("|").split("|")]


def _is_sep_row(s: str) -> bool:
    return s.startswith("|--") or set(s) <= {"|", "-", " ", ":"}


def _description_cells_filled(body: str) -> bool:
    """True if a table that HAS a Description column has any data row with a
    non-empty Description cell. Header-aware: we only judge a table once we've
    seen a header row whose last column is 'Description' — this avoids treating
    a 3-column table's Batch column, or an em/en-dash placeholder, as a
    description (which would over-count tier B for future re-synced docs)."""
    desc_col = None  # index of the Description column in the current table
    for ln in body.splitlines():
        s = ln.strip()
        if not s.startswith("|"):
            desc_col = None  # table ended
            continue
        if _is_sep_row(s):
            continue
        cells = _cells(s)
        low = [c.lower() for c in cells]
        if "description" in low:  # header row
            desc_col = low.index("description")
            continue
        if desc_col is None or desc_col >= len(cells):
            continue
        # strip bracket markers ([deprecated]) and dash placeholders (- – —)
        desc_clean = re.sub(r"\[[^\]]*\]", "", cells[desc_col]).strip(" -–—")
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
