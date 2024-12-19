import asyncio
import json
import os
import re

import requests
import structlog
import yaml
from dotenv import find_dotenv, load_dotenv
from sklearn.metrics.pairwise import cosine_similarity

from codegate.inference.inference_engine import LlamaCppInferenceEngine

logger = structlog.get_logger("codegate")


class CodegateTestRunner:
    def __init__(self):
        self.inference_engine = LlamaCppInferenceEngine()
        self.embedding_model = "codegate_volume/models/all-minilm-L6-v2-q5_k_m.gguf"

    @staticmethod
    def call_codegate(url, headers, data):
        response = None
        try:
            response = requests.post(url, headers=headers, json=data)
        except Exception as e:
            logger.exception("An error occurred: %s", e)
        return response

    @staticmethod
    def parse_response_message(response, streaming=True):
        response_message = ""
        try:
            if streaming:
                for line in response.iter_lines():
                    decoded_line = line.decode("utf-8").strip()
                    if (
                        not decoded_line
                        or decoded_line.startswith("event:")
                        or "message_start" in decoded_line
                    ):
                        continue

                    if "DONE" in decoded_line or "message_stop" in decoded_line:
                        break

                    decoded_line = decoded_line.replace("data:", "")
                    json_line = json.loads(decoded_line)

                    message_content = None
                    if "choices" in json_line:
                        if "delta" in json_line["choices"][0]:
                            message_content = json_line["choices"][0]["delta"].get("content", "")
                        elif "text" in json_line["choices"][0]:
                            message_content = json_line["choices"][0].get("text", "")
                    elif "delta" in json_line:
                        message_content = json_line["delta"].get("text", "")
                    elif "message" in json_line:
                        message_content = json_line["message"].get("content", "")
                    elif "response" in json_line:
                        message_content = json_line.get("response", "")

                    if message_content is not None:
                        response_message += message_content

            else:
                if "choices" in response.json():
                    response_message = response.json()["choices"][0]["message"].get("content", "")
                elif "content" in response.json():
                    response_message = response.json()["content"][0].get("text", "")

        except Exception as e:
            logger.exception("An error occurred: %s", e)

        return response_message

    async def calculate_string_similarity(self, str1, str2):
        vector1 = await self.inference_engine.embed(self.embedding_model, str1)
        vector2 = await self.inference_engine.embed(self.embedding_model, str2)
        similarity = cosine_similarity([vector1], [vector2])
        return similarity[0]

    @staticmethod
    def replace_env_variables(input_string, env):
        """
        Replace occurrences of strings starting with ENV in the input string
        with their corresponding values from the env dictionary.

        Args:
            input_string (str): The string containing patterns starting with ENV.
            env (dict): A dictionary mapping ENV keys to their replacement values.

        Returns:
            str: The modified string with ENV patterns replaced.
        """

        def replacement(match):
            key = match.group(0)  # Full match (e.g., ENV_VLLM_KEY)
            return env.get(key, key)  # Replace with value if key exists, else keep original

        # Match patterns starting with ENV (alphanumeric and underscore after ENV)
        pattern = r"ENV\w*"
        return re.sub(pattern, replacement, input_string)

    async def run_test(self, test, test_headers):
        test_name = test["name"]
        url = test["url"]
        data = json.loads(test["data"])
        streaming = data.get("stream", False)
        response = CodegateTestRunner.call_codegate(url, test_headers, data)
        expected_response = test["expected"]
        try:
            parsed_response = CodegateTestRunner.parse_response_message(
                response, streaming=streaming
            )
            similarity = await self.calculate_string_similarity(parsed_response, expected_response)
            if similarity < 0.8:
                logger.error(f"Test {test_name} failed")
                logger.error(f"Similarity: {similarity}")
                logger.error(f"Response: {parsed_response}")
                logger.error(f"Expected Response: {expected_response}")
            else:
                logger.info(f"Test {test['name']} passed")
        except Exception as e:
            logger.exception("Could not parse response: %s", e)

    async def run_tests(self, testcases_file):
        with open(testcases_file, "r") as f:
            tests = yaml.safe_load(f)

        headers = tests["headers"]
        for _, header_val in headers.items():
            if header_val is None:
                continue
            for key, val in header_val.items():
                header_val[key] = CodegateTestRunner.replace_env_variables(val, os.environ)

        test_count = len(tests["testcases"])

        logger.info(f"Running {test_count} tests")
        for _, test_data in tests["testcases"].items():
            test_headers = headers.get(test_data["provider"], {})
            await self.run_test(test_data, test_headers)


async def main():
    load_dotenv(find_dotenv())
    test_runner = CodegateTestRunner()
    await test_runner.run_tests("./tests/integration/testcases.yaml")


if __name__ == "__main__":
    asyncio.run(main())
