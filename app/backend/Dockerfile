# Multi-stage build for FastAPI backend

# Stage 1: Build — install Python deps into an isolated venv
FROM python:3.11-slim AS builder

WORKDIR /app

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .

# python:3.11-slim (Debian Bookworm) — all ML packages (xgboost, scikit-learn,
# numpy, pandas, shap) ship manylinux wheels, so zero source compilation.
# No build toolchain needed here; deps land in /opt/venv, discarded with this
# stage. Kept before the source COPYs in the final stage below, so editing
# app code never busts the pip cache (xgboost wheel alone is ~300MB).
RUN pip install --no-cache-dir "pip>=26.1.2" \
    && pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir --upgrade "jaraco.context>=6.1.0" "wheel>=0.46.2"

# Stage 2: Runtime — slim image, no build cache/toolchain
FROM python:3.11-slim

WORKDIR /app

# apt-get upgrade -y: picks up OS security patches at build time.
# purge linux-libc-dev: kernel headers pulled in by base image, never needed
# at runtime (CVE-2026-43185).
RUN apt-get update -qq \
    && apt-get upgrade -y \
    && apt-get install -y --no-install-recommends \
        curl \
        postgresql-client \
    && apt-get purge -y --auto-remove linux-libc-dev \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY start.sh main.py alembic.ini lambda_handler.py .
COPY alembic ./alembic
COPY core ./core
COPY data_models ./data_models
COPY dependencies ./dependencies
COPY middlewares ./middlewares
COPY mock_data ./mock_data
COPY models ./models
COPY modules ./modules
COPY schemas ./schemas
COPY scripts ./scripts
COPY services ./services
COPY tasks ./tasks
COPY utils ./utils

RUN sed -i 's/\r$//' start.sh && chmod +x start.sh \
    && mkdir -p logs \
    && adduser --disabled-password --gecos "" --uid 1000 appuser \
    && chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

CMD ["./start.sh"]
