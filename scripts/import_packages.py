import json
from utils.embedding_util import generate_embeddings
import weaviate
from weaviate.embedded import EmbeddedOptions
from weaviate.classes.config import Property, DataType


json_files = [
    'data/archived.jsonl',
    'data/deprecated.jsonl',
    'data/malicious.jsonl',
]


def setup_schema(client):
    if client.collections.exists("Package"):
        client.collections.delete("Package")
    client.collections.create(
        "Package",
        properties=[
            Property(name="name", data_type=DataType.TEXT),
            Property(name="type", data_type=DataType.TEXT),
            Property(name="status", data_type=DataType.TEXT),
            Property(name="description", data_type=DataType.TEXT),
        ]
    )


def add_data(client):
    collection = client.collections.get("Package")

    for json_file in json_files:
        with open(json_file, 'r') as f:
            print("Adding data from", json_file)
            counter = 0
            with collection.batch.dynamic() as batch:
                for line in f:
                    package = json.loads(line)
                    counter += 1
                    if counter > 100:
                        break

                    # prepare the object for embedding
                    vector_str = f"{package['name']} {package['description']}"
                    vector = generate_embeddings(vector_str)

                    # now add the status column
                    if 'archived' in json_file:
                        package['status'] = 'archived'
                    elif 'deprecated' in json_file:
                        package['status'] = 'deprecated'
                    elif 'malicious' in json_file:
                        package['status'] = 'malicious'
                    else:
                        package['status'] = 'unknown'

                    batch.add_object(properties=package, vector=vector)


def run_import():
    client = weaviate.WeaviateClient(
        embedded_options=EmbeddedOptions(
            persistence_data_path="./weaviate_data"
        ),
    )
    with client:
        client.connect()
        print('is_ready:', client.is_ready())

        setup_schema(client)
        add_data(client)


if __name__ == '__main__':
    run_import()
