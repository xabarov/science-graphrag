# syntax=docker/dockerfile:1.7
# API and CLI image (Python only). Static React UI is served by the compose `web` service.
# Rebuild only this image when backend changes: docker compose build api
FROM python:3.12-slim-bookworm

RUN apt-get update \
    && apt-get install -y --no-install-recommends poppler-utils \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml README.md LICENSE ./
COPY science_graphrag ./science_graphrag

# python-multipart is required for multipart routes (e.g. workspace document upload); keep explicit so
# `pip install .` cache layers cannot accidentally omit it on older pyproject snapshots.
# [agent] extra installs langgraph/langchain-core/langchain-openai required by agent/runtime.py.
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --upgrade pip \
    && pip install "python-multipart>=0.0.9" \
    && pip install ".[agent]"

# Keep non-runtime directories after dependency install so edits there
# do not invalidate the expensive `pip install` layer.
COPY eval ./eval
COPY tests/fixtures ./tests/fixtures

EXPOSE 8787

CMD ["uvicorn", "science_graphrag.api.main:app", "--host", "0.0.0.0", "--port", "8787"]
