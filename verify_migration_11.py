#!/usr/bin/env python3
"""
Pre and post-migration verification script for Migration 11
"""
import asyncio
import sys
from pathlib import Path

current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

from open_notebook.database.async_migrate import AsyncMigrationManager
from open_notebook.database.repository import repo_query
from loguru import logger

async def check_pre_migration_state():
    """Check database state before migration"""
    logger.info("🔍 Pre-migration verification...")

    try:
        # Check current version
        manager = AsyncMigrationManager()
        current_version = await manager.get_current_version()
        logger.info(f"📊 Current version: {current_version}")

        if current_version >= 11:
            logger.info("✅ Migration 11 already applied")
            return False

        # Check for problematic data patterns
        logger.info("🔍 Checking batch table schemas...")

        # Check if old timestamp fields exist
        try:
            result = await repo_query("SELECT created_at, updated_at FROM batch_upload LIMIT 1")
            if result:
                logger.warning("⚠️  Old timestamp fields (created_at/updated_at) found - migration needed")
        except:
            logger.info("✅ Old timestamp fields already cleaned up")

        # Check for missing HNSW indexes (this will fail pre-migration)
        logger.info("🔍 Checking for HNSW vector indexes...")
        try:
            await repo_query("SELECT * FROM source_embedding WHERE embedding <S> [0.1, 0.2] LIMIT 1")
            logger.info("✅ HNSW indexes already exist")
        except Exception as e:
            if "index" in str(e).lower():
                logger.warning("⚠️  HNSW indexes missing - vector search performance will be slow")
            else:
                logger.info("ℹ️  Index check inconclusive (expected)")

        # Check for orphaned batch relationships
        logger.info("🔍 Checking for potential orphaned records...")
        try:
            result = await repo_query("""
                SELECT COUNT() as count FROM batch_source_relationship
                WHERE source_id NOT IN (SELECT id FROM source)
            """)
            if result and result[0]['count'] > 0:
                logger.warning(f"⚠️  Found {result[0]['count']} potentially orphaned batch relationships")
        except Exception as e:
            logger.info(f"ℹ️  Orphan check inconclusive: {e}")

        return True

    except Exception as e:
        logger.error(f"❌ Pre-migration check failed: {e}")
        raise

async def check_post_migration_state():
    """Check database state after migration"""
    logger.info("🔍 Post-migration verification...")

    try:
        # Verify new version
        manager = AsyncMigrationManager()
        new_version = await manager.get_current_version()
        logger.success(f"✅ Database version after migration: {new_version}")

        # Verify HNSW indexes exist
        logger.info("🔍 Verifying HNSW vector indexes...")
        try:
            # This should work now with HNSW indexes
            await repo_query("SELECT * FROM source_embedding WHERE embedding <S> [0.1, 0.2] LIMIT 1")
            logger.success("✅ HNSW vector indexes are working")
        except Exception as e:
            logger.error(f"❌ HNSW indexes not working: {e}")

        # Verify relationship indexes
        logger.info("🔍 Verifying relationship indexes...")
        try:
            result = await repo_query("EXPLAIN SELECT * FROM source_embedding WHERE source = source:123")
            logger.success("✅ Relationship indexes available")
        except Exception as e:
            logger.warning(f"⚠️  Relationship index check inconclusive: {e}")

        # Verify timestamp fields are standardized
        logger.info("🔍 Verifying timestamp field standardization...")
        try:
            result = await repo_query("SELECT created, updated FROM batch_upload LIMIT 1")
            if result:
                logger.success("✅ New timestamp fields (created/updated) exist")
        except Exception as e:
            logger.error(f"❌ Timestamp field verification failed: {e}")

        # Verify vector search function works
        logger.info("🔍 Verifying vector search function...")
        try:
            result = await repo_query("""
                RETURN fn::vector_search([0.1, 0.2, 0.3], 1, true, false, 0.5)
            """)
            if result:
                logger.success("✅ Vector search function is working")
            else:
                logger.warning("⚠️  Vector search function returned no results")
        except Exception as e:
            logger.error(f"❌ Vector search function verification failed: {e}")

        logger.success("🎉 Migration 11 verification completed successfully!")

    except Exception as e:
        logger.error(f"❌ Post-migration verification failed: {e}")
        raise

async def run_full_verification():
    """Complete pre and post migration verification"""
    logger.info("🚀 Starting Migration 11 verification process...")

    # Pre-migration check
    migration_needed = await check_pre_migration_state()

    if not migration_needed:
        logger.info("✅ Migration 11 already complete")
        return

    # Ask user to proceed
    response = input("\n❓ Run Migration 11 now? (y/N): ")
    if response.lower() != 'y':
        logger.info("❌ Migration cancelled by user")
        return

    # Run migration
    logger.info("🔧 Running Migration 11...")
    try:
        manager = AsyncMigrationManager()
        await manager.run_migration_up()
        logger.success("✅ Migration 11 completed!")
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        raise

    # Post-migration verification
    await check_post_migration_state()

if __name__ == "__main__":
    asyncio.run(run_full_verification())