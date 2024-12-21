import json

import structlog
from litellm import ChatCompletionRequest

from codegate.llm_utils.extractor import PackageExtractor
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

    @property
    def name(self) -> str:
        """
        Returns the name of this pipeline step.
        """
        return "codegate-context-retriever"

    async def get_objects_from_db(
        self, ecosystem, packages: list[str] = None
    ) -> list[object]:
        logger.debug(
            "Searching database for packages",
            ecosystem=ecosystem,
            packages=packages
        )
        storage_engine = StorageEngine()
        objects = await storage_engine.search(
            distance=0.8, ecosystem=ecosystem, packages=packages
        )
        logger.debug(
            "Database search results",
            result_count=len(objects),
            results=[obj['properties'] for obj in objects] if objects else None
        )
        return objects

    def generate_context_str(self, objects: list[object], context: PipelineContext) -> str:
        context_str = ""
        matched_packages = []
        for obj in objects:
            # The object is already a dictionary with 'properties'
            package_obj = obj['properties']
            matched_packages.append(f"{package_obj['name']} ({package_obj['type']})")
            # Add one alert for each package found
            context.add_alert(
                self.name,
                trigger_string=json.dumps(package_obj),
                severity_category=AlertSeverity.CRITICAL,
            )
            package_str = generate_vector_string(package_obj)
            context_str += package_str + "\n"

        if matched_packages:
            logger.debug(
                "Found matching packages in sqlite-vec database",
                matched_packages=matched_packages
            )
        return context_str

    async def __lookup_packages(self, user_query: str, context: PipelineContext):
        # Use PackageExtractor to extract packages from the user query
        packages = await PackageExtractor.extract_packages(
            content=user_query,
            provider=context.sensitive.provider,
            model=context.sensitive.model,
            api_key=context.sensitive.api_key,
            base_url=context.sensitive.api_base,
            extra_headers=context.metadata.get("extra_headers", None),
        )

        logger.info(f"Packages in user query: {packages}")
        return packages

    async def __lookup_ecosystem(self, user_query: str, context: PipelineContext):
        # Use PackageExtractor to extract ecosystem from the user query
        ecosystem = await PackageExtractor.extract_ecosystem(
            content=user_query,
            provider=context.sensitive.provider,
            model=context.sensitive.model,
            api_key=context.sensitive.api_key,
            base_url=context.sensitive.api_base,
            extra_headers=context.metadata.get("extra_headers", None),
        )

        logger.debug(
            "Extracted ecosystem from query",
            ecosystem=ecosystem,
            query=user_query
        )
        return ecosystem

    async def process(
        self, request: ChatCompletionRequest, context: PipelineContext
    ) -> PipelineResult:
        """
        Use RAG DB to add context to the user request
        """

        # Get all user messages
        user_messages = self.get_all_user_messages(request)

        # Nothing to do if the user_messages string is empty
        if len(user_messages) == 0:
            return PipelineResult(request=request)

        # Extract packages from the user message
        ecosystem = await self.__lookup_ecosystem(user_messages, context)
        packages = await self.__lookup_packages(user_messages, context)

        logger.debug(
            "Processing request",
            user_messages=user_messages,
            extracted_ecosystem=ecosystem,
            extracted_packages=packages
        )

        context_str = "CodeGate did not find any malicious or archived packages."

        if len(packages) > 0:
            # Look for matches in DB using packages and ecosystem
            searched_objects = await self.get_objects_from_db(ecosystem, packages)

            logger.info(
                f"Found {len(searched_objects)} matches in the database",
                searched_objects=searched_objects,
            )

            # Generate context string using the searched objects
            logger.info(f"Adding {len(searched_objects)} packages to the context")

            if len(searched_objects) > 0:
                context_str = self.generate_context_str(searched_objects, context)

        last_user_idx = self.get_last_user_message_idx(request)

        # Make a copy of the request
        new_request = request.copy()

        # Add the context to the last user message
        # Format: "Context: {context_str} \n Query: {last user message content}"
        message = new_request["messages"][last_user_idx]
        context_msg = f'Context: {context_str} \n\n Query: {message["content"]}'
        message["content"] = context_msg

        logger.debug(
            "Final context message",
            context_message=context_msg
        )

        return PipelineResult(request=new_request, context=context)
