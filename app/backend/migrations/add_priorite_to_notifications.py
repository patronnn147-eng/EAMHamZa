#!/usr/bin/env python3
"""
Migration script to add missing 'priorite' column to notifications table
"""
import asyncio
import asyncpg
from sqlalchemy import text
from core.database import get_db_session


async def run_migration():
    """Add priorite column to notifications table"""
    print("🔧 Adding 'priorite' column to notifications table...")
    
    try:
        async with get_db_session() as db:
            # Check if column already exists
            check_column_query = text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'notifications' 
                AND column_name = 'priorite'
            """)
            
            result = await db.execute(check_column_query)
            column_exists = result.fetchone()
            
            if not column_exists:
                # Add the column
                add_column_query = text("""
                    ALTER TABLE notifications 
                    ADD COLUMN priorite VARCHAR(50) NULL
                """)
                
                await db.execute(add_column_query)
                await db.commit()
                print("✅ Added 'priorite' column to notifications table")
            else:
                print("✅ 'priorite' column already exists in notifications table")
                
    except Exception as e:
        print(f"❌ Error adding priorite column: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(run_migration())
