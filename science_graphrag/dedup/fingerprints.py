from __future__ import annotations

import hashlib


def work_pair_fingerprint(workspace_id: str, work_id_a: str, work_id_b: str) -> str:
    a, b = sorted((str(work_id_a).strip(), str(work_id_b).strip()))
    raw = f"{str(workspace_id).strip()}|{a}|{b}".encode()
    return hashlib.sha256(raw).hexdigest()


def author_pair_fingerprint(workspace_id: str, author_id_a: str, author_id_b: str) -> str:
    a, b = sorted((str(author_id_a).strip(), str(author_id_b).strip()))
    raw = f"{str(workspace_id).strip()}|author|{a}|{b}".encode()
    return hashlib.sha256(raw).hexdigest()


def make_entity_pair_fingerprint(
    workspace_id: str | None,
    entity_type: str,
    entity_id_a: str,
    entity_id_b: str,
) -> str:
    """Stable fingerprint for one candidate duplicate pair inside an entity type."""
    a, b = sorted((str(entity_id_a).strip(), str(entity_id_b).strip()))
    raw = f"{str(workspace_id or '').strip()}|{str(entity_type).strip().lower()}|{a}|{b}".encode()
    return hashlib.sha256(raw).hexdigest()
