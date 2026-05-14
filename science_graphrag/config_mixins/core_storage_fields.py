"""Core blob/S3/DB/Neo4j/Qdrant/Redis field group for :class:`science_graphrag.config.Settings`."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class CoreStorageFields(BaseModel):
    """Composable storage + primary datastore fields (env names unchanged)."""

    model_config = ConfigDict(extra="ignore")

    blob_root: Path = Field(default=Path("./data/blobs"))
    artifact_root: Path = Field(default=Path("./data/artifacts"))
    s3_endpoint_url: str | None = Field(
        default=None,
        description="S3 API endpoint (e.g. http://localhost:19000 for MinIO).",
    )
    s3_access_key_id: str = Field(
        description="Required. S3/MinIO access key (SCIENCE_GRAPHRAG_S3_ACCESS_KEY_ID).",
    )
    s3_secret_access_key: str = Field(
        description="Required. S3/MinIO secret key (SCIENCE_GRAPHRAG_S3_SECRET_ACCESS_KEY).",
    )
    s3_bucket: str = Field(
        default="science-raw", description="Bucket for ingest queue + raw sha blobs."
    )
    s3_use_ssl: bool = Field(
        default=True,
        description="Set false for plain-http MinIO in dev.",
    )
    s3_addressing_style: Literal["path", "virtual"] = Field(
        default="path",
        description="MinIO typically needs path-style addressing.",
    )
    s3_artifact_key_prefix: str = Field(
        default="science-artifacts",
        description=(
            "Object key prefix inside s3_bucket for ingest artifacts (article.md, normalized.md, "
            "diagnostics). Same bucket as Phase 1 raw/queue; distinct prefix per roadmap §7.2."
        ),
    )
    s3_benchmark_runs_key_prefix: str = Field(
        default="science-benchmarks",
        description="Object key prefix inside s3_bucket for UI benchmark run full.json payloads.",
    )
    s3_diagnostics_key_prefix: str = Field(
        default="science-diagnostics",
        description="Object key prefix for OD/chat-agent diagnostic dumps (CLI scripts).",
    )
    object_storage_diagnostics_retention_days: int = Field(
        default=30,
        ge=0,
        description=(
            "Phase 4: optional hint (object tag/metadata) for diagnostic S3 objects; "
            "GC scripts may use this with LastModified. 0 = omit hint tag."
        ),
    )
    object_storage_benchmark_full_retention_days: int = Field(
        default=90,
        ge=0,
        description=("Phase 4: optional hint for benchmark full.json in S3; 0 = omit hint tag."),
    )
    database_url: str = Field(
        default="postgresql+psycopg://science:science@localhost:15432/science_graphrag",
    )
    neo4j_uri: str = Field(default="bolt://localhost:17687")
    neo4j_user: str = Field(default="neo4j")
    neo4j_password: str = Field(default="sciencegraphrag")
    qdrant_url: str = Field(default="http://localhost:16333")
    redis_url: str = Field(default="redis://localhost:6379/0")
    qdrant_collection: str = Field(default="chunks")


__all__ = ["CoreStorageFields"]
