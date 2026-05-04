"""Legacy agent HTTP route (removed); retained only to return HTTP 410 + successor link."""

from __future__ import annotations

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

router = APIRouter()

_GONE_DETAIL = "POST /v1/agent/query was removed. Use POST /v2/agent/query (see Link header)."


@router.post("/agent/query")
def post_agent_query_removed() -> JSONResponse:
    """Legacy route removed; use ``POST /v2/agent/query`` (``agent_v2``)."""

    return JSONResponse(
        status_code=status.HTTP_410_GONE,
        content={
            "detail": _GONE_DETAIL,
            "replacement": "/v2/agent/query",
        },
        headers={"Link": '</v2/agent/query>; rel="successor-version"'},
    )
