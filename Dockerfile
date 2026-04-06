# API and CLI image (Python only). Static React UI is served by the compose `web` service.
# Rebuild only this image when backend changes: docker compose build api
FROM python:3.11-slim-bookworm

RUN apt-get update \
    && apt-get install -y --no-install-recommends poppler-utils \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml README.md LICENSE ./
COPY science_graphrag ./science_graphrag
COPY eval ./eval

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir .

EXPOSE 8787

CMD ["uvicorn", "science_graphrag.api.main:app", "--host", "0.0.0.0", "--port", "8787"]
