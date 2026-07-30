# syntax=docker/dockerfile:1
# EAM ML Prediction Service v2.0.0
# Multi-stage build

# Stage 1: Build — install Python deps into an isolated venv
FROM python:3.11-slim AS builder

ARG TARGETARCH

WORKDIR /app

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# ── Layer 1: Heavy deps (torch, numpy, sklearn, scipy…) ──────────────────────
# Cached until requirements-heavy.txt changes. BuildKit cache mount means
# packages are kept on the host between builds — no re-download even when
# this layer is invalidated.
# HEAVY_CACHE_BUST can be passed via --build-arg to force reinstall.
ARG HEAVY_CACHE_BUST=4
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install "pip>=26.1.2"
# CPU-only torch: this is an inference service with no GPU in CI/prod. Installing
# torch from the dedicated CPU index FIRST avoids pulling PyPI's default CUDA
# build (~2.5GB of nvidia-* wheels) which blew past the CI build-images timeout.
# The subsequent requirements-heavy install then sees torch already satisfied
# (same venv site-packages across builder-stage RUN layers).
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --index-url https://download.pytorch.org/whl/cpu 'torch>=2.2.0'
COPY requirements-heavy.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements-heavy.txt

# tensorflow-cpu has no linux/arm64 wheels on PyPI (any version) — skip on
# arm64 builds. P4's autoencoder is optional at runtime (guarded ImportError,
# weights renormalized across the remaining ensemble methods).
COPY requirements-tf.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    if [ "$TARGETARCH" = "amd64" ]; then pip install -r requirements-tf.txt; fi

# ── Layer 2: Light deps (fastapi, pydantic, uvicorn…) ────────────────────────
# Changes frequently; reinstalls in ~15s because packages are small.
COPY requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements.txt

# ── CVE patches: upgrade pip build-tools left in final image ──────────────────
# jaraco.context>=6.1.0 (CVE-2026-23949), wheel>=0.46.2 (CVE-2026-24049)
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --upgrade "jaraco.context>=6.1.0" "wheel>=0.46.2"

# Stage 2: Runtime — slim image, no pip cache/build toolchain
FROM python:3.11-slim

WORKDIR /app

# Upgrade OS packages, install runtime deps, then remove linux-libc-dev
# (kernel headers — never needed at runtime, but pulled in by python:3.11-slim base).
RUN apt-get update && apt-get upgrade -y && apt-get install -y --no-install-recommends \
    curl \
    && apt-get purge -y --auto-remove linux-libc-dev \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# ── Source code & models (most frequently changed — no pip cost) ──────────────
COPY src/ ./src/
COPY models/ ./models/
COPY main.py .
COPY ai4i2020.csv .

RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
