import json

import weaviate
from weaviate.classes.config import DataType, Property
from weaviate.embedded import EmbeddedOptions

from utils.embedding_util import generate_embeddings

json_files = [
    "data/archived.jsonl",
    "data/deprecated.jsonl",
    "data/malicious.jsonl",
]


def setup_schema(client):
    if not client.collections.exists("Package"):
        client.collections.create(
            "Package",
            properties=[
                Property(name="name", data_type=DataType.TEXT),
                Property(name="type", data_type=DataType.TEXT),
                Property(name="status", data_type=DataType.TEXT),
                Property(name="description", data_type=DataType.TEXT),
            ],
        )


def generate_vector_string(package):
    vector_str = f"{package['name']}"
    # add description
    package_url = ""
    if package["type"] == "pypi":
        vector_str += " is a Python package available on PyPI"
        package_url = f"https://trustypkg.dev/pypi/{package['name']}"
    elif package["type"] == "npm":
        vector_str += " is a JavaScript package available on NPM"
        package_url = f"https://trustypkg.dev/npm/{package['name']}"
    elif package["type"] == "go":
        vector_str += " is a Go package. "
        package_url = f"https://trustypkg.dev/go/{package['name']}"
    elif package["type"] == "crates":
        vector_str += " is a Rust package available on Crates. "
        package_url = f"https://trustypkg.dev/crates/{package['name']}"
    elif package["type"] == "java":
        vector_str += " is a Java package. "
        package_url = f"https://trustypkg.dev/java/{package['name']}"

    # add extra status
    if package["status"] == "archived":
        vector_str += (
            f". However, this package is found to be archived and no longer "
            f"maintained. For additional information refer to {package_url}"
        )
    elif package["status"] == "deprecated":
        vector_str += (
            f". However, this package is found to be deprecated and no longer "
            f"recommended for use. For additional information refer to {package_url}"
        )
    elif package["status"] == "malicious":
        vector_str += (
            f". However, this package is found to be malicious. "
            f"For additional information refer to {package_url}"
        )
    return vector_str


def add_data(client):
    collection = client.collections.get("Package")

    # read all the data from db, we will only add if there is no data, or is different
    existing_packages = list(collection.iterator())
    packages_dict = {}
    for package in existing_packages:
        key = package.properties["name"] + "/" + package.properties["type"]
        value = {
            "status": package.properties["status"],
            "description": package.properties["description"],
        }
        packages_dict[key] = value

    for json_file in json_files:
        with open(json_file, "r") as f:
            print("Adding data from", json_file)
            with collection.batch.dynamic() as batch:
                for line in f:
                    package = json.loads(line)

                    # now add the status column
                    if "archived" in json_file:
                        package["status"] = "archived"
                    elif "deprecated" in json_file:
                        package["status"] = "deprecated"
                    elif "malicious" in json_file:
                        package["status"] = "malicious"
                    else:
                        package["status"] = "unknown"

                    # check for the existing package and only add if different
                    key = package["name"] + "/" + package["type"]
                    if key in packages_dict:
                        if (
                            packages_dict[key]["status"] == package["status"]
                            and packages_dict[key]["description"]
                            == package["description"]
                        ):
                            print("Package already exists", key)
                            continue

                    # prepare the object for embedding
                    print("Generating data for", key)
                    vector_str = generate_vector_string(package)
                    vector = generate_embeddings(vector_str)

                    batch.add_object(properties=package, vector=vector)


def run_import():
    client = weaviate.WeaviateClient(
        embedded_options=EmbeddedOptions(
            persistence_data_path="./weaviate_data", grpc_port=50052
        ),
    )
    with client:
        client.connect()
        print("is_ready:", client.is_ready())

        setup_schema(client)
        add_data(client)


if __name__ == "__main__":
    run_import()
