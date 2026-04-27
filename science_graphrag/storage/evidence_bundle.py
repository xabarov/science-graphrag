"""Phase 4: zip bundles of S3 object bodies for incident export."""

from __future__ import annotations

import io
import zipfile
from pathlib import Path
from typing import Any


def _safe_zip_entry_name(name: str) -> str:
    """
    Normalize archive member names to reduce zip-slip risk on extract.

    Drops empty / ``.`` / ``..`` segments and strips leading slashes.
    """
    raw = (name or "").strip().replace("\\", "/").lstrip("/")
    parts: list[str] = []
    for seg in raw.split("/"):
        if seg in ("", ".", ".."):
            continue
        if ".." in seg:
            seg = seg.replace("..", "__")
        parts.append(seg)
    return "/".join(parts) if parts else "unnamed.bin"


def build_evidence_zip_bytes(
    client: Any,
    bucket: str,
    keys: list[str],
    *,
    extra_files: list[tuple[str, Path]] | None = None,
) -> bytes:
    """
    Download each object key and pack into a zip (keys become archive paths with ``/``).

    ``extra_files`` entries are ``(archive_name, filesystem_path)`` for local summaries, etc.
    """

    buf = io.BytesIO()
    seen: set[str] = set()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for key in keys:
            k = (key or "").strip()
            if not k or k in seen:
                continue
            seen.add(k)
            resp = client.get_object(Bucket=bucket, Key=k)
            body = resp["Body"].read()
            arc = _safe_zip_entry_name(k)
            zf.writestr(arc, body)
        for arc_name, fs_path in extra_files or []:
            p = Path(fs_path)
            if not p.is_file():
                continue
            zf.write(p, arcname=_safe_zip_entry_name(arc_name))
    return buf.getvalue()
