import asyncio
import os
import asyncpg


async def main():
    url = os.getenv("DATABASE_URL")
    if not url:
        print("DATABASE_URL is not set")
        return

    # asyncpg expects sync-style URL (postgresql://). Convert if needed.
    pg_url = url.replace("postgresql+asyncpg://", "postgresql://")

    try:
        conn = await asyncpg.connect(pg_url)

        print("Columns in OrdresIntervention:")
        rows = await conn.fetch("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'OrdresIntervention'
        """)
        for row in rows:
            print(f"- {row['column_name']}")

        print("\nColumns in OrdresTravail:")
        rows = await conn.fetch("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'OrdresTravail'
        """)
        for row in rows:
            print(f"- {row['column_name']}")

        await conn.close()
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    asyncio.run(main())
