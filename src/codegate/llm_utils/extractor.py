from typing import Dict, List, Optional

import structlog

from codegate.config import Config
from codegate.llm_utils.llmclient import LLMClient
from codegate.storage import StorageEngine

logger = structlog.get_logger("codegate")


class PackageExtractor:
    """
    Utility class to extract package names from code or queries.
    """

    def __init__(self):
        self.storage_engine = StorageEngine()

    @staticmethod
    async def extract_packages(
        content: str,
        provider: str,
        model: str = None,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        extra_headers: Optional[Dict[str, str]] = None,
    ) -> List[str]:
        """Extract package names from the given content."""
        system_prompt = Config.get_config().prompts.lookup_packages

        result = await LLMClient.complete(
            content=content,
            system_prompt=system_prompt,
            provider=provider,
            model=model,
            api_key=api_key,
            base_url=base_url,
            extra_headers=extra_headers,
        )

        # Handle both formats: {"packages": [...]} and direct list [...]
        packages = result if isinstance(result, list) else result.get("packages", [])
        logger.info(f"Extracted packages: {packages}")
        return packages

    @staticmethod
    async def extract_ecosystem(
        content: str,
        provider: str,
        model: str = None,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        extra_headers: Optional[Dict[str, str]] = None,
    ) -> List[str]:
        """Extract ecosystem from the given content."""
        system_prompt = Config.get_config().prompts.lookup_ecosystem

        result = await LLMClient.complete(
            content=content,
            system_prompt=system_prompt,
            provider=provider,
            model=model,
            api_key=api_key,
            base_url=base_url,
            extra_headers=extra_headers,
        )

        ecosystem = result if isinstance(result, str) else result.get("ecosystem")
        if ecosystem:
            ecosystem = ecosystem.lower()
        logger.info(f"Extracted ecosystem: {ecosystem}")
        return ecosystem
