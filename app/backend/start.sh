#!/bin/bash
# Startup script that runs migrations then starts the app
set -e

echo "Starting application with database migrations..."

# Wait for database to be ready
echo "Waiting for database..."
python - <<'PY'
import asyncio
import os
import sys
import asyncpg

async def check_db():
    url = os.getenv("DATABASE_URL")
    if not url:
        print("Error: DATABASE_URL environment variable is not set.", file=sys.stderr)
        return False

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

echo "Database is ready!"

# Run Alembic migrations
echo "Running database migrations..."

# Bootstrap: if alembic_version table is absent (fresh DB that was created by
# SQLAlchemy directly without migration tracking), stamp at the last revision
# whose DDL already exists so we only run genuinely new migrations.
# This block runs ONCE — subsequent startups skip it because alembic_version exists.
python - <<'PY'
import os
import asyncio
import asyncpg

async def needs_stamp():
    url = os.getenv("DATABASE_URL", "").replace("postgresql+asyncpg://", "postgresql://")
    conn = await asyncpg.connect(url, timeout=5)
    try:
        row = await conn.fetchval(
            "SELECT COUNT(*) FROM information_schema.tables "
            "WHERE table_name = 'alembic_version'"
        )
        if row == 0:
            return True
        # Table exists — check if it's empty (no tracked revision at all)
        version = await conn.fetchval("SELECT version_num FROM alembic_version LIMIT 1")
        return version is None
    finally:
        await conn.close()

if __name__ == "__main__":
    if asyncio.run(needs_stamp()):
        print("No Alembic version found — stamping bootstrap revision...")
        import subprocess
        subprocess.run(["alembic", "stamp", "add_requested_by"], check=True)
        print("Bootstrap stamp applied.")
    else:
        print("Alembic version exists — skipping bootstrap stamp.")
PY

alembic upgrade head
echo "Migrations applied!"

echo "Starting FastAPI application..."
exec uvicorn main:app --host 0.0.0.0 --port 8000 --reload
