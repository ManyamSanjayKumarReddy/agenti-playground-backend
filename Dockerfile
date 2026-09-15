# ── Stage 1: Builder ──────────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /app

# Install uv for fast dependency resolution
RUN pip install --no-cache-dir uv

COPY pyproject.toml .

# Install deps into a local venv
RUN uv venv .venv && \
    . .venv/bin/activate && \
    uv pip install --no-cache .


# ── Stage 2: Runtime ─────────────────────────────────────────────
FROM python:3.11-slim

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /app/.venv /app/.venv

# Copy application source
COPY agent_v1/ ./agent_v1/
COPY pyproject.toml .

# Generated projects land here at runtime (mounted as a volume)
RUN mkdir -p /app/generated_projects

# Activate the venv for all subsequent RUN/CMD
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

EXPOSE 8000

# Shell form so $PORT (Render, and similar PaaS targets) is respected —
# falls back to 8000 for local `docker compose up` / EC2 where it's unset.
CMD uvicorn agent_v1.api.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1