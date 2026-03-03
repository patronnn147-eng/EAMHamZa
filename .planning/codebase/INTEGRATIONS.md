# External Integrations

**Analysis Date:** 2026-03-03

## APIs & External Services

**AI Services:**
- OpenAI-compatible API (custom base URL)
  - SDK: `openai` Python package
  - Configuration: `APP_AI_BASE_URL`, `APP_AI_KEY`
  - Features: Text generation (gentxt), image generation (genimg), streaming support

**Payment Processing:**
- Stripe - Payment gateway
  - SDK: `stripe` Python package
  - Features: Checkout sessions, subscriptions, embedded/hosted UI modes
  - Config: `STRIPE_SECRET_KEY` environment variable

## Data Storage

**Primary Database:**
- PostgreSQL 15
  - Connection: `postgresql+asyncpg://user:pass@host:5432/db`
  - ORM: SQLAlchemy 2.0 async mode
  - Migrations: Alembic
  - Default: `asset_management` database

**Object Storage:**
- MinIO (S3-compatible)
  - SDK: `minio` Python package
  - Connection: `http://minio:9000` (container) or `http://localhost:9000` (local)
  - Credentials: `MINIO_ROOT_USER` / `MINIO_ROOT_PASSWORD`
  - Buckets: `attachments` bucket for file uploads
  - Features: Presigned URLs for upload/download

**Caching:**
- Not currently implemented (none detected)

## Authentication & Identity

**Auth Provider:**
- Custom JWT-based authentication
  - Implementation: `python-jose` for JWT encoding/decoding
  - Algorithm: HS256
  - Token expiry: 1440 minutes (24 hours)
  - Password hashing: Argon2 via `passlib`
  - Token validation: HTTP Bearer scheme
  - Config: `JWT_SECRET_KEY`, `JWT_ALGORITHM`, `JWT_EXPIRE_MINUTES`

## Messaging & Event Handling

**Message Broker:**
- RabbitMQ 3 (management alpine variant)
  - Connection: `amqp://guest:guest@rabbitmq:5672//`
  - Protocol: AMQP via `aio-pika`
  - Used by: Celery for task queue
  - Management UI: Port 15672

**Task Queue:**
- Celery 5.3+
  - Broker: RabbitMQ
  - Backend: Results backend (database)
  - Tasks: Email sending, maintenance scheduling, work order events

## Email Services

**SMTP Provider:**
- Gmail SMTP (smtp.gmail.com)
  - Port: 587 (TLS)
  - Auth: Username/password
  - Environment: `SMTP_SERVER`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`
  - Features: HTML email templates, registration notifications, approval workflows

## Frontend-Backend Communication

**API Communication:**
- REST API via Axios
- WebSocket support via `websockets` package
- Proxy configuration in Vite for development

**Authentication Flow:**
- JWT tokens stored client-side
- Bearer token in Authorization header
- Supabase client available for potential auth integration

## Monitoring & Observability

**Logging:**
- Python logging module
- File output: `logs/app_YYYYMMDD_HHMMSS.log`
- Console output: StreamHandler
- Log levels: DEBUG, INFO, WARNING, ERROR

**Health Checks:**
- Backend: `/health`, `/api/v1/health` endpoints
- Database: PostgreSQL health check
- Container health checks in docker-compose

## CI/CD & Deployment

**Container Platform:**
- Docker and Docker Compose
- Services: postgres, rabbitmq, minio, pgadmin, backend, celery_worker, celery_beat, frontend

**Deployment Targets:**
- Local development (docker-compose)
- AWS Lambda support via Mangum adapter

## Environment Configuration

**Required Environment Variables:**

| Variable | Purpose | Example |
|----------|---------|---------|
| `DATABASE_URL` | PostgreSQL connection | `postgresql+asyncpg://...` |
| `JWT_SECRET_KEY` | Auth signing key | (secret) |
| `SMTP_*` | Email configuration | Gmail credentials |
| `CELERY_BROKER_URL` | RabbitMQ connection | `amqp://...` |
| `OSS_*` | Object storage | MinIO credentials |
| `STRIPE_SECRET_KEY` | Payment processing | (secret) |
| `APP_AI_BASE_URL` | AI service endpoint | (URL) |
| `APP_AI_KEY` | AI service API key | (secret) |

**Secrets Location:**
- Development: `.env` file (not committed to git)
- Production: Docker environment variables or secrets management

## Webhooks & Callbacks

**Incoming:**
- Not currently detected (no webhook endpoints)

**Outgoing:**
- Stripe checkout completion redirects
- Frontend callback URLs for embedded payments

---

*Integration audit: 2026-03-03*
