FROM python:3.11-alpine

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

# Runtime deps: bash (start.sh), curl (healthcheck), postgresql-client (db ops)
# Build deps: gcc + musl-dev + python3-dev + libffi-dev + openssl-dev needed to
# compile asyncpg, cryptography, argon2-cffi C extensions — removed after install.
RUN apk add --no-cache \
        bash \
        curl \
        postgresql-client \
    && apk add --no-cache --virtual .build-deps \
        gcc \
        g++ \
        musl-dev \
        python3-dev \
        libffi-dev \
        openssl-dev \
        libpq-dev \
    && pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt \
    && apk del .build-deps \
    && sed -i 's/\r$//' start.sh && chmod +x start.sh \
    && mkdir -p logs \
    && adduser -D -u 1000 appuser \
    && chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

CMD ["./start.sh"]
