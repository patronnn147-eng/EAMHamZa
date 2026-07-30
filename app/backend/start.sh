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

# Bootstrap has two distinct cases, distinguished by whether any *model*
# tables exist yet (not just alembic_version):
#
#  - Genuinely empty DB (new Postgres volume, e.g. first deploy to a new
#    VM): no migration creates the base tables — they only ever come from
#    SQLAlchemy's Base.metadata.create_all(), which runs inside the FastAPI
#    app's lifespan startup, i.e. AFTER this script's `alembic upgrade head`
#    (uvicorn starts last, via `exec`, below). Stamping to "add_requested_by"
#    here and then running incremental ALTER-TABLE migrations against tables
#    that don't exist yet crashes the container on boot. Fix: build the
#    schema via create_all() right here (matches current models = head), then
#    stamp straight to "head" — no incremental migrations to run afterward.
#  - Pre-existing DB created by create_all() in an earlier deploy, before
#    Alembic tracking was introduced: tables already exist but alembic_version
#    doesn't. Stamp to "add_requested_by" (the bootstrap point) so only
#    genuinely new migrations after that point run.
#
# Both branches run ONCE — subsequent startups skip straight to `alembic
# upgrade head` because alembic_version is already populated.
python - <<'PY'
import os
import asyncio
import asyncpg

async def db_state():
    url = os.getenv("DATABASE_URL", "").replace("postgresql+asyncpg://", "postgresql://")
    conn = await asyncpg.connect(url, timeout=5)
    try:
        alembic_version_row = await conn.fetchval(
            "SELECT COUNT(*) FROM information_schema.tables "
            "WHERE table_name = 'alembic_version'"
        )
        if alembic_version_row > 0:
            version = await conn.fetchval("SELECT version_num FROM alembic_version LIMIT 1")
            if version is not None:
                return "tracked"
        # No tracked revision — check whether any model tables exist at all.
        other_tables = await conn.fetchval(
            "SELECT COUNT(*) FROM information_schema.tables "
            "WHERE table_schema = 'public' AND table_name != 'alembic_version'"
        )
        return "empty" if other_tables == 0 else "legacy"
    finally:
        await conn.close()

if __name__ == "__main__":
    state = asyncio.run(db_state())
    if state == "empty":
        print("Empty database — building schema via create_all() and stamping head...")
        import subprocess
        subprocess.run(
            ["python", "-c", "import asyncio; from services.database import initialize_database; asyncio.run(initialize_database())"],
            check=True,
        )
        subprocess.run(["alembic", "stamp", "head"], check=True)
        print("Schema created and stamped at head.")
    elif state == "legacy":
        print("Existing tables with no Alembic tracking — stamping bootstrap revision...")
        import subprocess
        subprocess.run(["alembic", "stamp", "add_requested_by"], check=True)
        print("Bootstrap stamp applied.")
    else:
        print("Alembic version exists — skipping bootstrap.")
PY

alembic upgrade head
echo "Migrations applied!"

echo "Starting FastAPI application..."
exec uvicorn main:app --host 0.0.0.0 --port 8000 --reload
