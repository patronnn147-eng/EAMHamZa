from core.database import db_manager
from sqlalchemy import text
import asyncio

async def check_schema():
    async with db_manager.async_session_maker() as session:
        result = await session.execute(text('SELECT column_name, data_type FROM information_schema.columns WHERE table_name = \'utilisateurs\' AND column_name = \'role\''))
        print(result.fetchone())

if __name__ == "__main__":
    asyncio.run(check_schema())
