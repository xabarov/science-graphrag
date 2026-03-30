from __future__ import annotations

import hashlib
import re

_DOI_RE = re.compile(r"\b(10\.\d{4,9}/\S+)\b", re.IGNORECASE)


def normalize_doi(raw: str | None) -> str | None:
    if not raw:
        return None
    s = raw.strip()
    s = s.replace("https://doi.org/", "").replace("http://doi.org/", "")
    s = s.replace("doi:", "").strip()
    m = _DOI_RE.search(s)
    if m:
        return m.group(1).rstrip(").,;]")
    return None


def find_doi_in_text(text: str) -> str | None:
    m = _DOI_RE.search(text)
    return normalize_doi(m.group(1)) if m else None


def title_fingerprint(title: str, year: int | None) -> str:
    base = re.sub(r"\s+", " ", title.lower().strip()) + "|" + str(year or "")
    return hashlib.sha256(base.encode()).hexdigest()[:16]
