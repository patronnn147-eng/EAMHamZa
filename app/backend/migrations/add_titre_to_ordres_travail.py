#!/usr/bin/env python3
"""
Migration script to add missing 'titre' column to ordres_travail table
"""
import asyncio
from sqlalchemy import text
from core.database import get_db_session


async def run_migration():
    """Add titre column to ordres_travail table"""
    print("🔧 Adding 'titre' column to ordres_travail table...")
    
    try:
        async with get_db_session() as db:
            # Check if column already exists
            check_column_query = text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'ordres_travail' 
                AND column_name = 'titre'
            """)
            
            result = await db.execute(check_column_query)
            column_exists = result.fetchone()
            
            if not column_exists:
                # Add the column
                add_column_query = text("""
                    ALTER TABLE ordres_travail 
                    ADD COLUMN titre VARCHAR(255) NULL
                """)
                
                await db.execute(add_column_query)
                await db.commit()
                print("✅ Added 'titre' column to ordres_travail table")
            else:
                print("✅ 'titre' column already exists in ordres_travail table")
                
    except Exception as e:
        print(f"❌ Error adding titre column: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(run_migration())
