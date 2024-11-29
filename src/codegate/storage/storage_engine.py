from codegate.codegate_logging import setup_logging
from codegate.inference.inference_engine import LlamaCppInferenceEngine
from weaviate.classes.config import DataType, Property
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
    def __init__(self, data_path='./weaviate_data'):
        self.client = weaviate.WeaviateClient(
            embedded_options=weaviate.EmbeddedOptions(
                persistence_data_path=data_path
            ),
        )
        self.__logger = setup_logging()
        self.inference_engine = LlamaCppInferenceEngine()
        self.model_path = "./models/all-minilm-L6-v2-q5_k_m.gguf"
        self.schema_config = schema_config
        self.connect()
        self.setup_schema()

    def connect(self):
        self.client.connect()
        if self.client.is_ready():
            self.__logger.info("Weaviate connection established and client is ready.")
        else:
            raise Exception("Weaviate client is not ready.")

    def setup_schema(self):
        for class_config in self.schema_config:
            if not self.client.collections.exists(class_config['name']):
                self.client.collections.create(class_config['name'], properties=class_config['properties'])
                self.__logger.info(f"Weaviate schema for class {class_config['name']} setup complete.")

    async def search(self, query, limit=5, distance=0.1):
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
        try:
            collection = self.client.collections.get("Package")
            response = collection.query.near_vector(query_vector, limit=limit, distance=distance, return_metadata=MetadataQuery(distance=True))
            if not response:
                return []
            return response.objects

        except Exception as e:
            self.__logger.error(f"Error during search: {str(e)}")
            return []

    def close(self):
        self.client.close()
        self.__logger.info("Connection closed.")
