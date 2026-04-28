"""Regression: shell-exported SCIENCE_GRAPHRAG_BLOB_ROOT must win over repo .env."""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]


def _subprocess_blob_root(*, cwd: Path, env: dict[str, str]) -> str:
    code = "from science_graphrag.config import Settings; print(Settings().blob_root)"
    proc = subprocess.run(
        [sys.executable, "-c", code],
        cwd=str(cwd),
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )
    return proc.stdout.strip()


def _minimal_env(**extra: str) -> dict[str, str]:
    """Fresh env for subprocess: no inherited SCIENCE_GRAPHRAG_* except what we pass."""
    env: dict[str, str] = {
        "PATH": os.environ.get("PATH", "/usr/bin"),
        "HOME": os.environ.get("HOME", "/tmp"),
        "PYTHONPATH": str(_REPO_ROOT),
        "PYTHONNOUSERSITE": "1",
        "LANG": os.environ.get("LANG", "C.UTF-8"),
        "SCIENCE_GRAPHRAG_S3_ACCESS_KEY_ID": "testing",
        "SCIENCE_GRAPHRAG_S3_SECRET_ACCESS_KEY": "testing",
    }
    env.update(extra)
    return env


def test_blob_root_shell_export_wins_over_dotenv_when_skip_host_dotenv_off() -> None:
    """Shell SCIENCE_GRAPHRAG_BLOB_ROOT survives load_dotenv(override=True) in cwd .env."""
    with tempfile.TemporaryDirectory() as tmp:
        cwd = Path(tmp)
        (cwd / ".env").write_text(
            "SCIENCE_GRAPHRAG_BLOB_ROOT=/from_dotenv_file\n"
            "SCIENCE_GRAPHRAG_ARTIFACT_ROOT=/artifacts_dotenv\n",
            encoding="utf-8",
        )
        shell_blob = str(cwd / "from_shell")
        env = _minimal_env(
            SCIENCE_GRAPHRAG_SKIP_HOST_DOTENV="0",
            SCIENCE_GRAPHRAG_BLOB_ROOT=shell_blob,
        )
        out = _subprocess_blob_root(cwd=cwd, env=env)
        assert Path(out).resolve() == Path(shell_blob).resolve()


def test_blob_root_from_dotenv_when_shell_unset() -> None:
    """When BLOB_ROOT is only in cwd .env, Settings picks it up."""
    with tempfile.TemporaryDirectory() as tmp:
        cwd = Path(tmp)
        dotenv_blob = str(cwd / "only_dotenv")
        (cwd / ".env").write_text(
            f"SCIENCE_GRAPHRAG_BLOB_ROOT={dotenv_blob}\n"
            "SCIENCE_GRAPHRAG_ARTIFACT_ROOT=/artifacts_dotenv\n",
            encoding="utf-8",
        )
        env = _minimal_env(SCIENCE_GRAPHRAG_SKIP_HOST_DOTENV="0")
        out = _subprocess_blob_root(cwd=cwd, env=env)
        assert Path(out).resolve() == Path(dotenv_blob).resolve()


def test_blob_root_shell_export_with_skip_host_dotenv() -> None:
    """Shell BLOB_ROOT still wins with SCIENCE_GRAPHRAG_SKIP_HOST_DOTENV=1."""
    with tempfile.TemporaryDirectory() as tmp:
        cwd = Path(tmp)
        (cwd / ".env").write_text(
            "SCIENCE_GRAPHRAG_BLOB_ROOT=/from_dotenv_file\n"
            "SCIENCE_GRAPHRAG_ARTIFACT_ROOT=/artifacts_dotenv\n",
            encoding="utf-8",
        )
        shell_blob = str(cwd / "from_shell_skip")
        env = _minimal_env(
            SCIENCE_GRAPHRAG_SKIP_HOST_DOTENV="1",
            SCIENCE_GRAPHRAG_BLOB_ROOT=shell_blob,
        )
        out = _subprocess_blob_root(cwd=cwd, env=env)
        assert Path(out).resolve() == Path(shell_blob).resolve()
