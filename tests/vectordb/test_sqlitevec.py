import os
import sqlite3
import pytest
from unittest.mock import patch, AsyncMock
from codegate.storage.storage_engine import StorageEngine

@pytest.fixture(scope="module")
def storage_engine():
    # Setup: Create a temporary database for testing
    test_db_path = "./test_sqlite_data"
    os.makedirs(test_db_path, exist_ok=True)
    engine = StorageEngine(data_path=test_db_path)
    yield engine
    # Teardown: Remove the temporary database
    del engine
    os.rmdir(test_db_path)

@pytest.mark.asyncio
async def test_search_by_property(storage_engine):
    # Insert test data
    cursor = storage_engine.conn.cursor()
    cursor.execute("""
        INSERT INTO packages (name, type, status, description)
        VALUES ('test_package', 'npm', 'active', 'A test package')
    """)
    storage_engine.conn.commit()

    # Test search by property
    results = await storage_engine.search_by_property('name', ['test_package'])
    assert len(results) == 1
    assert results[0]['properties']['name'] == 'test_package'
    assert results[0]['properties']['type'] == 'npm'
    assert results[0]['properties']['status'] == 'active'
    assert results[0]['properties']['description'] == 'A test package'

@pytest.mark.asyncio
async def test_search_by_package_names(storage_engine):
    # Insert test data
    cursor = storage_engine.conn.cursor()
    cursor.execute("""
        INSERT INTO packages (name, type, status, description)
        VALUES ('test_package', 'npm', 'active', 'A test package')
    """)
    storage_engine.conn.commit()

    # Test search by package names
    results = await storage_engine.search(packages=['test_package'])
    assert len(results) == 1
    assert results[0]['properties']['name'] == 'test_package'
    assert results[0]['properties']['type'] == 'npm'
    assert results[0]['properties']['status'] == 'active'
    assert results[0]['properties']['description'] == 'A test package'

@pytest.mark.asyncio
async def test_search_by_query(storage_engine):
    # Mock the inference engine to return a fixed embedding
    with patch.object(storage_engine.inference_engine, 'embed', new=AsyncMock(return_value=[[0.1, 0.2, 0.3]])):
        # Insert test data with embedding
        cursor = storage_engine.conn.cursor()
        embedding = bytes([0.1, 0.2, 0.3])
        cursor.execute("""
            INSERT INTO packages (name, type, status, description, embedding)
            VALUES ('test_package', 'npm', 'active', 'A test package', ?)
        """, (embedding,))
        storage_engine.conn.commit()

        # Test search by query
        results = await storage_engine.search(query='test')
        assert len(results) == 1
        assert results[0]['properties']['name'] == 'test_package'
        assert results[0]['properties']['type'] == 'npm'
        assert results[0]['properties']['status'] == 'active'
        assert results[0]['properties']['description'] == 'A test package'
        assert 'metadata' in results[0]
        assert 'distance' in results[0]['metadata']

