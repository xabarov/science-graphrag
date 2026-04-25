"""Prompt contracts for work metadata extraction."""

from __future__ import annotations

import hashlib

MAX_META_CHARS = 60_000
MAX_REFS_PROMPT_CHARS = 90_000

SYSTEM_FENCE = (
    "You extract structured metadata from scholarly Markdown (possibly inside a fenced "
    "` ```markdown ` wrapper). Ignore wrapper fences; read the inner # title, author block, "
    "`## Abstract`, and `## References` like a normal paper. "
    "Return only fields supported by the text; use null for unknown. "
    "Do not invent DOIs, arXiv ids, or titles. "
    "For references without DOI, still fill arxiv_id and year when printed."
)

SYSTEM_META_NORMALIZE = (
    "For title and abstract fields, normalize PDF line-break artifacts: join words "
    "split by an end-of-line hyphen or spacing artifact (e.g. `frame- work` -> "
    "`framework`, `improve-ments` -> `improvements`, `ob- ject` -> `object`). "
    "Keep genuine compound terms hyphenated (e.g. `real-time`, `one-stage`, "
    "`task-aligned`)."
)


def extraction_layer1_prompt_fingerprint() -> str:
    """Stable id for layer-1 prompt contract."""

    material = "|".join(
        (
            SYSTEM_FENCE,
            SYSTEM_META_NORMALIZE,
            f"MAX_META_CHARS={MAX_META_CHARS}",
            f"MAX_REFS_PROMPT_CHARS={MAX_REFS_PROMPT_CHARS}",
            "schemas=v1",
        ),
    )
    digest = hashlib.sha256(material.encode("utf-8")).hexdigest()[:20]
    return f"sha256-20:{digest}"
