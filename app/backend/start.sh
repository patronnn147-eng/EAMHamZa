#!/bin/bash
# Startup script that runs migrations then starts the app

echo "🚀 Starting application with database migrations..."

# Wait for database to be ready
echo "⏳ Waiting for database..."
python - <<'PY'
import asyncio
import os
import sys

import asyncpg

async def main():
    url = os.getenv("DATABASE_URL")
    if not url:
        print("DATABASE_URL is not set", file=sys.stderr)
        sys.exit(1)

    # asyncpg expects sync-style URL (postgresql://). Convert if needed.
    pg_url = url.replace("postgresql+asyncpg://", "postgresql://")

    for _ in range(60):
        try:
            conn = await asyncpg.connect(pg_url)
            await conn.close()
            sys.exit(0)
        except Exception:
            await asyncio.sleep(2)

    print("Database not ready after timeout", file=sys.stderr)
    sys.exit(1)

asyncio.run(main())
PY

echo "✅ Database is ready!"

# Run Alembic migrations
echo "🔧 Running database migrations (Alembic)..."

# If alembic_version table doesn't exist yet, stamp the current head
python - <<'PY'
import os
import sys
import asyncio
import asyncpg

async def main():
    url = os.getenv("DATABASE_URL")
    if not url:
        print("DATABASE_URL is not set", file=sys.stderr)
        sys.exit(1)
    pg_url = url.replace("postgresql+asyncpg://", "postgresql://")
    conn = await asyncpg.connect(pg_url)
    try:
        row = await conn.fetchrow("SELECT to_regclass('public.alembic_version')")
        print("alembic_version:", row[0])
        if row[0] is None:
            sys.exit(2)
        sys.exit(0)
    finally:
        await conn.close()

asyncio.run(main())
PY

STATUS=$?
if [ "$STATUS" -eq 2 ]; then
  echo "🧷 alembic_version missing: stamping head..."
  alembic stamp head
fi

alembic upgrade head

echo "🎉 Starting FastAPI application..."
exec uvicorn main:app --host 0.0.0.0 --port 8000