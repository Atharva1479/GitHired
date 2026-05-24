FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
        libpq5 \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv==0.5.0

# /srv because /app would collide with our actual `app` package directory
# (would create /app/app — confusing during shell debugging in the
# container).
WORKDIR /srv

# Build context is the backend/ folder. Order matters for layer caching:
# pyproject + lock change less often than app code, so installing deps
# first lets later code-only rebuilds reuse the deps layer.
COPY pyproject.toml ./
COPY uv.lock* ./
RUN uv sync --frozen --no-dev || uv sync --no-dev

COPY app ./app
COPY alembic.ini ./

ENV PATH="/srv/.venv/bin:$PATH"
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
