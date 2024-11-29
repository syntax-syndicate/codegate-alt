import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from codegate.storage.storage_engine import StorageEngine  # Adjust the import based on your actual path


@pytest.fixture
def mock_weaviate_client():
    client = MagicMock()
    response = MagicMock()
    response.objects = [
        {
            'properties': {
                'name': 'test',
                'type': 'library',
                'status': 'active',
                'description': 'test description'
            }
        }
    ]
    client.collections.get.return_value.query.near_vector.return_value = response
    return client


@pytest.fixture
def mock_inference_engine():
    engine = AsyncMock()
    engine.embed.return_value = [0.1, 0.2, 0.3]  # Adjust based on expected vector dimensions
    return engine


@pytest.mark.asyncio
async def test_search(mock_weaviate_client, mock_inference_engine):
    # Patch the WeaviateClient and LlamaCppInferenceEngine inside the test function
    with patch('weaviate.WeaviateClient', return_value=mock_weaviate_client), \
         patch('codegate.inference.inference_engine.LlamaCppInferenceEngine',
               return_value=mock_inference_engine):

        # Initialize StorageEngine
        storage_engine = StorageEngine(data_path='./weaviate_data')

        # Invoke the search method
        results = await storage_engine.search("test query", 5, 0.3)

        # Assertions to validate the expected behavior
        assert len(results) == 1  # Assert that one result is returned
        assert results[0]['properties']['name'] == 'test'
        mock_weaviate_client.connect.assert_called()
        mock_weaviate_client.close.assert_called()
