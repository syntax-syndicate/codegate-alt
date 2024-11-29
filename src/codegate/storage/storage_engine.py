from codegate.codegate_logging import setup_logging
from codegate.inference.inference_engine import LlamaCppInferenceEngine
from weaviate.classes.config import DataType
from weaviate.classes.query import MetadataQuery
import weaviate


schema_config = [
    {
        "name": "Package",
        "properties": [
            {"name": "name", "data_type": DataType.TEXT},
            {"name": "type", "data_type": DataType.TEXT},
            {"name": "status", "data_type": DataType.TEXT},
            {"name": "description", "data_type": DataType.TEXT},
        ]
    },
]


class StorageEngine:
    def get_client(self, data_path):
        try:
            client = weaviate.WeaviateClient(
                embedded_options=weaviate.EmbeddedOptions(
                    persistence_data_path=data_path
                ),
            )
            return client
        except Exception as e:
            self.__logger.error(f"Error during client creation: {str(e)}")
            return None

    def __init__(self, data_path='./weaviate_data'):
        self.__logger = setup_logging()
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
            finally:
                weaviate_client.close()
        else:
            self.__logger.error("Could not find client, skipping schema setup.")

    def setup_schema(self, client):
        for class_config in self.schema_config:
            if not client.collections.exists(class_config['name']):
                client.collections.create(class_config['name'],
                                          properties=class_config['properties'])
                self.__logger.info(
                    f"Weaviate schema for class {class_config['name']} setup complete.")

    async def search(self, query: str, limit=5, distance=0.3) -> list[object]:
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
            self.__logger.error("Could not find client, not returning results.")
            return []

        try:
            weaviate_client.connect()
            collection = weaviate_client.collections.get("Package")
            response = collection.query.near_vector(
                query_vector[0], limit=limit, distance=distance,
                return_metadata=MetadataQuery(distance=True))

            weaviate_client.close()
            if not response:
                return []
            return response.objects

        except Exception as e:
            self.__logger.error(f"Error during search: {str(e)}")
            return []
        finally:
            weaviate_client.close()
