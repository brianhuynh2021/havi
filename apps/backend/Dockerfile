# Multi-stage production Dockerfile for Havi backend (FastAPI, Celery Worker, Celery Beat)
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

# Install dependencies with cache mount
COPY pyproject.toml /app/
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --no-dev --extra queue --extra db --extra storage --no-install-project

COPY . /app
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --no-dev --extra queue --extra db --extra storage

# Runtime image
FROM python:3.12-slim-bookworm AS runner

WORKDIR /app

# Install runtime system packages (curl for healthcheck, ffmpeg for video probe)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Copy virtualenv and application code
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app /app

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Non-root user for security
RUN useradd -m -u 1000 havi && chown -R havi:havi /app
USER havi

EXPOSE 8000

# Default command runs the FastAPI API server
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
