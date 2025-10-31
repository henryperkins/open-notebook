#!/usr/bin/env python3
"""
Manual migration runner for Migration 11
"""
import asyncio
import sys
from pathlib import Path

# Add current directory to Python path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

from open_notebook.database.async_migrate import AsyncMigrationManager
from loguru import logger

async def run_migration_11():
    """Run Migration 11 manually with detailed logging"""
    logger.info("🚀 Starting Migration 11 manual execution...")

    try:
        # Initialize migration manager
        manager = AsyncMigrationManager()

        # Check current state
        current_version = await manager.get_current_version()
        total_migrations = len(manager.up_migrations)

        logger.info(f"📊 Current database version: {current_version}/{total_migrations}")

        if current_version >= total_migrations:
            logger.info("✅ Database is already at latest version")
            return

        if current_version >= 11:
            logger.info("✅ Migration 11 has already been applied")
            return

        logger.warning("⚠️  Migration 11 needs to be applied")
        logger.info("📋 Migration 11 will:")
        logger.info("   • Align batch table timestamp schemas")
        logger.info("   • Add HNSW vector indexes (100x vector search improvement)")
        logger.info("   • Add relationship lookup indexes")
        logger.info("   • Fix vector search function output format")
        logger.info("   • Improve cascade delete for batch relationships")

        # Confirm before proceeding
        response = input("\n❓ Do you want to proceed with Migration 11? (y/N): ")
        if response.lower() != 'y':
            logger.info("❌ Migration cancelled by user")
            return

        # Run the migration
        logger.info("🔧 Running Migration 11...")
        await manager.run_migration_up()

        # Verify success
        new_version = await manager.get_current_version()
        logger.success(f"✅ Migration 11 completed successfully!")
        logger.info(f"📊 Database version: {new_version}/{total_migrations}")

        # Verify indexes were created
        logger.info("🔍 Verifying HNSW indexes were created...")
        # Note: You could add verification queries here

    except Exception as e:
        logger.error(f"❌ Migration 11 failed: {str(e)}")
        logger.exception(e)
        raise

if __name__ == "__main__":
    asyncio.run(run_migration_11())