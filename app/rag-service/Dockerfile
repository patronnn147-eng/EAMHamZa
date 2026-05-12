FROM python:3.11-slim

WORKDIR /app

# System deps:
#   gcc  — needed only at pip-compile time (native extensions in asyncpg, etc.)
#   curl — needed at runtime for HEALTHCHECK
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc curl && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# 1. CPU-only torch — must come BEFORE sentence-transformers install.
#    Without this, pip resolves torch with CUDA (~3.5 GB of nvidia-* packages).
# 2. Install remaining requirements.
# 3. Purge gcc — no longer needed at runtime; reduces final image ~30 MB.
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu && \
    pip install --no-cache-dir -r requirements.txt && \
    apt-get purge -y --auto-remove gcc && \
    rm -rf /var/lib/apt/lists/*

# Point HF/ST caches into /app so they survive the upcoming chown.
# Default paths (/root/.cache) would be inaccessible after USER switch.
ENV HF_HOME=/app/.cache/huggingface
ENV SENTENCE_TRANSFORMERS_HOME=/app/.cache/sentence_transformers

# HF_TOKEN passed at build time only — ARG not promoted to ENV so never baked into image.
# Usage: docker compose build --build-arg HF_TOKEN=hf_xxx rag-service
ARG HF_TOKEN

# Bake model into image (~120 MB) — multilingual, handles French/Arabic/EN.
# paraphrase-multilingual-MiniLM-L12-v2: 384 dims, same as all-MiniLM-L6-v2.
# HF_TOKEN injected inline so it never persists in any layer.
RUN HF_TOKEN=${HF_TOKEN} python -c "from sentence_transformers import SentenceTransformer; \
    SentenceTransformer('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2')"

COPY . .

# Non-root user — security baseline; never run ML inference as root.
RUN addgroup --gid 1001 raguser && \
    adduser --disabled-password --gecos "" --uid 1001 --ingroup raguser raguser && \
    chown -R raguser:raguser /app

USER raguser

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8003/health || exit 1

EXPOSE 8003
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8003", "--workers", "1"]
