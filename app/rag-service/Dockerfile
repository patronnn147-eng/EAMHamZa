FROM python:3.11-slim

WORKDIR /app

# System deps:
#   gcc          — pip-compile time (native extensions in asyncpg, etc.)
#   curl         — runtime HEALTHCHECK
#   tesseract-ocr + fra/eng — runtime OCR for scanned/image-only PDFs
# upgrade first to patch base-image OS CVEs (perl, linux-libc-dev, etc.)
RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get install -y --no-install-recommends \
        gcc curl \
        tesseract-ocr tesseract-ocr-fra tesseract-ocr-eng && \
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

# Point HF/ST caches to a directory that will be mounted as a named volume.
# BAAI/bge-m3 is public — no HF_TOKEN needed. Model downloads on first start,
# then served from the volume on every subsequent start (no re-download).
ENV HF_HOME=/app/.cache/huggingface
ENV SENTENCE_TRANSFORMERS_HOME=/app/.cache/sentence_transformers

COPY . .

# Pre-create cache dirs BEFORE chown so the named volume inherits raguser ownership.
# Without this, Docker creates the mount point as root → "Permission denied" at runtime.
RUN mkdir -p /app/.cache/huggingface /app/.cache/sentence_transformers

# Non-root user — security baseline; never run ML inference as root.
RUN addgroup --gid 1001 raguser && \
    adduser --disabled-password --gecos "" --uid 1001 --ingroup raguser raguser && \
    chown -R raguser:raguser /app

USER raguser

HEALTHCHECK --interval=30s --timeout=10s --start-period=180s --retries=3 \
    CMD curl -f http://localhost:8003/health || exit 1

EXPOSE 8003
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8003", "--workers", "1"]
