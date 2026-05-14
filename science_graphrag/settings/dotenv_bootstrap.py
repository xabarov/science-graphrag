"""Load `.env` before ``Settings`` with Docker / skip-host-dotenv aware precedence."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import dotenv_values, load_dotenv

# Unprefixed keys used by third-party tooling (e.g. PHOENIX_*) may still be read via os.getenv
# outside Settings. For SCIENCE_GRAPHRAG_* fields, pydantic-settings loads `.env` before process env.
# override=True: a shell export of SCIENCE_GRAPHRAG_EXTRACTION_LLM_API_KEY="" (empty) must not
# block values from `.env`.
# Inside Docker, Compose already injects SCIENCE_GRAPHRAG_* (Neo4j/Qdrant hosts); do not let
# load_dotenv clobber them with host-oriented localhost values from a mounted `.env`.
# blob_root / artifact_root are runtime-overridable: an operator or agent may set them
# via shell export for a single ingest run (e.g. SCIENCE_GRAPHRAG_BLOB_ROOT=./blobs_merged).
# load_dotenv(override=True) below would clobber those shell exports; save them first.
_RUNTIME_PATH_VARS = ("SCIENCE_GRAPHRAG_BLOB_ROOT", "SCIENCE_GRAPHRAG_ARTIFACT_ROOT")
_saved_runtime_paths = {k: os.environ[k] for k in _RUNTIME_PATH_VARS if k in os.environ}

_skip_host_dotenv = (
    Path("/.dockerenv").is_file() or os.getenv("SCIENCE_GRAPHRAG_SKIP_HOST_DOTENV") == "1"
)
if _skip_host_dotenv:
    # Load `.env` without clobbering Compose-injected service URLs.
    load_dotenv(override=False)
    # Separately ensure canonical LLM/VL credential vars from `.env` are visible when the shell
    # exported them empty (override=False would otherwise leave os.environ blocking dotenv).
    _api_key_vars = (
        "SCIENCE_GRAPHRAG_API_KEY",
        "SCIENCE_GRAPHRAG_EXTRACTION_LLM_API_KEY",
        "SCIENCE_GRAPHRAG_EXTRACTION_LLM_BASE_URL",
        "SCIENCE_GRAPHRAG_EXTRACTION_LLM_MODEL",
        "SCIENCE_GRAPHRAG_CHAT_LLM_MODEL",
        "SCIENCE_GRAPHRAG_VL_API_KEY",
        "SCIENCE_GRAPHRAG_VL_BASE_URL",
        "SCIENCE_GRAPHRAG_VL_MODEL",
        "SCIENCE_GRAPHRAG_USE_VL_FOR_PDF",
        "SCIENCE_GRAPHRAG_OPENROUTER_EMBEDDING_MODEL",
        "SCIENCE_GRAPHRAG_BENCHMARK_TEACHER_LLM_API_KEY",
        "SCIENCE_GRAPHRAG_BENCHMARK_TEACHER_LLM_BASE_URL",
        "SCIENCE_GRAPHRAG_BENCHMARK_TEACHER_LLM_MODEL",
    )
    _env_file_vals = dotenv_values()
    for _k in _api_key_vars:
        if _k in _env_file_vals and not os.environ.get(_k):
            os.environ[_k] = _env_file_vals[_k]
    del _api_key_vars, _env_file_vals, _k
else:
    load_dotenv(override=True)
    # Restore runtime-overridable paths that load_dotenv(override=True) may have clobbered.
    for _k, _v in _saved_runtime_paths.items():
        os.environ[_k] = _v

del _saved_runtime_paths

__all__: list[str] = []
