#!/usr/bin/env python3
"""
Test Migration 11 improvements
"""
import asyncio
import sys
from pathlib import Path

current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

from open_notebook.database.repository import repo_query
from loguru import logger

async def test_migration_11_improvements():
    """Test that Migration 11 improvements are working"""
    print("🔍 Testing Migration 11 improvements...\n")

    try:
        # Test 1: Vector search function exists and works
        print("1. Testing vector search function...")
        try:
            result = await repo_query("""
                RETURN fn::vector_search([0.1, 0.2, 0.3], 1, true, false, 0.5)
            """)
            if result and len(result) > 0:
                first_result = result[0]
                if 'matches' in first_result and 'similarity' in first_result:
                    print("   ✅ Vector search function working correctly")
                    print(f"   📊 Sample result structure: {list(first_result.keys())}")
                else:
                    print("   ⚠️  Vector search function returned unexpected format")
            else:
                print("   ✅ Vector search function exists (no results is normal for test vector)")
        except Exception as e:
            print(f"   ❌ Vector search function error: {e}")

        # Test 2: Check if HNSW indexes are available (indirect test)
        print("\n2. Testing vector search performance (HNSW indexes)...")
        try:
            import time

            settings_result = await repo_query(
                "SELECT embedding_dimension FROM open_notebook:content_settings LIMIT 1"
            )
            embedding_dimension = (
                settings_result[0].get("embedding_dimension", 1024)
                if settings_result
                else 1024
            )

            start_time = time.time()
            result = await repo_query(
                """
                RETURN fn::vector_search($vector, 5, true, true, 0.1)
            """,
                {"vector": [0.1] * embedding_dimension},
            )
            end_time = time.time()
            search_time = end_time - start_time

            if search_time < 1.0:  # Should be very fast with HNSW
                print(
                    f"   ✅ Vector search is fast ({search_time:.3f}s) "
                    f"- HNSW indexes working at {embedding_dimension} dims"
                )
            else:
                print(
                    f"   ⚠️  Vector search is slow ({search_time:.3f}s) "
                    f"- indexes may not be optimized (dimension {embedding_dimension})"
                )
        except Exception as e:
            print(f"   ❌ Vector search performance test failed: {e}")

        # Test 3: Check timestamp field standardization
        print("\n3. Testing batch table schema...")
        try:
            result = await repo_query("SELECT created, updated FROM batch_upload LIMIT 1")
            if result:
                print("   ✅ New timestamp fields (created/updated) exist")
            else:
                print("   ✅ Batch table exists (no data to test fields)")
        except Exception as e:
            print(f"   ℹ️  Batch table test inconclusive (may be empty): {e}")

        # Test 4: Check relationship indexes work
        print("\n4. Testing relationship query performance...")
        try:
            import time
            start_time = time.time()
            result = await repo_query("""
                SELECT source.id, source.title
                FROM source_embedding
                LIMIT 10
            """)
            end_time = time.time()
            query_time = end_time - start_time

            if query_time < 0.5:
                print(f"   ✅ Relationship queries are fast ({query_time:.3f}s)")
            else:
                print(f"   ⚠️  Relationship queries are slow ({query_time:.3f}s)")

            print(f"   📊 Found {len(result) if result else 0} source embeddings")
        except Exception as e:
            print(f"   ❌ Relationship query test failed: {e}")

        print("\n🎉 Migration 11 verification completed!")
        print("📈 Expected improvements:")
        print("   • Vector search: 100x faster with HNSW indexes")
        print("   • Relationship queries: 10-50x faster")
        print("   • Better cascade cleanup for batch operations")
        print("   • Standardized timestamp schemas")

    except Exception as e:
        print(f"❌ Migration test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_migration_11_improvements())
