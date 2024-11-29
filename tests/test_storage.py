import pytest
from unittest.mock import Mock, AsyncMock
from codegate.storage.storage_engine import StorageEngine  # Adjust the import according to your project structure


@pytest.fixture
def mock_client():
    client = Mock()
    client.connect = Mock()
    client.is_ready = Mock(return_value=True)
    client.schema.contains = Mock(return_value=False)
    client.schema.create_class = Mock()
    client.collections.get = Mock()
    client.close = Mock()
    return client


@pytest.fixture
def mock_logger():
    logger = Mock()
    return logger


@pytest.fixture
def mock_inference_engine():
    inference_engine = AsyncMock()
    inference_engine.embed = AsyncMock(
        return_value=[0.1, 0.2, 0.3])  # Adjust based on expected vector dimensions
    return inference_engine


@pytest.fixture
def storage_engine(mock_client, mock_logger, mock_inference_engine):
    engine = StorageEngine(data_path='./weaviate_data')
    engine.client = mock_client
    engine.__logger = mock_logger
    engine.inference_engine = mock_inference_engine
    return engine


def test_connect(storage_engine, mock_client):
    storage_engine.connect()
    mock_client.connect.assert_called_once()
    mock_client.is_ready.assert_called_once()


@pytest.mark.asyncio
async def test_search(storage_engine, mock_client):
    query = "test query"
    results = await storage_engine.search(query)
    storage_engine.inference_engine.embed.assert_called_once_with(
        "./models/all-minilm-L6-v2-q5_k_m.gguf", [query])
    assert results is not None  # Further asserts can be based on your application logic


def test_close(storage_engine, mock_client):
    storage_engine.close()
    mock_client.close.assert_called_once()
