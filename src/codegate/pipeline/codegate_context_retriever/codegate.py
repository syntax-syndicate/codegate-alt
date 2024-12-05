import json

import structlog
from litellm import ChatCompletionRequest

from codegate.config import Config
from codegate.inference.inference_engine import LlamaCppInferenceEngine
from codegate.pipeline.base import (
    AlertSeverity,
    PipelineContext,
    PipelineResult,
    PipelineStep,
)
from codegate.storage.storage_engine import StorageEngine
from codegate.utils.utils import generate_vector_string

logger = structlog.get_logger("codegate")


class CodegateContextRetriever(PipelineStep):
    """
    Pipeline step that adds a context message to the completion request when it detects
    the word "codegate" in the user message.
    """

    def __init__(self):
        self.storage_engine = StorageEngine()
        self.inference_engine = LlamaCppInferenceEngine()

    @property
    def name(self) -> str:
        """
        Returns the name of this pipeline step.
        """
        return "codegate-context-retriever"

    async def get_objects_from_search(
        self, search: str, packages: list[str] = None
    ) -> list[object]:
        objects = await self.storage_engine.search(search, distance=0.8, packages=packages)
        return objects

    def generate_context_str(self, objects: list[object]) -> str:
        context_str = ""
        for obj in objects:
            # generate dictionary from object
            package_obj = {
                "name": obj.properties["name"],
                "type": obj.properties["type"],
                "status": obj.properties["status"],
                "description": obj.properties["description"],
            }
            package_str = generate_vector_string(package_obj)
            context_str += package_str + "\n"
        return context_str

    async def __lookup_packages(self, user_query: str):
        # Check which packages are referenced in the user query
        request = {
            "messages": [
                {"role": "system", "content": Config.get_config().prompts.lookup_packages},
                {"role": "user", "content": user_query},
            ],
            "model": "qwen2-1_5b-instruct-q5_k_m",
            "stream": False,
            "response_format": {"type": "json_object"},
            "temperature": 0,
        }

        result = await self.inference_engine.chat(
            f"{Config.get_config().model_base_path}/{request['model']}.gguf",
            n_ctx=Config.get_config().chat_model_n_ctx,
            n_gpu_layers=Config.get_config().chat_model_n_gpu_layers,
            **request,
        )

        result = json.loads(result["choices"][0]["message"]["content"])
        logger.info(f"Packages in user query: {result['packages']}")
        return result["packages"]

    async def process(
        self, request: ChatCompletionRequest, context: PipelineContext
    ) -> PipelineResult:
        """
        Use RAG DB to add context to the user request
        """

        # Get the last user message
        last_user_message = self.get_last_user_message(request)

        # Nothing to do if the last user message is none
        if last_user_message is None:
            return PipelineResult(request=request)

        # Extract packages from the user message
        last_user_message_str, last_user_idx = last_user_message
        packages = await self.__lookup_packages(last_user_message_str)

        # If user message does not reference any packages, then just return
        if len(packages) == 0:
            return PipelineResult(request=request)

        # Look for matches in vector DB using list of packages as filter
        searched_objects = await self.get_objects_from_search(last_user_message_str, packages)

        # If matches are found, add the matched content to context
        if len(searched_objects) > 0:
            # Remove searched objects that are not in packages. This is needed
            # since Weaviate performs substring match in the filter.
            updated_searched_objects = []
            for searched_object in searched_objects:
                if searched_object.properties["name"] in packages:
                    updated_searched_objects.append(searched_object)
            searched_objects = updated_searched_objects

            # Generate context string using the searched objects
            logger.info(f"Adding {len(searched_objects)} packages to the context")
            context_str = self.generate_context_str(searched_objects)

            # Make a copy of the request
            new_request = request.copy()

            # Add the context to the last user message
            # Format: "Context: {context_str} \n Query: {last user message conent}"
            # Handle the two cases: (a) message content is str, (b)message content
            # is list
            message = new_request["messages"][last_user_idx]
            if isinstance(message["content"], str):
                context_msg = f'Context: {context_str} \n\n Query: {message["content"]}'
                context.add_alert(
                    self.name, trigger_string=context_msg, severity_category=AlertSeverity.CRITICAL
                )
                message["content"] = context_msg
            elif isinstance(message["content"], (list, tuple)):
                for item in message["content"]:
                    if isinstance(item, dict) and item.get("type") == "text":
                        context_msg = f'Context: {context_str} \n\n Query: {item["text"]}'
                        context.add_alert(
                            self.name,
                            trigger_string=context_msg,
                            severity_category=AlertSeverity.CRITICAL,
                        )
                        item["text"] = context_msg

                    return PipelineResult(request=new_request, context=context)

        # Fall through
        return PipelineResult(request=request, context=context)
