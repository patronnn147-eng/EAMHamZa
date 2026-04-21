# syntax=docker/dockerfile:1
# EAM ML Prediction Service v2.0.0
FROM python:3.11-slim

WORKDIR /app

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# ── Layer 1: Heavy deps (torch, numpy, sklearn, scipy…) ──────────────────────
# Cached until requirements-heavy.txt changes. BuildKit cache mount means
# packages are kept on the host between builds — no re-download even when
# this layer is invalidated.
# HEAVY_CACHE_BUST can be passed via --build-arg to force reinstall.
ARG HEAVY_CACHE_BUST=4
COPY requirements-heavy.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements-heavy.txt

# ── Layer 2: Light deps (fastapi, pydantic, uvicorn…) ────────────────────────
# Changes frequently; reinstalls in ~15s because packages are small.
COPY requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements.txt

# ── Source code & models (most frequently changed — no pip cost) ──────────────
COPY src/ ./src/
COPY models/ ./models/
COPY main.py .

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
