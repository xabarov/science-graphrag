"""API routes for runtime settings and LLM connection checks."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends

from science_graphrag.api.auth import require_settings_access
from science_graphrag.api.settings_models import (
    SettingsSchemaResponse,
    SettingsSnapshotResponse,
    TestLlmConnectionRequest,
    UpdateIngestionSettingsRequest,
    UpdateLlmSettingsRequest,
)
from science_graphrag.config import get_settings
from science_graphrag.settings.service import LlmTestDraft, SettingsService

router = APIRouter(prefix="/settings", tags=["settings"])

_SETTINGS_SERVICE = SettingsService(repo_root=Path(__file__).resolve().parents[2])


@router.get("/schema", response_model=SettingsSchemaResponse)
def get_settings_schema(_: str = Depends(require_settings_access)) -> SettingsSchemaResponse:
    return SettingsSchemaResponse.model_validate(_SETTINGS_SERVICE.get_schema())


@router.get("", response_model=SettingsSnapshotResponse)
def get_settings_snapshot(_: str = Depends(require_settings_access)) -> SettingsSnapshotResponse:
    snapshot = _SETTINGS_SERVICE.get_snapshot(get_settings())
    return SettingsSnapshotResponse(
        sections=snapshot.sections,
        llm=snapshot.llm,
        ingestion=snapshot.ingestion,
        diagnostics=snapshot.diagnostics,
        security=snapshot.security,
    )


@router.patch("/llm", response_model=SettingsSnapshotResponse)
def patch_llm_settings(
    body: UpdateLlmSettingsRequest,
    actor: str = Depends(require_settings_access),
) -> SettingsSnapshotResponse:
    snapshot = _SETTINGS_SERVICE.update_llm_settings(
        base_settings=get_settings(),
        base_url=str(body.base_url),
        model=body.model,
        temperature=body.temperature,
        timeout_seconds=body.timeout_seconds,
        actor=actor,
        api_key=body.api_key,
    )
    return SettingsSnapshotResponse(
        sections=snapshot.sections,
        llm=snapshot.llm,
        ingestion=snapshot.ingestion,
        diagnostics=snapshot.diagnostics,
        security=snapshot.security,
    )


@router.patch("/ingestion", response_model=SettingsSnapshotResponse)
def patch_ingestion_settings(
    body: UpdateIngestionSettingsRequest,
    actor: str = Depends(require_settings_access),
) -> SettingsSnapshotResponse:
    snapshot = _SETTINGS_SERVICE.update_ingestion_settings(
        base_settings=get_settings(),
        max_file_size_mb=body.max_file_size_mb,
        actor=actor,
    )
    return SettingsSnapshotResponse(
        sections=snapshot.sections,
        llm=snapshot.llm,
        ingestion=snapshot.ingestion,
        diagnostics=snapshot.diagnostics,
        security=snapshot.security,
    )


@router.delete("/llm/secret", response_model=SettingsSnapshotResponse)
def delete_llm_secret(actor: str = Depends(require_settings_access)) -> SettingsSnapshotResponse:
    del actor
    snapshot = _SETTINGS_SERVICE.delete_llm_secret(base_settings=get_settings())
    return SettingsSnapshotResponse(
        sections=snapshot.sections,
        llm=snapshot.llm,
        ingestion=snapshot.ingestion,
        diagnostics=snapshot.diagnostics,
        security=snapshot.security,
    )


@router.post("/llm/test")
def post_llm_test(
    body: TestLlmConnectionRequest,
    actor: str = Depends(require_settings_access),
) -> dict:
    payload = body.model_dump(mode="json")
    return _SETTINGS_SERVICE.test_llm_connection(
        base_settings=get_settings(),
        actor=actor,
        draft=LlmTestDraft.model_validate(payload),
    )
