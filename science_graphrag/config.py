from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="SCIENCE_GRAPHRAG_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    blob_root: Path = Field(default=Path("./data/blobs"))
    database_url: str = Field(
        default="postgresql+psycopg://science:science@localhost:5432/science_graphrag",
    )
    neo4j_uri: str = Field(default="bolt://localhost:7687")
    neo4j_user: str = Field(default="neo4j")
    neo4j_password: str = Field(default="sciencegraphrag")
    qdrant_url: str = Field(default="http://localhost:6333")
    qdrant_collection: str = Field(default="chunks")
    openalex_mailto: str = Field(default="dev@localhost")
    embedding_model: str | None = Field(
        default=None,
        description="If set, use sentence-transformers; else deterministic hash vectors.",
    )
    chunk_size: int = Field(default=512)
    chunk_overlap: int = Field(default=64)


def get_settings() -> Settings:
    return Settings()
