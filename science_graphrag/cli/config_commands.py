"""Config and preflight CLI commands."""

from __future__ import annotations

import os
from typing import Any

import typer

from science_graphrag.config import Settings, get_settings
from science_graphrag.utils.project_logging import (
    describe_dramatiq_log_level_env,
    describe_http_log_level_env,
    describe_ingest_log_level_env,
    describe_log_format_env,
)


def _mask_url(url: str) -> str:
    u = str(url or "").strip()
    if "@" in u and "://" in u:
        head, tail = u.split("://", 1)
        if "@" in tail:
            creds, host = tail.rsplit("@", 1)
            if creds:
                return f"{head}://***@{host}"
    return u


def register(app: typer.Typer) -> None:
    """Register config-check command."""

    @app.command("config-check")
    def config_check_cmd(
        strict: bool = typer.Option(
            True,
            "--strict/--no-strict",
            help="Exit 1 if no LLM API key is configured.",
        ),
        embeddings_preflight: bool = typer.Option(
            False,
            "--embeddings-preflight/--no-embeddings-preflight",
            help="After printing settings, call embeddings once.",
        ),
        object_storage_preflight: bool = typer.Option(
            True,
            "--object-storage-preflight/--no-object-storage-preflight",
            help="Verify S3/MinIO bucket access (head + list).",
        ),
    ) -> None:
        """Print non-secret diagnostics for Settings (operator pre-flight)."""
        s: Settings = get_settings()

        def _line(label: str, value: str) -> None:
            typer.echo(f"[config-check] {label:40} {value}")

        canon_ok = bool((s.api_key or "").strip())
        ex_ok = bool(s.extraction_llm_api_key)
        vl_explicit = bool((s.vl_api_key or "").strip())
        vl_effective = bool(s.resolved_vl_api_key)
        _line("SCIENCE_GRAPHRAG_API_KEY", "SET" if canon_ok else "UNSET")
        _line("extraction_llm_api_key", "SET" if ex_ok else "UNSET")
        _line("vl_api_key (explicit env)", "SET" if vl_explicit else "UNSET")
        _line("vl_api_key (effective for VL)", "SET" if vl_effective else "UNSET")
        if s.openrouter_embedding_model:
            _line(
                "embeddings channel",
                f"openrouter (model={s.openrouter_embedding_model}, dim={s.openrouter_embedding_dim})",
            )
        elif s.embedding_model:
            _line("embeddings channel", f"local_sentence_transformers ({s.embedding_model})")
        else:
            _line("embeddings channel", "hash_fallback (no embedding_model / openrouter_embedding_model)")
        _line("database_url", _mask_url(s.database_url))
        _line("neo4j_uri", str(s.neo4j_uri))
        _line("qdrant_url", str(s.qdrant_url))
        _line("redis_url", _mask_url(s.redis_url))
        _line("agent_session_memory_backend", str(s.agent_session_memory_backend))
        skip = os.getenv("SCIENCE_GRAPHRAG_SKIP_HOST_DOTENV", "")
        _line("SCIENCE_GRAPHRAG_SKIP_HOST_DOTENV", skip or "(unset)")
        _line("SCIENCE_GRAPHRAG_LOG_LEVEL", os.getenv("SCIENCE_GRAPHRAG_LOG_LEVEL", "INFO"))
        _line("SCIENCE_GRAPHRAG_LOG_LEVEL_INGEST", describe_ingest_log_level_env())
        _line("SCIENCE_GRAPHRAG_HTTP_LOG_LEVEL", describe_http_log_level_env())
        _line("SCIENCE_GRAPHRAG_DRAMATIQ_LOG_LEVEL", describe_dramatiq_log_level_env())
        _line("SCIENCE_GRAPHRAG_LOG_FORMAT", describe_log_format_env())
        _line("SCIENCE_GRAPHRAG_METRICS_ENABLED", str(bool(s.metrics_enabled)))
        _line("extraction_llm_enabled", str(bool(s.extraction_llm_enabled)))
        br: Any = s.blob_root
        try:
            exists = br.exists()
        except OSError:
            exists = False
        _line("blob_root", f"{br} (exists={exists})")
        _line(
            "s3_endpoint_url",
            (s.s3_endpoint_url or "").strip() or "(default virtual-hosted AWS / moto)",
        )
        _line("s3_bucket", (s.s3_bucket or "").strip())
        _line("s3_access_key_id", "SET" if (s.s3_access_key_id or "").strip() else "UNSET")
        _line("s3_secret_access_key", "SET" if (s.s3_secret_access_key or "").strip() else "UNSET")
        _line("s3_use_ssl", str(bool(s.s3_use_ssl)))
        if strict and not ex_ok:
            typer.echo(
                "[config-check] FAILED: no LLM API key (set SCIENCE_GRAPHRAG_API_KEY or "
                "SCIENCE_GRAPHRAG_EXTRACTION_LLM_API_KEY)",
                err=True,
            )
            raise typer.Exit(code=1)
        if embeddings_preflight:
            from science_graphrag.embeddings.preflight import probe_embeddings

            try:
                probe_embeddings(s)
                typer.echo("[config-check] embeddings preflight: OK")
            except Exception as exc:  # noqa: BLE001
                typer.echo(f"[config-check] embeddings preflight: FAILED ({exc!s})", err=True)
                raise typer.Exit(code=1) from exc
        if object_storage_preflight:
            from science_graphrag.storage.object_storage_preflight import probe_object_storage

            try:
                probe_object_storage(s)
                typer.echo("[config-check] object storage preflight: OK")
            except Exception as exc:  # noqa: BLE001
                typer.echo(f"[config-check] object storage preflight: FAILED ({exc!s})", err=True)
                raise typer.Exit(code=1) from exc
