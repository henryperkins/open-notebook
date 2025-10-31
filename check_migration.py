#!/usr/bin/env python3
"""
Simple migration status checker
"""
import asyncio
import sys
from pathlib import Path

current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

from loguru import logger

async def check_migration():
    """Check migration status"""
    try:
        from open_notebook.database.async_migrate import AsyncMigrationManager

        manager = AsyncMigrationManager()
        current_version = await manager.get_current_version()
        total_migrations = len(manager.up_migrations)

        print(f"📊 Database Version: {current_version}/{total_migrations}")

        if current_version >= 11:
            print("✅ Migration 11 has been applied!")
            print("🚀 Vector search should be 100x faster")
            print("📈 Relationship queries should be 10-50x faster")
        elif current_version == 10:
            print("⚠️  Migration 11 is pending - you should apply it!")
            print("🔧 The system will auto-migrate when API starts")
        else:
            print(f"⚠️  Database is behind - needs {11 - current_version} migrations")

    except Exception as e:
        print(f"❌ Error checking migration: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(check_migration())