import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Unprefixed keys (MAIN_LLM_*, PHOENIX_*, etc.) must be visible to os.getenv for merge validators.
load_dotenv()


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="SCIENCE_GRAPHRAG_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    blob_root: Path = Field(default=Path("./data/blobs"))
    artifact_root: Path = Field(default=Path("./data/artifacts"))
    database_url: str = Field(
        default="postgresql+psycopg://science:science@localhost:15432/science_graphrag",
    )
    neo4j_uri: str = Field(default="bolt://localhost:17687")
    neo4j_user: str = Field(default="neo4j")
    neo4j_password: str = Field(default="sciencegraphrag")
    qdrant_url: str = Field(default="http://localhost:16333")
    qdrant_collection: str = Field(default="chunks")
    openalex_mailto: str = Field(default="dev@localhost")
    use_vl_for_pdf: bool = Field(default=True)
    vl_api_key: str | None = Field(default=None)
    vl_base_url: str = Field(default="https://openrouter.ai/api/v1")
    vl_model: str = Field(default="qwen/qwen2.5-vl-72b-instruct")
    vl_max_pages: int = Field(default=16)
    vl_dpi: int = Field(default=144)
    embedding_model: str | None = Field(
        default=None,
        description="If set, use sentence-transformers; else deterministic hash vectors.",
    )
    chunk_size: int = Field(default=512)
    chunk_overlap: int = Field(default=64)

    @model_validator(mode="before")
    @classmethod
    def merge_osint_gr_compatible_env(cls, data: Any) -> Any:
        """
        Reuse osint-gr-style env without SCIENCE_GRAPHRAG_ prefix when explicit
        SCIENCE_GRAPHRAG_* keys are absent.
        """
        if not isinstance(data, dict):
            return data

        if not data.get("vl_api_key"):
            key = os.getenv("MAIN_LLM_API_KEY") or os.getenv("API_KEY")
            if key:
                data["vl_api_key"] = key

        if os.getenv("SCIENCE_GRAPHRAG_VL_BASE_URL") is None and os.getenv("MAIN_LLM_BASE_URL"):
            data["vl_base_url"] = os.environ["MAIN_LLM_BASE_URL"].strip().rstrip("/")

        if os.getenv("SCIENCE_GRAPHRAG_VL_MODEL") is None and os.getenv("MAIN_LLM_MODEL"):
            main_model = os.environ["MAIN_LLM_MODEL"].strip()
            if "vl" in main_model.lower() or "vision" in main_model.lower():
                data["vl_model"] = main_model

        if os.getenv("SCIENCE_GRAPHRAG_USE_VL_FOR_PDF") is None and os.getenv("USE_VL_FOR_PDF") is not None:
            data["use_vl_for_pdf"] = os.getenv("USE_VL_FOR_PDF", "true").lower() in (
                "1",
                "true",
                "yes",
                "on",
            )

        return data


def get_settings() -> Settings:
    return Settings()
