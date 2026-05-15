"""API routes for runtime settings and LLM connection checks."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from science_graphrag.api.auth import require_settings_access
from science_graphrag.api.settings_models import (
    SettingsSchemaResponse,
    SettingsSnapshotResponse,
    TestLlmConnectionRequest,
    UpdateAgentToolsSettingsRequest,
    UpdateBenchmarkSettingsRequest,
    UpdateGeneralSettingsRequest,
    UpdateIngestionSettingsRequest,
    UpdateLlmSettingsRequest,
    UpdateStorageSettingsRequest,
)
from science_graphrag.config import get_settings
from science_graphrag.settings.service import LlmTestDraft, SettingsService, SettingsSnapshot

router = APIRouter(prefix="/settings", tags=["settings"])

_SETTINGS_SERVICE = SettingsService(repo_root=Path(__file__).resolve().parents[2])


def _settings_snapshot_response(snapshot: SettingsSnapshot) -> SettingsSnapshotResponse:
    """Map service snapshot dataclass to API response (single place for new snapshot fields)."""
    return SettingsSnapshotResponse(
        sections=snapshot.sections,
        llm=snapshot.llm,
        ingestion=snapshot.ingestion,
        general=snapshot.general,
        storage=snapshot.storage,
        benchmark=snapshot.benchmark,
        diagnostics=snapshot.diagnostics,
        security=snapshot.security,
        work_dedup=snapshot.work_dedup,
        agent_tools=snapshot.agent_tools,
    )


@router.get("/schema", response_model=SettingsSchemaResponse)
def get_settings_schema(_: str = Depends(require_settings_access)) -> SettingsSchemaResponse:
    return SettingsSchemaResponse.model_validate(_SETTINGS_SERVICE.get_schema())


@router.get("", response_model=SettingsSnapshotResponse)
def get_settings_snapshot(_: str = Depends(require_settings_access)) -> SettingsSnapshotResponse:
    snapshot = _SETTINGS_SERVICE.get_snapshot(get_settings())
    return _settings_snapshot_response(snapshot)


@router.patch("/llm", response_model=SettingsSnapshotResponse)
def patch_llm_settings(
    body: UpdateLlmSettingsRequest,
    actor: str = Depends(require_settings_access),
) -> SettingsSnapshotResponse:
    raw = body.model_dump(exclude_unset=True)
    kwargs: dict[str, Any] = {
        "base_settings": get_settings(),
        "base_url": str(body.base_url),
        "model": body.model,
        "temperature": body.temperature,
        "timeout_seconds": body.timeout_seconds,
        "actor": actor,
        "api_key": body.api_key,
    }
    if "vl_model" in raw:
        kwargs["vl_model"] = body.vl_model
    if "vl_base_url" in raw:
        kwargs["vl_base_url"] = body.vl_base_url
    if "chat_model" in raw:
        kwargs["chat_model"] = body.chat_model
    if "vision_api_key" in raw:
        kwargs["vision_api_key"] = body.vision_api_key
    if body.runtime_overrides is not None:
        adv = body.runtime_overrides.model_dump(exclude_unset=True, exclude_none=True)
        if adv:
            kwargs["advanced_patch"] = adv
    try:
        snapshot = _SETTINGS_SERVICE.update_llm_settings(**kwargs)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return _settings_snapshot_response(snapshot)


@router.patch("/ingestion", response_model=SettingsSnapshotResponse)
def patch_ingestion_settings(
    body: UpdateIngestionSettingsRequest,
    actor: str = Depends(require_settings_access),
) -> SettingsSnapshotResponse:
    snapshot = _SETTINGS_SERVICE.update_ingestion_settings(
        get_settings(),
        body.max_file_size_mb,
        body.claims_extraction_enabled,
        actor,
    )
    return _settings_snapshot_response(snapshot)


@router.patch("/general", response_model=SettingsSnapshotResponse)
def patch_general_settings(
    body: UpdateGeneralSettingsRequest,
    actor: str = Depends(require_settings_access),
) -> SettingsSnapshotResponse:
    try:
        snapshot = _SETTINGS_SERVICE.update_general_settings(
            base_settings=get_settings(),
            openalex_mailto=body.openalex_mailto,
            actor=actor,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return _settings_snapshot_response(snapshot)


@router.patch("/storage", response_model=SettingsSnapshotResponse)
def patch_storage_settings(
    body: UpdateStorageSettingsRequest,
    actor: str = Depends(require_settings_access),
) -> SettingsSnapshotResponse:
    raw = body.model_dump(exclude_unset=True)
    try:
        snapshot = _SETTINGS_SERVICE.update_storage_settings(
            base_settings=get_settings(),
            actor=actor,
            updates=raw,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return _settings_snapshot_response(snapshot)


@router.patch("/agent_tools", response_model=SettingsSnapshotResponse)
def patch_agent_tools_settings(
    body: UpdateAgentToolsSettingsRequest,
    actor: str = Depends(require_settings_access),
) -> SettingsSnapshotResponse:
    raw = body.model_dump(exclude_unset=True, mode="python")
    try:
        snapshot = _SETTINGS_SERVICE.update_agent_tools_settings(
            base_settings=get_settings(),
            actor=actor,
            patch=raw,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return _settings_snapshot_response(snapshot)


@router.patch("/benchmark", response_model=SettingsSnapshotResponse)
def patch_benchmark_settings(
    body: UpdateBenchmarkSettingsRequest,
    actor: str = Depends(require_settings_access),
) -> SettingsSnapshotResponse:
    by_family: dict[str, dict[str, Any]] = {}
    for fam_key, prefs in body.by_family.items():
        by_family[fam_key] = prefs.model_dump(exclude_unset=True)
    try:
        snapshot = _SETTINGS_SERVICE.update_benchmark_settings(
            base_settings=get_settings(),
            actor=actor,
            by_family=by_family,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return _settings_snapshot_response(snapshot)


@router.delete("/llm/secret", response_model=SettingsSnapshotResponse)
def delete_llm_secret(
    _actor: str = Depends(require_settings_access),
) -> SettingsSnapshotResponse:
    snapshot = _SETTINGS_SERVICE.delete_llm_secret(base_settings=get_settings())
    return _settings_snapshot_response(snapshot)


@router.delete("/llm/vision-secret", response_model=SettingsSnapshotResponse)
def delete_llm_vision_secret(
    _actor: str = Depends(require_settings_access),
) -> SettingsSnapshotResponse:
    snapshot = _SETTINGS_SERVICE.delete_llm_vision_secret(base_settings=get_settings())
    return _settings_snapshot_response(snapshot)


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
