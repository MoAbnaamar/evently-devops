# syntax=docker/dockerfile:1

# ==============================
# Stage 1: Builder
# ==============================

# Builder stage for dependency installation
FROM python:3.12-slim-bookworm AS builder

# Copy static uv binary from official image
COPY --from=ghcr.io/astral-sh/uv:0.12.6 /uv /bin/uv

# Configure uv build environment flags
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never

WORKDIR /app

# Copy dependency specification files
COPY pyproject.toml uv.lock .python-version ./

# Install production dependencies into virtual environment (according to uv.lock and without test tooling)
RUN uv sync --frozen --no-dev

# ==============================
# Stage 2: Runtime
# ==============================

# Runtime stage for application execution
FROM python:3.12-slim-bookworm AS runtime

# Set Python execution environment variables and PATH (send stdout/stderr to container log and dont write .pyc files)
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/app/.venv/bin:$PATH"

# Create non-root system user and group
RUN groupadd --system --gid 1001 evently \
    && useradd --system --uid 1001 --gid evently --no-create-home evently

WORKDIR /app

# Copy virtual environment and application code with correct ownership
COPY --from=builder --chown=evently:evently /app/.venv /app/.venv
COPY --chown=evently:evently app ./app

USER evently

# Expose application port
EXPOSE 8000

# Start application server
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]