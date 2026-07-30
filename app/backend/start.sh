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
#    VM): the migration chain's true base (db0b16342160_auto_update, down_
#    revision=None) already creates the core tables (OrdresIntervention,
#    utilisateurs, machines, ...) directly via op.create_table — it does NOT
#    depend on SQLAlchemy's create_all(). Some tables (documents/doc_chunks,
#    the pgvector RAG tables) are ONLY ever created this way, by design —
#    they're deliberately kept out of the ORM/Base.metadata so the pgvector
#    extension can be created before the vector column type is needed (see
#    add_pgvector_rag.py). So for an empty DB we must NOT stamp past these
#    migrations — just leave alembic_version untouched and let the normal
#    `alembic upgrade head` below run the entire chain from base. (An
#    earlier version of this script stamped straight to "head" via
#    create_all() here, which skipped the chain entirely and silently left
#    documents/doc_chunks missing — create_all() is unnecessary for a fresh
#    DB and actively wrong for tables it doesn't know about.)
#  - Pre-existing DB created by create_all() in an earlier deploy, before
#    Alembic tracking was introduced: tables already exist but alembic_version
#    doesn't. Stamp to "add_requested_by" (the bootstrap point) so only
#    genuinely new migrations after that point run — replaying the full chain
#    here would fail on the early create_table migrations (tables already
#    exist).
#
# Runs ONCE — subsequent startups skip straight to `alembic upgrade head`
# because alembic_version is already populated.
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
        print("Empty database — will run the full migration chain from base.")
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
