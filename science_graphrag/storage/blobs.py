from __future__ import annotations

import hashlib
import shutil
from pathlib import Path
from uuid import uuid4


class BlobStore:
    """Content-addressed file storage under blob_root."""

    def __init__(self, root: Path) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def _path_for_sha(self, sha256_hex: str) -> Path:
        return self.root / "raw" / sha256_hex[:2] / sha256_hex

    def store_file(self, source_path: Path) -> tuple[str, Path]:
        """Copy file into blob store. Returns (sha256_hex, stored_path)."""
        data = source_path.read_bytes()
        sha = hashlib.sha256(data).hexdigest()
        dest = self._path_for_sha(sha)
        dest.parent.mkdir(parents=True, exist_ok=True)
        if not dest.exists():
            shutil.copy2(source_path, dest)
        return sha, dest

    def write_text(self, name: str, text: str) -> Path:
        """Store derived text under a unique id path (not content-addressed)."""
        doc_id = uuid4().hex
        rel = Path("derived") / doc_id / name
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path
