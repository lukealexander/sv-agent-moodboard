ARG PYTHON_VERSION=3.12

# ── dev ──────────────────────────────────────────────────────────────────────
FROM python:${PYTHON_VERSION}-slim AS dev

WORKDIR /app

# Install uv from the official distroless image — faster and more reliable than pip/curl
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# curl is required by the ECS task-definition container health check
# (curl -f localhost/health); libpq-dev provides Postgres client headers.
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy lock file and project metadata first to maximise Docker layer caching
COPY pyproject.toml uv.lock ./
RUN uv sync --extra dev --frozen

# Source is mounted at runtime in dev/devcontainer; copy here for CI
COPY . .

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# ── prod ─────────────────────────────────────────────────────────────────────
FROM python:${PYTHON_VERSION}-slim AS prod

WORKDIR /app

# Install uv from the official distroless image — faster and more reliable than pip/curl
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# curl is required by the ECS task-definition container health check
# (curl -f localhost/health); libpq-dev provides Postgres client headers.
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy lock file and project metadata first to maximise Docker layer caching
COPY pyproject.toml uv.lock ./
# --no-dev ensures dev extras are excluded; --frozen treats uv.lock as authoritative
RUN uv sync --frozen --no-dev

COPY . .

# Apply DB migrations on startup (when DATABASE_URL is set), then exec the CMD.
# chmod here so the build doesn't depend on the committed file mode.
RUN chmod +x docker-entrypoint.sh

EXPOSE 8000
ENTRYPOINT ["/app/docker-entrypoint.sh"]
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
