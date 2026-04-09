import asyncio
from core.database import DatabaseManager
from sqlalchemy import text

async def check_zone_travail():
    db_manager = DatabaseManager()
    await db_manager.ensure_initialized()
    
    async with db_manager.async_session_maker() as session:
        result = await session.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name = 'plannings' AND column_name = 'zone_travail'"))
        columns = result.fetchall()
        print(f'Columns found: {columns}')
        
        if columns:
            print('✅ zone_travail column exists in plannings table')
            
            # Check some sample data
            sample_result = await session.execute(text('SELECT id, identifiant_planning, zone_travail FROM plannings LIMIT 5'))
            samples = sample_result.fetchall()
            print(f'Sample data: {samples}')
        else:
            print('❌ zone_travail column NOT found in plannings table')

if __name__ == "__main__":
    asyncio.run(check_zone_travail())
