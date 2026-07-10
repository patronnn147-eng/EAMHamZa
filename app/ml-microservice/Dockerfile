# syntax=docker/dockerfile:1
# EAM ML Prediction Service v2.0.0
FROM python:3.11-slim

WORKDIR /app

# Upgrade OS packages, install runtime deps, then remove linux-libc-dev
# (kernel headers — never needed at runtime, but pulled in by python:3.11-slim base).
RUN apt-get update && apt-get upgrade -y && apt-get install -y --no-install-recommends \
    curl \
    && apt-get purge -y --auto-remove linux-libc-dev \
    && rm -rf /var/lib/apt/lists/*

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
# The subsequent requirements-heavy install then sees torch already satisfied.
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --index-url https://download.pytorch.org/whl/cpu 'torch>=2.2.0'
COPY requirements-heavy.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements-heavy.txt

# ── Layer 2: Light deps (fastapi, pydantic, uvicorn…) ────────────────────────
# Changes frequently; reinstalls in ~15s because packages are small.
COPY requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements.txt

# ── CVE patches: upgrade pip build-tools left in final image ──────────────────
# jaraco.context>=6.1.0 (CVE-2026-23949), wheel>=0.46.2 (CVE-2026-24049)
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --upgrade "jaraco.context>=6.1.0" "wheel>=0.46.2"

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
