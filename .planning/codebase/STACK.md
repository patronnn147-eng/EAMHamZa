# Technology Stack

**Analysis Date:** 2026-03-03

## Languages

**Primary:**
- Python 3.13+ - Backend API, services, ML pipeline
- TypeScript 5.5.3 - Frontend web application
- JavaScript - Frontend configuration

**Secondary:**
- HTML/CSS - Frontend templates and styles

## Runtime

**Backend Environment:**
- Python - Running on Uvicorn ASGI server
- Supports AWS Lambda deployment via Mangum adapter

**Frontend Environment:**
- Node.js - Vite development server and build tool
- Package Manager: pnpm 8.10.0

**Database:**
- PostgreSQL 15 - Primary database (asyncpg async driver)
- SQLite (development) - aiosqlite for local development

## Frameworks

**Backend:**
- FastAPI 0.110.0+ - Web framework for building APIs
- Pydantic 2.5.0+ - Data validation and settings management
- SQLAlchemy 2.0.0+ - ORM (async mode)
- Alembic 1.13.0+ - Database migrations

**Task Queue:**
- Celery 5.3.0+ - Distributed task queue
- RabbitMQ 3 - Message broker for Celery

**Frontend:**
- React 19.1.1 - UI library
- Vite 5.4.1 - Build tool and dev server
- Tailwind CSS 3.4.11 - CSS framework
- shadcn/ui - Component library (Radix UI based)
- React Router DOM 6.26.2 - Client-side routing

**Testing:**
- pytest 8.4.1 - Backend testing framework
- pytest-asyncio 1.1.0 - Async test support
- httpx 0.27.0 - HTTP client for testing

**ML Pipeline:**
- scikit-learn 1.3.0 - Machine learning
- pandas 2.0.0+ - Data manipulation
- numpy 1.24.0+ - Numerical computing
- imbalanced-learn 0.11.0 - Handling imbalanced datasets

## Key Dependencies

**Backend Critical:**
- `fastapi` - API framework
- `uvicorn[standard]` - ASGI server
- `sqlalchemy` + `asyncpg` - Database ORM
- `python-jose[cryptography]` - JWT token handling
- `passlib[bcrypt,argon2]` - Password hashing

**Frontend Critical:**
- `react` + `react-dom` - UI framework
- `@radix-ui/*` - Accessible UI components
- `axios` - HTTP client
- `@tanstack/react-query` - Server state management
- `zustand` - Client state management
- `react-hook-form` + `zod` - Form handling and validation
- `recharts` - Data visualization
- `lucide-react` - Icons

**Infrastructure:**
- `minio` 7.2.0+ - S3-compatible object storage
- `aio-pika` 9.3.0+ - Async RabbitMQ client
- `stripe` 12.0.0+ - Payment processing
- `openai` 1.0.0+ - AI service integration
- `mangum` 0.19.0 - AWS Lambda adapter

## Configuration

**Environment:**
- Uses `.env` files for local development
- Pydantic Settings for configuration management
- Dynamic environment variable reading via `Settings` class

**Key Config Files:**
- `app/backend/core/config.py` - Main backend configuration
- `app/frontend/vite.config.ts` - Vite build configuration
- `app/frontend/tsconfig.json` - TypeScript configuration
- `docker-compose.yml` - Container orchestration

**Environment Variables:**
- `DATABASE_URL` - PostgreSQL connection string
- `JWT_SECRET_KEY` - Authentication secret
- `CELERY_BROKER_URL` - RabbitMQ connection
- `OSS_SERVICE_URL`, `OSS_API_KEY`, `OSS_SECRET_KEY` - Object storage
- `SMTP_*` - Email configuration
- `STRIPE_SECRET_KEY` - Payment processing

## Platform Requirements

**Development:**
- Python 3.13+
- Node.js (pnpm 8.10.0)
- PostgreSQL 15 (or SQLite for dev)
- RabbitMQ (for async tasks)

**Production:**
- Docker and Docker Compose for containerization
- PostgreSQL 15 database
- RabbitMQ message broker
- MinIO or S3-compatible storage

---

*Stack analysis: 2026-03-03*
