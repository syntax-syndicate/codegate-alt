import structlog
import weaviate
import weaviate.classes as wvc
from weaviate.classes.config import DataType
from weaviate.classes.query import MetadataQuery
from weaviate.embedded import EmbeddedOptions

from codegate.config import Config
from codegate.inference.inference_engine import LlamaCppInferenceEngine

logger = structlog.get_logger("codegate")

schema_config = [
    {
        "name": "Package",
        "properties": [
            {"name": "name", "data_type": DataType.TEXT},
            {"name": "type", "data_type": DataType.TEXT},
            {"name": "status", "data_type": DataType.TEXT},
            {"name": "description", "data_type": DataType.TEXT},
        ],
    },
]


class StorageEngine:
    def get_client(self, data_path):
        try:
            # Get current config
            config = Config.get_config()

            # Configure Weaviate logging
            additional_env_vars = {
                # Basic logging configuration
                "LOG_FORMAT": config.log_format.value.lower(),
                "LOG_LEVEL": config.log_level.value.lower(),
                # Disable colored output
                "LOG_FORCE_COLOR": "false",
                # Configure JSON format
                "LOG_JSON_FIELDS": "timestamp, level,message",
                # Configure text format
                "LOG_METHOD": config.log_format.value.lower(),
                "LOG_LEVEL_IN_UPPER": "false",  # Keep level lowercase like codegate format
                # Disable additional fields
                "LOG_GIT_HASH": "false",
                "LOG_VERSION": "false",
                "LOG_BUILD_INFO": "false",
            }

            client = weaviate.WeaviateClient(
                embedded_options=EmbeddedOptions(
                    persistence_data_path=data_path,
                    additional_env_vars=additional_env_vars,
                ),
            )
            return client
        except Exception as e:
            logger.error(f"Error during client creation: {str(e)}")
            return None

    def __init__(self, data_path="./weaviate_data"):
        self.data_path = data_path
        self.inference_engine = LlamaCppInferenceEngine()
        self.model_path = "./models/all-minilm-L6-v2-q5_k_m.gguf"
        self.schema_config = schema_config

        # setup schema for weaviate
        weaviate_client = self.get_client(self.data_path)
        if weaviate_client is not None:
            try:
                weaviate_client.connect()
                self.setup_schema(weaviate_client)
            except Exception as e:
                logger.error(f"Failed to connect or setup schema: {str(e)}")
            finally:
                try:
                    weaviate_client.close()
                except Exception as e:
                    logger.error(f"Failed to close client: {str(e)}")
        else:
            logger.error("Could not find client, skipping schema setup.")

    def setup_schema(self, client):
        for class_config in self.schema_config:
            if not client.collections.exists(class_config["name"]):
                client.collections.create(
                    class_config["name"], properties=class_config["properties"]
                )
            logger.info(f"Weaviate schema for class {class_config['name']} setup complete.")

    async def search(self, query: str, limit=5, distance=0.3, packages=None) -> list[object]:
        """
        Search the 'Package' collection based on a query string.

        Args:
            query (str): The text query for which to search.
            limit (int): The number of results to return.

        Returns:
            list: A list of matching results with their properties and distances.
        """
        # Generate the vector for the query
        query_vector = await self.inference_engine.embed(self.model_path, [query])

        # Perform the vector search
        weaviate_client = self.get_client(self.data_path)
        if weaviate_client is None:
            logger.error("Could not find client, not returning results.")
            return []

        try:
            weaviate_client.connect()
            collection = weaviate_client.collections.get("Package")
            if packages:
                response = collection.query.near_vector(
                    query_vector[0],
                    limit=limit,
                    distance=distance,
                    filters=wvc.query.Filter.by_property("name").contains_any(packages),
                    return_metadata=MetadataQuery(distance=True),
                )
            else:
                response = collection.query.near_vector(
                    query_vector[0],
                    limit=limit,
                    distance=distance,
                    return_metadata=MetadataQuery(distance=True),
                )

            weaviate_client.close()
            if not response:
                return []
            return response.objects

        except Exception as e:
            logger.error(f"Error during search: {str(e)}")
            return []
        finally:
            try:
                weaviate_client.close()
            except Exception as e:
                logger.error(f"Failed to close client: {str(e)}")
