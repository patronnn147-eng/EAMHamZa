#!/bin/bash
# Startup script that runs migrations then starts the app
set -e

echo "🚀 Starting application with database migrations..."

# Wait for database to be ready
echo "⏳ Waiting for database..."
python - <<'PY'
import asyncio
import os
import sys
import asyncpg
import time

async def check_db():
    url = os.getenv("DATABASE_URL")
    if not url:
        print("Error: DATABASE_URL environment variable is not set.", file=sys.stderr)
        return False

    # asyncpg expects sync-style URL (postgresql://). Convert if needed.
    pg_url = url.replace("postgresql+asyncpg://", "postgresql://")

    for i in range(30):
        try:
            print(f"Attempting to connect to database (attempt {i+1}/30)...")
            conn = await asyncpg.connect(pg_url, timeout=5)
            await conn.close()
            print("Successfully connected to database.")
            return True
        except Exception as e:
            print(f"Database connection attempt {i+1} failed: {e}")
            await asyncio.sleep(2)
    return False

if __name__ == "__main__":
    if not asyncio.run(check_db()):
        sys.exit(1)
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
    try:
        conn = await asyncpg.connect(pg_url)
        try:
            row = await conn.fetchrow("SELECT to_regclass('public.alembic_version')")
            if row[0] is None:
                sys.exit(2)
            sys.exit(0)
        finally:
            await conn.close()
    except Exception as e:
        print(f"Error checking alembic version: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
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