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

# Run migrations
echo "🔧 Running database migrations..."
python migrations/fix_schema.py
python migrations/add_priorite_to_notifications.py
python migrations/add_titre_to_ordres_travail.py
python migrations/add_shift_type_to_utilisateurs.py
python migrations/add_zones_to_machines.py

echo "🎉 Starting FastAPI application..."
exec uvicorn main:app --host 0.0.0.0 --port 8000