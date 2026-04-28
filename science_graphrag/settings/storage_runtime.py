"""Runtime overlay + UI snapshot helpers for storage / integrations settings."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from science_graphrag.settings.secret_display import mask_short_secret
from science_graphrag.settings.secrets import SecretStore

_SK_NEO4J_PASSWORD = "storage.neo4j_password"
_SK_DATABASE_URL = "storage.database_url"
_SK_S3_SECRET = "storage.s3_secret_access_key"


def _pick_secret(
    sk_name: str,
    secret_store: SecretStore,
    explicit: dict[str, str | None] | None,
    base_val: str,
) -> str:
    """``explicit`` uses SecretStore key names; empty/None value means fall back to env/base."""

    if explicit and sk_name in explicit:
        val = explicit[sk_name]
        if val is None or (isinstance(val, str) and not str(val).strip()):
            return base_val
        return str(val).strip()
    saved = secret_store.get_secret(sk_name)
    return saved if saved else base_val


# Keys persisted in runtime_settings.json under "storage" (non-secret).
STORAGE_JSON_SCALAR_KEYS = (
    "neo4j_uri",
    "neo4j_user",
    "qdrant_url",
    "qdrant_collection",
    "qdrant_claims_collection",
    "qdrant_work_embeddings_collection",
    "qdrant_author_embeddings_collection",
    "redis_url",
    "blob_root",
    "artifact_root",
    "s3_endpoint_url",
    "s3_bucket",
    "s3_artifact_key_prefix",
    "s3_access_key_id",
    "s3_benchmark_runs_key_prefix",
    "s3_diagnostics_key_prefix",
)

STORAGE_JSON_BOOL_KEYS = (
    "object_storage_enabled",
    "s3_use_ssl",
    "benchmark_runs_object_storage",
    "diagnostics_object_storage",
)


def mask_url_userinfo(raw: str | None) -> str | None:
    """Redact user:password in netloc for DSN-style URLs."""

    if not raw:
        return None
    try:
        p = urlsplit(raw)
        if "@" not in p.netloc:
            return raw
        userinfo, _, hostport = p.netloc.rpartition("@")
        if ":" in userinfo:
            user, _, _pw = userinfo.partition(":")
            masked = f"{user}:***@{hostport}"
        else:
            masked = f"{userinfo}@{hostport}"
        return urlunsplit((p.scheme, masked, p.path, p.query, p.fragment))
    except (TypeError, ValueError):
        return raw


def _pick_str(sk: dict[str, Any], key: str, base_val: str) -> str:
    if key not in sk:
        return base_val
    raw = sk.get(key)
    if raw is None:
        return base_val
    s = str(raw).strip()
    return s if s else base_val


def _pick_bool(sk: dict[str, Any], key: str, base_val: bool) -> bool:
    if key not in sk:
        return base_val
    return bool(sk.get(key))


def _pick_path_str(sk: dict[str, Any], key: str, base: Path) -> Path:
    s = _pick_str(sk, key, str(base))
    return Path(s)


def merge_storage_runtime_fields(
    base_settings: Any,
    storage_cfg: dict[str, Any] | None,
    secret_store: SecretStore,
    *,
    explicit_secrets: dict[str, str | None] | None = None,
) -> dict[str, Any]:
    """Return Settings attribute updates from persisted storage + secrets."""

    sk = {k: v for k, v in dict(storage_cfg or {}).items() if not str(k).startswith("_")}

    out: dict[str, Any] = {
        "neo4j_uri": _pick_str(sk, "neo4j_uri", base_settings.neo4j_uri),
        "neo4j_user": _pick_str(sk, "neo4j_user", base_settings.neo4j_user),
        "qdrant_url": _pick_str(sk, "qdrant_url", base_settings.qdrant_url),
        "qdrant_collection": _pick_str(sk, "qdrant_collection", base_settings.qdrant_collection),
        "qdrant_claims_collection": _pick_str(
            sk, "qdrant_claims_collection", base_settings.qdrant_claims_collection
        ),
        "qdrant_work_embeddings_collection": _pick_str(
            sk,
            "qdrant_work_embeddings_collection",
            base_settings.qdrant_work_embeddings_collection,
        ),
        "qdrant_author_embeddings_collection": _pick_str(
            sk,
            "qdrant_author_embeddings_collection",
            base_settings.qdrant_author_embeddings_collection,
        ),
        "redis_url": _pick_str(sk, "redis_url", base_settings.redis_url),
        "blob_root": _pick_path_str(sk, "blob_root", base_settings.blob_root),
        "artifact_root": _pick_path_str(sk, "artifact_root", base_settings.artifact_root),
        "object_storage_enabled": _pick_bool(
            sk, "object_storage_enabled", base_settings.object_storage_enabled
        ),
        "s3_use_ssl": _pick_bool(sk, "s3_use_ssl", base_settings.s3_use_ssl),
        "benchmark_runs_object_storage": _pick_bool(
            sk, "benchmark_runs_object_storage", base_settings.benchmark_runs_object_storage
        ),
        "diagnostics_object_storage": _pick_bool(
            sk, "diagnostics_object_storage", base_settings.diagnostics_object_storage
        ),
    }

    ep = sk.get("s3_endpoint_url")
    if "s3_endpoint_url" in sk:
        if ep is None or (isinstance(ep, str) and not str(ep).strip()):
            out["s3_endpoint_url"] = None
        else:
            out["s3_endpoint_url"] = str(ep).strip()
    else:
        out["s3_endpoint_url"] = base_settings.s3_endpoint_url

    out["s3_bucket"] = _pick_str(sk, "s3_bucket", base_settings.s3_bucket)
    out["s3_artifact_key_prefix"] = _pick_str(
        sk, "s3_artifact_key_prefix", base_settings.s3_artifact_key_prefix
    )
    if "s3_access_key_id" in sk:
        aid = sk.get("s3_access_key_id")
        if aid is None or (isinstance(aid, str) and not str(aid).strip()):
            out["s3_access_key_id"] = None
        else:
            out["s3_access_key_id"] = str(aid).strip()
    else:
        out["s3_access_key_id"] = base_settings.s3_access_key_id

    style = sk.get("s3_addressing_style")
    if "s3_addressing_style" in sk and style in ("path", "virtual"):
        out["s3_addressing_style"] = style
    else:
        out["s3_addressing_style"] = base_settings.s3_addressing_style

    out["s3_benchmark_runs_key_prefix"] = _pick_str(
        sk, "s3_benchmark_runs_key_prefix", base_settings.s3_benchmark_runs_key_prefix
    )
    out["s3_diagnostics_key_prefix"] = _pick_str(
        sk, "s3_diagnostics_key_prefix", base_settings.s3_diagnostics_key_prefix
    )

    out["neo4j_password"] = _pick_secret(
        _SK_NEO4J_PASSWORD, secret_store, explicit_secrets, base_settings.neo4j_password
    )
    out["database_url"] = _pick_secret(
        _SK_DATABASE_URL, secret_store, explicit_secrets, base_settings.database_url
    )
    raw_s3_base = base_settings.s3_secret_access_key or ""
    out["s3_secret_access_key"] = _pick_secret(
        _SK_S3_SECRET, secret_store, explicit_secrets, raw_s3_base
    )

    return out


def _src(key: str, sk: dict[str, Any]) -> str:
    return "server_managed" if key in sk else "environment"


def build_storage_ui_snapshot(
    *,
    base_settings: Any,
    storage_cfg: dict[str, Any],
    secret_store: SecretStore,
) -> dict[str, Any]:
    """Masked, UI-facing storage snapshot."""

    sk = {k: v for k, v in dict(storage_cfg or {}).items() if not str(k).startswith("_")}
    meta = dict(storage_cfg.get("_meta") or {})

    merged = merge_storage_runtime_fields(base_settings, sk, secret_store)

    has_saved_neo4j_pw = bool(secret_store.get_secret(_SK_NEO4J_PASSWORD))
    has_saved_dsn = bool(secret_store.get_secret(_SK_DATABASE_URL))
    has_saved_s3_secret = bool(secret_store.get_secret(_SK_S3_SECRET))

    def neo_pw_source() -> str:
        if has_saved_neo4j_pw:
            return "server_managed"
        if str(base_settings.neo4j_password or "").strip():
            return "environment"
        return "none"

    def dsn_source() -> str:
        if has_saved_dsn:
            return "server_managed"
        if str(base_settings.database_url or "").strip():
            return "environment"
        return "none"

    def s3_secret_source() -> str:
        if has_saved_s3_secret:
            return "server_managed"
        if str(base_settings.s3_secret_access_key or "").strip():
            return "environment"
        return "none"

    active_neo_pw = merged["neo4j_password"]
    active_dsn = merged["database_url"]
    active_s3_secret = merged["s3_secret_access_key"]

    out: dict[str, Any] = {
        "neo4j": {
            "persisted": {k: sk.get(k) for k in ("neo4j_uri", "neo4j_user") if k in sk},
            "effective": {
                "resolved_uri": merged["neo4j_uri"],
                "resolved_user": merged["neo4j_user"],
                "masked_password": mask_short_secret(active_neo_pw),
            },
            "fields": {
                "neo4j_uri": {
                    "persisted": sk.get("neo4j_uri"),
                    "effective": merged["neo4j_uri"],
                    "source": _src("neo4j_uri", sk),
                },
                "neo4j_user": {
                    "persisted": sk.get("neo4j_user"),
                    "effective": merged["neo4j_user"],
                    "source": _src("neo4j_user", sk),
                },
                "neo4j_password": {
                    "secret_source": neo_pw_source(),
                    "masked": mask_short_secret(active_neo_pw),
                },
            },
        },
        "qdrant": {
            "fields": {
                k: {
                    "persisted": sk.get(k),
                    "effective": merged[k],
                    "source": _src(k, sk),
                }
                for k in (
                    "qdrant_url",
                    "qdrant_collection",
                    "qdrant_claims_collection",
                    "qdrant_work_embeddings_collection",
                    "qdrant_author_embeddings_collection",
                )
            }
        },
        "postgres": {
            "fields": {
                "database_url": {
                    "secret_source": dsn_source(),
                    "masked": mask_url_userinfo(active_dsn),
                }
            }
        },
        "redis": {
            "fields": {
                "redis_url": {
                    "persisted": sk.get("redis_url"),
                    "effective": merged["redis_url"],
                    "source": _src("redis_url", sk),
                    "masked": mask_url_userinfo(merged["redis_url"]),
                }
            }
        },
        "paths": {
            "fields": {
                "blob_root": {
                    "persisted": sk.get("blob_root"),
                    "effective": str(merged["blob_root"]),
                    "source": _src("blob_root", sk),
                },
                "artifact_root": {
                    "persisted": sk.get("artifact_root"),
                    "effective": str(merged["artifact_root"]),
                    "source": _src("artifact_root", sk),
                },
            }
        },
        "s3": {
            "fields": {
                **{
                    k: {
                        "persisted": sk.get(k),
                        "effective": merged.get(k),
                        "source": _src(k, sk),
                    }
                    for k in (
                        "object_storage_enabled",
                        "s3_endpoint_url",
                        "s3_bucket",
                        "s3_use_ssl",
                        "s3_addressing_style",
                        "s3_artifact_key_prefix",
                        "s3_access_key_id",
                        "benchmark_runs_object_storage",
                        "diagnostics_object_storage",
                        "s3_benchmark_runs_key_prefix",
                        "s3_diagnostics_key_prefix",
                    )
                },
                "s3_secret_access_key": {
                    "secret_source": s3_secret_source(),
                    "masked": mask_short_secret(active_s3_secret),
                },
            }
        },
        "status": {
            "last_updated_at": meta.get("last_updated_at"),
            "last_updated_by": meta.get("last_updated_by"),
            "requires_process_restart": bool(meta.get("restart_recommended")),
        },
    }
    return out


def apply_storage_json_updates(
    storage: dict[str, Any],
    updates: dict[str, Any],
) -> None:
    """Mutate ``storage`` with non-secret keys from ``updates`` (already filtered)."""

    for key in STORAGE_JSON_SCALAR_KEYS:
        if key not in updates:
            continue
        val = updates[key]
        if val is None:
            storage.pop(key, None)
            continue
        if isinstance(val, str) and not val.strip():
            storage.pop(key, None)
            continue
        storage[key] = str(val).strip() if isinstance(val, str) else val

    for key in STORAGE_JSON_BOOL_KEYS:
        if key not in updates:
            continue
        storage[key] = bool(updates[key])

    if "s3_addressing_style" in updates:
        st = updates["s3_addressing_style"]
        if st in ("path", "virtual"):
            storage["s3_addressing_style"] = st


__all__ = [
    "STORAGE_JSON_BOOL_KEYS",
    "STORAGE_JSON_SCALAR_KEYS",
    "_SK_DATABASE_URL",
    "_SK_NEO4J_PASSWORD",
    "_SK_S3_SECRET",
    "apply_storage_json_updates",
    "build_storage_ui_snapshot",
    "mask_short_secret",
    "mask_url_userinfo",
    "merge_storage_runtime_fields",
]
