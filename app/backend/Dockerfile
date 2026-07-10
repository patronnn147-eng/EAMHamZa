FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt start.sh main.py alembic.ini lambda_handler.py .
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

# python:3.11-slim (Debian Bookworm) — all ML packages (xgboost, scikit-learn,
# numpy, pandas, shap) ship manylinux wheels, so zero source compilation.
# No build toolchain needed; only runtime deps installed.
RUN apt-get update -qq \
    && apt-get install -y --no-install-recommends \
        curl \
        postgresql-client \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt \
    && sed -i 's/\r$//' start.sh && chmod +x start.sh \
    && mkdir -p logs \
    && adduser --disabled-password --gecos "" --uid 1000 appuser \
    && chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

CMD ["./start.sh"]
