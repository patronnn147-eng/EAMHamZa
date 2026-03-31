import asyncio
import os
import sys
import asyncpg

async def main():
    url = os.getenv("DATABASE_URL")
    if not url:
        print("DATABASE_URL is not set")
        sys.exit(1)
    
    # asyncpg expects sync-style URL (postgresql://). Convert if needed.
    pg_url = url.replace("postgresql+asyncpg://", "postgresql://")
    
    try:
        conn = await asyncpg.connect(pg_url)
        # Update the alembic_version table
        await conn.execute("UPDATE alembic_version SET version_num = 'add_machine_telemetry_columns'")
        print("Successfully updated alembic_version to 'add_machine_telemetry_columns'")
        await conn.close()
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
