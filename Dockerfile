# syntax=docker/dockerfile:1
# Multi-stage build for Railway / container deployments.
# Uses uv for fast, reproducible dependency resolution.

# ---------------------------------------------------------------------------
# Stage 1: Build
# ---------------------------------------------------------------------------
FROM python:3.13-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:0.10.6 /uv /usr/local/bin/uv

WORKDIR /home/user/app

# Install dependencies first (layer cache optimisation).
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --extra ui --no-dev --no-install-project

# Copy source and install the project itself.
COPY . .
RUN uv sync --frozen --extra ui --no-dev

# ---------------------------------------------------------------------------
# Stage 2: Runtime
# ---------------------------------------------------------------------------
FROM python:3.13-slim

# Create non-root user with UID 1000 (required for Hugging Face Spaces & security)
RUN useradd -m -u 1000 user

WORKDIR /home/user/app

# Copy the entire virtualenv + project from the builder with non-root ownership.
COPY --chown=user:user --from=builder /home/user/app /home/user/app

# Symlink /app to /home/user/app for backwards compatibility
RUN ln -s /home/user/app /app

USER user

ENV HOME=/home/user \
    PATH="/home/user/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PORT=7860

# Port 7860 is default for Hugging Face Spaces (supports PORT env override)
EXPOSE 7860

CMD ["sh", "-c", "exec /home/user/app/.venv/bin/optopsy-chat run --host 0.0.0.0 --port ${PORT:-8000} --headless"]
