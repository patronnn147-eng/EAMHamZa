#!/usr/bin/env python3
"""
Database migration script to fix schema issues
Run this script to ensure all database fields are properly set up
"""

import asyncio
import os

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

async def run_migrations():
    """Run all necessary database migrations"""

    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL is not set")

    engine = create_async_engine(database_url, echo=False)

    try:
        async with engine.begin() as conn:
            print("🔄 Starting database migrations...")
            
            # Fix notifications table - ensure titre column exists and has proper default
            print("📝 Fixing notifications table...")
            try:
                await conn.execute(text("""
                    ALTER TABLE notifications 
                    ALTER COLUMN titre SET DEFAULT 'Planning Assignment'
                """))
                print("   ✅ Set default value for titre column")
            except Exception as e:
                print(f"   ⚠️  titre column issue: {e}")
                try:
                    await conn.execute(text("""
                        ALTER TABLE notifications 
                        ADD COLUMN IF NOT EXISTS titre VARCHAR(255) DEFAULT 'Planning Assignment'
                    """))
                    print("   ✅ Added titre column with default")
                except Exception as e2:
                    print(f"   ❌ Could not add titre column: {e2}")
            
            # Fix utilisateurs table - ensure status column exists and is proper enum
            print("👥 Fixing utilisateurs table...")
            try:
                await conn.execute(text("""
                    DO $$
                    BEGIN
                        IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'userstatus') THEN
                            CREATE TYPE userstatus AS ENUM('PENDING', 'APPROVED', 'REJECTED');
                        END IF;
                    END $$;
                """))
                
                await conn.execute(text("""
                    ALTER TABLE utilisateurs 
                    ALTER COLUMN status TYPE userstatus USING status::userstatus
                """))
                print("   ✅ Fixed status column type")
            except Exception as e:
                print(f"   ⚠️  Status column issue: {e}")
            
            # Ensure created_at and updated_at columns exist
            print("📅 Fixing timestamp columns...")
            try:
                await conn.execute(text("""
                    ALTER TABLE utilisateurs 
                    ADD COLUMN IF NOT EXISTS created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                """))
                print("   ✅ Added timestamp columns")
            except Exception as e:
                print(f"   ⚠️  Timestamp columns issue: {e}")
            
            # Fix plannings table - ensure enum types exist
            print("📋 Fixing plannings table...")
            try:
                await conn.execute(text("""
                    DO $$
                    BEGIN
                        IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'planningtype') THEN
                            CREATE TYPE planningtype AS ENUM('MAINTENANCE', 'SHIFT');
                        END IF;
                    END $$;
                """))
                
                await conn.execute(text("""
                    DO $$
                    BEGIN
                        IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'shifttype') THEN
                            CREATE TYPE shifttype AS ENUM('MORNING', 'AFTERNOON', 'NIGHT');
                        END IF;
                    END $$;
                """))
                print("   ✅ Created enum types")
            except Exception as e:
                print(f"   ⚠️  Enum types issue: {e}")

            print("✅ All migrations completed successfully!")

    finally:
        await engine.dispose()

if __name__ == "__main__":
    print("🚀 Running database migration script...")
    asyncio.run(run_migrations())
    print("🎉 Migration script completed!")
