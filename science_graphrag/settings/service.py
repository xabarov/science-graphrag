"""Runtime settings service with secret-aware LLM configuration."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from pathlib import Path
from threading import Lock
from typing import TYPE_CHECKING, Any

import httpx

from science_graphrag.settings.agent_tools_mcp import normalize_mcp_server_denylist
from science_graphrag.settings.benchmark_defaults import (
    merge_persisted_benchmark_family,
    normalize_benchmark_family_key,
    validate_merged_benchmark_family_prefs,
)
from science_graphrag.settings.llm_advanced_fields import (
    LLM_ADVANCED_RUNTIME_KEYS,
    clamp_advanced_field,
    validate_merged_runtime_settings,
)
from science_graphrag.settings.llm_task_persisted import (
    apply_tasks_to_llm_dict,
    get_normalized_llm_tasks,
    merge_partial_tasks_patch,
    strip_legacy_llm_task_flat_keys,
)
from science_graphrag.settings.llm_test_probe_service import (
    LlmTestDraft,
    run_llm_connection_probe,
    run_settings_llm_test_probe,
)
from science_graphrag.settings.repository import SettingsRepository
from science_graphrag.settings.runtime_llm_bootstrap import (
    ensure_llm_runtime_bootstrap_from_env,
    llm_bootstrap_applied,
)
from science_graphrag.settings.runtime_overlay import build_non_secret_overrides
from science_graphrag.settings.schema import build_settings_schema
from science_graphrag.settings.secret_store_keys import (
    LLM_API_KEY,
    LLM_CHAT_API_KEY,
    LLM_EMBEDDINGS_API_KEY,
    LLM_VISION_API_KEY,
    SEMANTIC_SCHOLAR_API_KEY,
)
from science_graphrag.settings.secrets import SecretStore
from science_graphrag.settings.service_runtime_merge import (
    merged_runtime_candidate_from_persisted_payload,
    validate_settings_model_roundtrip,
)
from science_graphrag.settings.snapshot_materialize import materialize_settings_snapshot
from science_graphrag.settings.snapshot_model import SettingsSnapshot
from science_graphrag.settings.storage_runtime import (
    _SK_DATABASE_URL,
    _SK_NEO4J_PASSWORD,
    _SK_S3_SECRET,
    apply_storage_json_updates,
)

if TYPE_CHECKING:
    from science_graphrag.config import Settings

_AGENT_TOOLS_PATCH_ALLOWLIST: frozenset[str] = frozenset(
    {
        "agent_supervisor_max_rounds",
        "external_research_default_enabled",
        "external_research_sources",
        "pdf_reading_mode",
        "agent_pdf_read_backend_mode",
        "agent_unpaywall_oa_tool_enabled",
        "agent_external_http_timeout_seconds",
        "agent_external_max_calls_per_turn",
        "agent_external_max_source_cards",
        "agent_pdf_read_tool_enabled",
        "agent_pdf_read_max_bytes",
        "agent_pdf_read_max_pages",
        "agent_pdf_read_cache_ttl_seconds",
        "agent_pdf_read_cache_max_entries",
        "agent_pdf_read_durable_cache_enabled",
        "agent_mcp_request_timeout_seconds",
        "agent_mcp_server_denylist",
        "agent_mcp_http_base_url",
    }
)


_UNSET_CHAT_MODEL = object()
_UNSET_VISION_API_KEY = object()
_UNSET_CHAT_API_KEY = object()
_UNSET_EMBEDDINGS_API_KEY = object()
_UNSET_EXTRACTION_API_KEY = object()

_LOGGER = logging.getLogger(__name__)


def _now_iso() -> str:
    return datetime.now(tz=UTC).isoformat()


def _runtime_settings_root(repo_root: Path) -> Path:
    return repo_root / "data" / "settings"


class SettingsService:
    """Read, write, and test runtime settings persisted outside env files."""

    def __init__(
        self,
        *,
        repo_root: Path,
        repository: SettingsRepository | None = None,
        secret_store: SecretStore | None = None,
    ) -> None:
        self._repo_root = repo_root
        root_dir = _runtime_settings_root(repo_root)
        self._repository = repository or SettingsRepository(root_dir)
        self._secret_store = secret_store or SecretStore(root_dir)
        self._lock = Lock()

    def build_runtime_settings(self, base_settings: Settings) -> Settings:
        """Overlay persisted runtime overrides onto env-derived settings."""
        ensure_llm_runtime_bootstrap_from_env(self, base_settings)
        overrides = self.get_snapshot(base_settings).non_secret_overrides
        payload = dict(overrides)
        persisted = self._repository.load()
        boot = llm_bootstrap_applied(persisted)
        api_key = self._secret_store.get_secret(LLM_API_KEY)
        if api_key:
            payload["extraction_llm_api_key"] = api_key
        elif boot:
            payload["extraction_llm_api_key"] = ""
        chat_key = self._secret_store.get_secret(LLM_CHAT_API_KEY)
        if chat_key:
            payload["chat_llm_api_key"] = chat_key.strip()
        elif boot:
            payload["chat_llm_api_key"] = ""
        emb_key = self._secret_store.get_secret(LLM_EMBEDDINGS_API_KEY)
        if emb_key:
            payload["embeddings_api_key"] = emb_key.strip()
        elif boot:
            payload["embeddings_api_key"] = ""
        vision_key = self._secret_store.get_secret(LLM_VISION_API_KEY)
        if vision_key:
            payload["vl_api_key"] = vision_key.strip()
        elif boot:
            payload["vl_api_key"] = ""
        s2_key = self._secret_store.get_secret(SEMANTIC_SCHOLAR_API_KEY)
        if s2_key:
            payload["semantic_scholar_api_key"] = s2_key.strip()
        if not payload:
            return base_settings
        return base_settings.model_copy(update=payload)

    def get_snapshot(self, base_settings: Settings) -> SettingsSnapshot:
        """Return a masked UI-facing snapshot of runtime settings."""
        ensure_llm_runtime_bootstrap_from_env(self, base_settings)
        persisted = self._repository.load()
        return materialize_settings_snapshot(
            base_settings=base_settings,
            persisted=persisted,
            secret_store=self._secret_store,
        )

    def get_schema(self) -> dict[str, Any]:
        """Return a UI-friendly schema so future sections can extend the page safely."""
        return build_settings_schema()

    def update_llm_settings(  # pylint: disable=too-many-arguments,too-many-positional-arguments,too-many-locals,too-many-branches
        self,
        *,
        base_settings: Settings,
        actor: str,
        tasks_patch: dict[str, dict[str, Any]] | None = None,
        base_url: str | None = None,
        model: str | None = None,
        temperature: float | None = None,
        timeout_seconds: float | None = None,
        api_key: Any = _UNSET_EXTRACTION_API_KEY,
        chat_model: Any = _UNSET_CHAT_MODEL,
        chat_base_url: Any = _UNSET_CHAT_MODEL,
        vl_model: Any = _UNSET_CHAT_MODEL,
        vl_base_url: Any = _UNSET_CHAT_MODEL,
        vision_api_key: Any = _UNSET_VISION_API_KEY,
        chat_api_key: Any = _UNSET_CHAT_API_KEY,
        embeddings_mode: Any = _UNSET_CHAT_MODEL,
        embeddings_model: Any = _UNSET_CHAT_MODEL,
        embeddings_api_key: Any = _UNSET_EMBEDDINGS_API_KEY,
        advanced_patch: dict[str, Any] | None = None,
    ) -> SettingsSnapshot:
        """Persist editable LLM task blocks and optional managed secrets."""

        with self._lock:
            payload = self._repository.load()
            llm = dict(payload.get("llm") or {})
            tasks_next = get_normalized_llm_tasks(llm, base_settings)

            legacy_blocks: dict[str, dict[str, Any]] = {}
            ext_legacy: dict[str, Any] = {}
            if base_url is not None:
                ext_legacy["base_url"] = str(base_url).strip().rstrip("/")
            if model is not None:
                ext_legacy["model"] = str(model).strip()
            if temperature is not None:
                ext_legacy["temperature"] = float(temperature)
            if timeout_seconds is not None:
                ext_legacy["timeout_seconds"] = float(timeout_seconds)
            if ext_legacy:
                legacy_blocks["extraction"] = ext_legacy

            chat_legacy: dict[str, Any] = {}
            if chat_model is not _UNSET_CHAT_MODEL:
                chat_legacy["model"] = str(chat_model or "").strip()
            if chat_base_url is not _UNSET_CHAT_MODEL:
                chat_legacy["base_url"] = str(chat_base_url or "").strip().rstrip("/")
            if chat_legacy:
                legacy_blocks["chat"] = chat_legacy

            vision_legacy: dict[str, Any] = {}
            if vl_model is not _UNSET_CHAT_MODEL:
                vision_legacy["model"] = str(vl_model or "").strip()
            if vl_base_url is not _UNSET_CHAT_MODEL:
                vision_legacy["base_url"] = str(vl_base_url or "").strip().rstrip("/")
            if vision_legacy:
                legacy_blocks["vision"] = vision_legacy

            emb_legacy: dict[str, Any] = {}
            if embeddings_mode is not _UNSET_CHAT_MODEL:
                em = str(embeddings_mode or "").strip().lower()
                if em == "local":
                    emb_legacy["mode"] = "local"
                elif em == "openrouter":
                    emb_legacy["mode"] = "http"
            if embeddings_model is not _UNSET_CHAT_MODEL:
                emd = str(embeddings_model or "").strip()
                if emd:
                    emb_legacy["model"] = emd
            if emb_legacy:
                legacy_blocks["embeddings"] = emb_legacy

            if legacy_blocks:
                tasks_next = merge_partial_tasks_patch(tasks_next, legacy_blocks)
            if tasks_patch:
                tasks_next = merge_partial_tasks_patch(tasks_next, tasks_patch)

            meta = dict(llm.get("_meta") or {})
            meta["last_updated_at"] = _now_iso()
            meta["last_updated_by"] = actor
            llm["_meta"] = meta
            apply_tasks_to_llm_dict(llm, tasks_next)
            strip_legacy_llm_task_flat_keys(llm)
            llm["enabled"] = True

            if advanced_patch:
                for key, raw in advanced_patch.items():
                    if key in LLM_ADVANCED_RUNTIME_KEYS:
                        llm[key] = clamp_advanced_field(key, raw, base_settings)
            ingestion_cfg = dict(payload.get("ingestion") or {})
            general_cfg = dict(payload.get("general") or {})
            storage_cfg = dict(payload.get("storage") or {})
            agent_tools_cfg = dict(payload.get("agent_tools") or {})
            merged_non_secret = build_non_secret_overrides(
                base_settings=base_settings,
                llm=llm,
                ingestion_cfg=ingestion_cfg,
                general_cfg=general_cfg,
                storage_cfg=storage_cfg,
                secret_store=self._secret_store,
                storage_secret_explicit=None,
                agent_tools=agent_tools_cfg,
            )
            validate_merged_runtime_settings(
                base_settings.model_copy(update=merged_non_secret),
            )
            payload["llm"] = llm
            self._repository.save(payload)
            if api_key is not _UNSET_EXTRACTION_API_KEY:
                if api_key is None:
                    self._secret_store.delete_secret(LLM_API_KEY)
                else:
                    self._secret_store.set_secret(LLM_API_KEY, str(api_key).strip())
            if vision_api_key is not _UNSET_VISION_API_KEY:
                raw_v = vision_api_key
                if raw_v is None:
                    self._secret_store.delete_secret(LLM_VISION_API_KEY)
                else:
                    stripped = str(raw_v).strip()
                    if stripped:
                        self._secret_store.set_secret(LLM_VISION_API_KEY, stripped)
                    else:
                        self._secret_store.delete_secret(LLM_VISION_API_KEY)
            if chat_api_key is not _UNSET_CHAT_API_KEY:
                raw_c = chat_api_key
                if raw_c is None:
                    self._secret_store.delete_secret(LLM_CHAT_API_KEY)
                else:
                    stripped = str(raw_c).strip()
                    if stripped:
                        self._secret_store.set_secret(LLM_CHAT_API_KEY, stripped)
                    else:
                        self._secret_store.delete_secret(LLM_CHAT_API_KEY)
            if embeddings_api_key is not _UNSET_EMBEDDINGS_API_KEY:
                raw_e = embeddings_api_key
                if raw_e is None:
                    self._secret_store.delete_secret(LLM_EMBEDDINGS_API_KEY)
                else:
                    stripped = str(raw_e).strip()
                    if stripped:
                        self._secret_store.set_secret(LLM_EMBEDDINGS_API_KEY, stripped)
                    else:
                        self._secret_store.delete_secret(LLM_EMBEDDINGS_API_KEY)
        return self.get_snapshot(base_settings)

    def reveal_llm_task_secret(self, *, task: str, actor: str, base_settings: Settings) -> str:
        """Return a raw vault secret for ``task`` (explicit operator reveal; audit logged)."""

        del base_settings  # Reserved for future tenant/workspace scoping.
        allowed = {"extraction", "chat", "vision", "embeddings"}
        if task not in allowed:
            raise ValueError(f"Unknown LLM task: {task}")
        key_map = {
            "extraction": LLM_API_KEY,
            "chat": LLM_CHAT_API_KEY,
            "vision": LLM_VISION_API_KEY,
            "embeddings": LLM_EMBEDDINGS_API_KEY,
        }
        secret = self._secret_store.get_secret(key_map[task])
        if not secret and task in {"chat", "vision", "embeddings"}:
            secret = self._secret_store.get_secret(LLM_API_KEY)
        _LOGGER.info("LLM secret revealed (explicit operator action) task=%s actor=%s", task, actor)
        return secret or ""

    def update_ingestion_settings(
        self,
        base_settings: Settings,
        max_file_size_mb: int,
        claims_extraction_enabled: bool,
        actor: str,
    ) -> SettingsSnapshot:
        """Persist workspace upload size limit (megabytes per file)."""
        bounded = max(1, min(2048, int(max_file_size_mb)))
        with self._lock:
            payload = self._repository.load()
            ingestion = dict(payload.get("ingestion") or {})
            ingestion.update(
                {
                    "max_file_size_mb": bounded,
                    "claims_extraction_enabled": bool(claims_extraction_enabled),
                    "_meta": {
                        "last_updated_at": _now_iso(),
                        "last_updated_by": actor,
                    },
                },
            )
            payload["ingestion"] = ingestion
            self._repository.save(payload)
        return self.get_snapshot(base_settings)

    def update_general_settings(
        self,
        *,
        base_settings: Settings,
        openalex_mailto: str,
        actor: str,
    ) -> SettingsSnapshot:
        """Persist OpenAlex polite-pool contact email (non-secret)."""

        mailto = str(openalex_mailto or "").strip()
        if "@" not in mailto or " " in mailto:
            raise ValueError("openalex_mailto must be a single email-like address")
        if len(mailto) > 320:
            raise ValueError("openalex_mailto is too long")

        with self._lock:
            payload = self._repository.load()
            general = dict(payload.get("general") or {})
            general["openalex_mailto"] = mailto
            general["_meta"] = {
                "last_updated_at": _now_iso(),
                "last_updated_by": actor,
            }
            payload["general"] = general
            merged_runtime_candidate_from_persisted_payload(
                base_settings=base_settings,
                payload=payload,
                secret_store=self._secret_store,
            )
            self._repository.save(payload)
        return self.get_snapshot(base_settings)

    def update_agent_tools_settings(
        self,
        *,
        base_settings: Settings,
        actor: str,
        patch: dict[str, Any],
    ) -> SettingsSnapshot:
        """Persist allowlisted agent runtime knobs (partial PATCH)."""
        filtered = {k: v for k, v in dict(patch or {}).items() if k in _AGENT_TOOLS_PATCH_ALLOWLIST}
        if not filtered:
            return self.get_snapshot(base_settings)

        with self._lock:
            payload = self._repository.load()
            at = {k: v for k, v in dict(payload.get("agent_tools") or {}).items() if k != "_meta"}

            if "agent_supervisor_max_rounds" in filtered:
                at["agent_supervisor_max_rounds"] = max(
                    2, min(32, int(filtered["agent_supervisor_max_rounds"]))
                )
            if "external_research_default_enabled" in filtered:
                at["external_research_default_enabled"] = bool(
                    filtered["external_research_default_enabled"]
                )
            if "external_research_sources" in filtered:
                inc = filtered["external_research_sources"]
                prev = dict(at.get("external_research_sources") or {})
                if isinstance(inc, dict):
                    for key in ("crossref", "arxiv", "unpaywall", "openalex", "semantic_scholar"):
                        if key in inc and isinstance(inc[key], bool):
                            prev[key] = bool(inc[key])
                    at["external_research_sources"] = prev
            if "pdf_reading_mode" in filtered:
                mode = filtered["pdf_reading_mode"]
                if mode in {"off", "ask", "auto_safe_oa"}:
                    at["pdf_reading_mode"] = mode
            if "agent_pdf_read_backend_mode" in filtered:
                bm = filtered["agent_pdf_read_backend_mode"]
                if bm in {"pypdf", "vl", "hybrid"}:
                    at["agent_pdf_read_backend_mode"] = bm
            if "agent_unpaywall_oa_tool_enabled" in filtered:
                at["agent_unpaywall_oa_tool_enabled"] = bool(
                    filtered["agent_unpaywall_oa_tool_enabled"]
                )
            if "agent_external_http_timeout_seconds" in filtered:
                at["agent_external_http_timeout_seconds"] = max(
                    5.0, min(120.0, float(filtered["agent_external_http_timeout_seconds"]))
                )
            if "agent_external_max_calls_per_turn" in filtered:
                at["agent_external_max_calls_per_turn"] = max(
                    1, min(32, int(filtered["agent_external_max_calls_per_turn"]))
                )
            if "agent_external_max_source_cards" in filtered:
                at["agent_external_max_source_cards"] = max(
                    4, min(128, int(filtered["agent_external_max_source_cards"]))
                )
            if "agent_pdf_read_tool_enabled" in filtered:
                at["agent_pdf_read_tool_enabled"] = bool(filtered["agent_pdf_read_tool_enabled"])
            if "agent_pdf_read_max_bytes" in filtered:
                at["agent_pdf_read_max_bytes"] = max(
                    100_000, min(100_000_000, int(filtered["agent_pdf_read_max_bytes"]))
                )
            if "agent_pdf_read_max_pages" in filtered:
                at["agent_pdf_read_max_pages"] = max(
                    1, min(500, int(filtered["agent_pdf_read_max_pages"]))
                )
            if "agent_pdf_read_cache_ttl_seconds" in filtered:
                at["agent_pdf_read_cache_ttl_seconds"] = max(
                    0, min(86_400, int(filtered["agent_pdf_read_cache_ttl_seconds"]))
                )
            if "agent_pdf_read_cache_max_entries" in filtered:
                at["agent_pdf_read_cache_max_entries"] = max(
                    16, min(10_000, int(filtered["agent_pdf_read_cache_max_entries"]))
                )
            if "agent_pdf_read_durable_cache_enabled" in filtered:
                at["agent_pdf_read_durable_cache_enabled"] = bool(
                    filtered["agent_pdf_read_durable_cache_enabled"]
                )
            if "agent_mcp_request_timeout_seconds" in filtered:
                at["agent_mcp_request_timeout_seconds"] = max(
                    1.0,
                    min(120.0, float(filtered["agent_mcp_request_timeout_seconds"])),
                )
            if "agent_mcp_server_denylist" in filtered:
                at["agent_mcp_server_denylist"] = normalize_mcp_server_denylist(
                    filtered["agent_mcp_server_denylist"]
                )
            if "agent_mcp_http_base_url" in filtered:
                raw_base = str(filtered["agent_mcp_http_base_url"] or "").strip()
                at["agent_mcp_http_base_url"] = raw_base.rstrip("/") if raw_base else ""

            at["_meta"] = {
                "last_updated_at": _now_iso(),
                "last_updated_by": actor,
            }
            payload["agent_tools"] = at
            candidate = merged_runtime_candidate_from_persisted_payload(
                base_settings=base_settings,
                payload=payload,
                secret_store=self._secret_store,
            )
            validate_settings_model_roundtrip(candidate)
            self._repository.save(payload)
        return self.get_snapshot(base_settings)

    def test_agent_tool_source(
        self,
        *,
        base_settings: Settings,
        actor: str,
        source_id: str,
    ) -> dict[str, Any]:
        """Run a short operator smoke for one external source and persist diagnostics."""
        del actor  # Reserved for audit expansion.
        sid = str(source_id or "").strip()
        checked_at = _now_iso()
        ok = False
        detail = "unknown_source"
        status = 0

        try:
            if sid == "openalex":
                ok, detail, status = self._probe_openalex(base_settings)
            elif sid == "semantic_scholar":
                ok, detail, status = self._probe_semantic_scholar(base_settings)
            elif sid == "mcp":
                ok, detail, status = self._probe_mcp_adapter(base_settings)
            else:
                raise ValueError(f"unsupported source_id={sid!r}")
        finally:
            with self._lock:
                payload = self._repository.load()
                at = {
                    k: v for k, v in dict(payload.get("agent_tools") or {}).items() if k != "_meta"
                }
                diag = dict(at.get("source_diagnostics") or {})
                diag[sid] = {
                    "last_test": checked_at,
                    "last_ok": bool(ok),
                    "last_error": "" if ok else str(detail),
                    "last_http_status": int(status or 0),
                }
                at["source_diagnostics"] = diag
                at["_meta"] = {
                    "last_updated_at": checked_at,
                    "last_updated_by": "source_test",
                }
                payload["agent_tools"] = at
                self._repository.save(payload)

        return {
            "source_id": sid,
            "ok": bool(ok),
            "detail": str(detail),
            "checked_at": checked_at,
        }

    @staticmethod
    def _probe_openalex(base_settings: Settings) -> tuple[bool, str, int]:
        mailto = str(getattr(base_settings, "openalex_mailto", "") or "").strip()
        headers = {"User-Agent": "science-graphrag-openalex-smoke/1.0"}
        if mailto:
            headers["From"] = mailto
        url = "https://api.openalex.org/works"
        params = {"search": "attention is all you need", "per-page": 1}
        try:
            with httpx.Client(timeout=12.0) as client:
                resp = client.get(url, params=params, headers=headers)
        except (httpx.HTTPError, OSError) as exc:
            return False, f"transport_error:{exc}", 0
        if resp.status_code != 200:
            return False, f"http_{resp.status_code}", int(resp.status_code)
        try:
            body = resp.json()
        except ValueError as exc:
            return False, f"json_error:{exc}", 200
        rows = body.get("results") if isinstance(body, dict) else None
        if not isinstance(rows, list):
            return False, "invalid_json_shape:results", 200
        return True, f"ok:results={len(rows)}", 200

    @staticmethod
    def _probe_semantic_scholar(base_settings: Settings) -> tuple[bool, str, int]:
        key = str(getattr(base_settings, "semantic_scholar_api_key", "") or "").strip()
        headers = {"User-Agent": "science-graphrag-semantic-scholar-smoke/1.0"}
        if key:
            headers["x-api-key"] = key
        url = "https://api.semanticscholar.org/graph/v1/paper/search"
        params = {"query": "attention is all you need", "limit": 1, "fields": "paperId,title"}
        try:
            with httpx.Client(timeout=12.0) as client:
                resp = client.get(url, params=params, headers=headers)
        except (httpx.HTTPError, OSError) as exc:
            return False, f"transport_error:{exc}", 0
        if resp.status_code != 200:
            return False, f"http_{resp.status_code}", int(resp.status_code)
        try:
            body = resp.json()
        except ValueError as exc:
            return False, f"json_error:{exc}", 200
        rows = body.get("data") if isinstance(body, dict) else None
        if not isinstance(rows, list):
            return False, "invalid_json_shape:data", 200
        return True, f"ok:results={len(rows)}", 200

    @staticmethod
    def _probe_mcp_adapter(base_settings: Settings) -> tuple[bool, str, int]:
        base = str(getattr(base_settings, "agent_mcp_http_base_url", "") or "").strip()
        if not base:
            return False, "missing_base_url", 0
        payload = {
            "jsonrpc": "2.0",
            "id": "settings-mcp-test",
            "method": "tools/list",
            "params": {"server": "smoke"},
        }
        try:
            with httpx.Client(
                timeout=float(
                    getattr(base_settings, "agent_mcp_request_timeout_seconds", 15.0) or 15.0
                )
            ) as client:
                resp = client.post(base, json=payload)
        except (httpx.HTTPError, OSError) as exc:
            return False, f"transport_error:{exc}", 0
        if resp.status_code != 200:
            return False, f"http_{resp.status_code}", int(resp.status_code)
        try:
            body = resp.json()
        except ValueError as exc:
            return False, f"json_error:{exc}", 200
        if not isinstance(body, dict):
            return False, "invalid_json_shape:object", 200
        if body.get("error"):
            return False, "rpc_error", 200
        return True, "ok", 200

    def update_storage_settings(  # pylint: disable=too-many-branches
        self,
        *,
        base_settings: Settings,
        actor: str,
        updates: dict[str, Any],
    ) -> SettingsSnapshot:
        """Persist storage / integration overrides (requires API restart to reconnect stores)."""

        if not updates:
            return self.get_snapshot(base_settings)

        secret_body_keys = ("neo4j_password", "database_url", "s3_secret_access_key")
        with self._lock:
            payload = self._repository.load()
            storage_next = dict(payload.get("storage") or {})
            json_updates = {k: v for k, v in updates.items() if k not in secret_body_keys}
            apply_storage_json_updates(storage_next, json_updates)

            explicit: dict[str, str | None] = {}
            if "neo4j_password" in updates:
                explicit[_SK_NEO4J_PASSWORD] = updates["neo4j_password"]
            if "database_url" in updates:
                explicit[_SK_DATABASE_URL] = updates["database_url"]
            if "s3_secret_access_key" in updates:
                explicit[_SK_S3_SECRET] = updates["s3_secret_access_key"]

            candidate = merged_runtime_candidate_from_persisted_payload(
                base_settings=base_settings,
                payload={
                    **payload,
                    "storage": storage_next,
                },
                secret_store=self._secret_store,
                storage_secret_explicit=explicit if explicit else None,
            )
            validate_settings_model_roundtrip(candidate)

            storage_next["_meta"] = {
                "last_updated_at": _now_iso(),
                "last_updated_by": actor,
                "restart_recommended": True,
            }
            payload["storage"] = storage_next

            if "neo4j_password" in updates:
                val = updates["neo4j_password"]
                if val is None or (isinstance(val, str) and not str(val).strip()):
                    self._secret_store.delete_secret(_SK_NEO4J_PASSWORD)
                else:
                    self._secret_store.set_secret(_SK_NEO4J_PASSWORD, str(val).strip())
            if "database_url" in updates:
                val = updates["database_url"]
                if val is None or (isinstance(val, str) and not str(val).strip()):
                    self._secret_store.delete_secret(_SK_DATABASE_URL)
                else:
                    self._secret_store.set_secret(_SK_DATABASE_URL, str(val).strip())
            if "s3_secret_access_key" in updates:
                val = updates["s3_secret_access_key"]
                if val is None or (isinstance(val, str) and not str(val).strip()):
                    self._secret_store.delete_secret(_SK_S3_SECRET)
                else:
                    self._secret_store.set_secret(_SK_S3_SECRET, str(val).strip())

            self._repository.save(payload)
        return self.get_snapshot(base_settings)

    def update_benchmark_settings(
        self,
        *,
        base_settings: Settings,
        actor: str,
        by_family: dict[str, dict[str, Any]],
    ) -> SettingsSnapshot:
        """Persist per-family benchmark launcher defaults (non-secret, UI + launcher merge)."""
        if not by_family:
            return self.get_snapshot(base_settings)
        allowed_keys = (
            "model_profile",
            "custom_model_id",
            "gold_source",
            "threshold_profile",
            "base_url_override",
            "api_key_env_name",
        )
        with self._lock:
            payload = self._repository.load()
            bench = dict(payload.get("benchmark") or {})
            by_existing: dict[str, Any] = dict(bench.get("by_family") or {})
            for fam_key, patch in by_family.items():
                fam = normalize_benchmark_family_key(fam_key)
                prev_slice = dict(by_existing.get(fam) or {})
                merged_input = dict(prev_slice)
                for key in allowed_keys:
                    if key in patch:
                        merged_input[key] = patch[key]
                merged = merge_persisted_benchmark_family(fam, merged_input)
                validate_merged_benchmark_family_prefs(fam, merged)
                by_existing[fam] = merged
            bench["by_family"] = by_existing
            bench["_meta"] = {
                "last_updated_at": _now_iso(),
                "last_updated_by": actor,
            }
            payload["benchmark"] = bench
            self._repository.save(payload)
        return self.get_snapshot(base_settings)

    def test_llm_connection(  # pylint: disable=too-many-locals
        self,
        *,
        base_settings: Settings,
        actor: str,
        draft: LlmTestDraft | None = None,
    ) -> dict[str, Any]:
        """Run a minimal OpenAI-compatible probe using current or draft settings."""
        del actor  # Reserved for future audit trail.
        snapshot = self.get_snapshot(base_settings)
        return run_settings_llm_test_probe(
            base_settings=base_settings,
            secret_store=self._secret_store,
            effective_llm_snapshot=snapshot.llm["effective"],
            draft=draft,
            probe_fn=run_llm_connection_probe,
        )


__all__ = [
    "LlmTestDraft",
    "SettingsService",
    "SettingsSnapshot",
    "run_llm_connection_probe",
]
