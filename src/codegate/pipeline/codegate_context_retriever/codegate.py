import json
import re

import structlog
from litellm import ChatCompletionRequest

from codegate.pipeline.base import (
    AlertSeverity,
    PipelineContext,
    PipelineResult,
    PipelineStep,
)
from codegate.pipeline.extract_snippets.extract_snippets import extract_snippets
from codegate.storage.storage_engine import StorageEngine
from codegate.utils.package_extractor import PackageExtractor
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

    def generate_context_str(self, objects: list[object], context: PipelineContext) -> str:
        context_str = ""
        matched_packages = []
        for obj in objects:
            # The object is already a dictionary with 'properties'
            package_obj = obj["properties"]
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
                "Found matching packages in sqlite-vec database", matched_packages=matched_packages
            )
        return context_str

    async def process(
        self, request: ChatCompletionRequest, context: PipelineContext
    ) -> PipelineResult:
        """
        Use RAG DB to add context to the user request
        """
        # Get the latest user messages
        user_messages = self.get_latest_user_messages(request)

        # Nothing to do if the user_messages string is empty
        if len(user_messages) == 0:
            return PipelineResult(request=request)

        # Create storage engine object
        storage_engine = StorageEngine()

        # Extract any code snippets
        snippets = extract_snippets(user_messages)

        bad_snippet_packages = []
        if len(snippets) > 0:
            # Collect all packages referenced in the snippets
            snippet_packages = []
            for snippet in snippets:
                snippet_packages.extend(
                    PackageExtractor.extract_packages(snippet.code, snippet.language)
                )
            logger.info(f"Found {len(snippet_packages)} packages in code snippets.")

            # Find bad packages in the snippets
            bad_snippet_packages = await storage_engine.search(
                language=snippets[0].language, packages=snippet_packages
            )
            logger.info(f"Found {len(bad_snippet_packages)} bad packages in code snippets.")

        # Remove code snippets from the user messages and search for bad packages
        # in the rest of the user query/messsages
        user_messages = re.sub(r"```.*?```", "", user_messages, flags=re.DOTALL)

        # extract query from <task> if needed
        task_match = re.search(r"<task>(.*?)</task>", user_messages, re.DOTALL)
        if task_match:
            # Extract content inside <task> tags
            user_messages = task_match.group(1).strip()
        
        # Vector search to find bad packages
        bad_packages = await storage_engine.search(query=user_messages, distance=0.5, limit=100)

        # All bad packages
        all_bad_packages = bad_snippet_packages + bad_packages

        logger.info(f"Adding {len(all_bad_packages)} bad packages to the context.")

        # Generate context string using the searched objects
        context_str = "CodeGate did not find any malicious or archived packages."

        # Nothing to do if no bad packages are found
        if len(all_bad_packages) == 0:
            return PipelineResult(request=request, context=context)
        else:
            # Add context for bad packages
            context_str = self.generate_context_str(all_bad_packages, context)
            context.bad_packages_found = True

            last_user_idx = self.get_last_user_message_idx(request)

            # Make a copy of the request
            new_request = request.copy()

            # Add the context to the last user message
            # Format: "Context: {context_str} \n Query: {last user message content}"
            message = new_request["messages"][last_user_idx]
            context_msg = f'Context: {context_str} \n\n Query: {message["content"]}'
            message["content"] = context_msg

            logger.debug("Final context message", context_message=context_msg)

            return PipelineResult(request=new_request, context=context)
