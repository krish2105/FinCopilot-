"""Parse subsidiary names from a 10-K Exhibit 21 ("List of Subsidiaries").

Exhibit 21 is free-form (list or two-column name/jurisdiction), so this uses a
conservative heuristic: keep lines whose leading token looks like a company name,
drop headers and jurisdiction-only rows. Good enough to build a subsidiary graph;
never fabricates.
"""

from __future__ import annotations

import re

_HEADER_RE = re.compile(
    r"exhibit|subsidiar|registrant|jurisdiction|state of|country of|incorporat|organized",
    re.IGNORECASE,
)
# Lines that are always headers even if they contain a company-form token.
_ALWAYS_HEADER = re.compile(
    r"consolidated subsidiar|parent and subsidiar|subsidiaries of|list of subsidiar",
    re.IGNORECASE,
)
# Split a row's name from a trailing jurisdiction (2+ spaces, tab, table pipe, " - ").
_SPLIT_RE = re.compile(r"\s{2,}|\t|\s*\|\s*|\s[-–]\s")
_COMPANY_HINT = re.compile(
    r"\b(inc|llc|ltd|corp|co|company|gmbh|s\.?a\.?|s\.?r\.?l|holdings?|limited|plc|ag|bv|pty)\b",
    re.IGNORECASE,
)

# Common Exhibit-21 jurisdictions (US states + frequent countries) — stripped from
# the trailing token(s), since chunking collapses the name/jurisdiction columns.
_JURISDICTIONS = {
    "delaware",
    "nevada",
    "california",
    "texas",
    "florida",
    "ireland",
    "luxembourg",
    "netherlands",
    "singapore",
    "china",
    "japan",
    "germany",
    "france",
    "canada",
    "switzerland",
    "india",
    "brazil",
    "mexico",
    "australia",
    "spain",
    "italy",
    "bermuda",
    "cayman islands",
    "hong kong",
    "united kingdom",
    "new york",
    "new jersey",
    "north carolina",
    "south carolina",
    "washington",
    "colorado",
    "illinois",
    "massachusetts",
    "virginia",
    "ohio",
    "georgia",
    "arizona",
}


def _strip_jurisdiction(name: str) -> str:
    words = name.split()
    for take in (2, 1):  # try two-word jurisdictions first ("New York")
        if len(words) > take and " ".join(words[-take:]).lower() in _JURISDICTIONS:
            return " ".join(words[:-take]).rstrip(", ")
    return name


def parse_subsidiaries(text: str, limit: int = 200) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for raw in text.splitlines():
        line = re.sub(r"^[•\-*\s]+", "", raw).strip()
        if len(line) < 3 or len(line) > 120:
            continue
        if _ALWAYS_HEADER.search(line):
            continue
        if _HEADER_RE.search(line) and not _COMPANY_HINT.search(line):
            continue
        name = re.sub(r"[,\s|]+$", "", _SPLIT_RE.split(line)[0].strip())  # keep "Inc." periods
        name = _strip_jurisdiction(name)
        if len(name) < 3 or not re.search(r"[A-Za-z]", name):
            continue
        # Require either a company-form token or Title-Case multi-word name.
        words = name.split()
        titleish = len(words) >= 2 and sum(1 for w in words if w[:1].isupper()) >= 2
        if not (_COMPANY_HINT.search(name) or titleish):
            continue
        key = name.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(name)
        if len(out) >= limit:
            break
    return out
