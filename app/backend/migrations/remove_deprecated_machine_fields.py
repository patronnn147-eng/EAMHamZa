#!/usr/bin/env python3
"""
Migration script to remove deprecated fields from machines table
- Remove identifiant_machine (using auto-increment ID instead)
- Remove emplacement (location)
- Remove statut (status)
- Remove type
"""

import asyncio
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.database import db_manager
from sqlalchemy import text
from models.machines import Machines


async def remove_deprecated_fields():
    """Remove deprecated fields from machines table"""
    
    print("Starting migration: Remove deprecated fields from machines table...")
    
    async with db_manager.async_session_maker() as session:
        try:
            # Check if columns exist before dropping them
            result = await session.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'machines'
            """))
            existing_columns = [row[0] for row in result.fetchall()]
            
            # Columns to drop
            columns_to_drop = ['identifiant_machine', 'emplacement', 'statut', 'type']
            
            for column in columns_to_drop:
                if column in existing_columns:
                    print(f"Dropping column: {column}")
                    await session.execute(text(f"ALTER TABLE machines DROP COLUMN {column}"))
                else:
                    print(f"Column {column} does not exist, skipping...")
            
            await session.commit()
            print("✅ Successfully removed deprecated fields from machines table")
            
        except Exception as e:
            await session.rollback()
            print(f"❌ Error removing deprecated fields: {e}")
            raise


async def verify_schema():
    """Verify the updated schema"""
    
    print("\nVerifying updated schema...")
    
    async with db_manager.async_session_maker() as session:
        try:
            result = await session.execute(text("""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns 
                WHERE table_name = 'machines'
                ORDER BY ordinal_position
            """))
            
            columns = result.fetchall()
            print("Current machines table schema:")
            for col in columns:
                print(f"  - {col[0]} ({col[1]}, nullable={col[2]})")
                
        except Exception as e:
            print(f"❌ Error verifying schema: {e}")
            raise


async def main():
    """Main migration function"""
    
    print("=" * 60)
    print("MIGRATION: Remove deprecated fields from machines table")
    print("=" * 60)
    
    try:
        # Initialize database manager
        await db_manager.initialize()
        await remove_deprecated_fields()
        await verify_schema()
        print("\n✅ Migration completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        sys.exit(1)
    finally:
        # Cleanup
        await db_manager.dispose()


if __name__ == "__main__":
    asyncio.run(main())
