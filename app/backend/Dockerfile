# Single-stage build for Python backend
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy only the files and directories required by the backend
COPY requirements.txt start.sh main.py alembic.ini lambda_handler.py .
COPY alembic core data_models dependencies middlewares mock_data models modules schemas scripts services tasks utils ./

# Install system dependencies, Python dependencies, and prepare runtime permissions in one layer
RUN apt-get update && apt-get install -y \
    bash \
    gcc \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt \
    && sed -i 's/\r$//' start.sh && chmod +x start.sh \
    && mkdir -p logs \
    && useradd -m -u 1000 appuser \
    && chown -R appuser:appuser /app

USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

# Start application with migrations
CMD ["./start.sh"]