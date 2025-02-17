import copy
from abc import ABC, abstractmethod
from asyncio import Lock
from typing import Dict, List, Optional

import structlog

from codegate.clients.clients import ClientType
from codegate.db import models as db_models
from codegate.extract_snippets.body_extractor import BodyCodeSnippetExtractorError
from codegate.extract_snippets.factory import BodyCodeExtractorFactory
from codegate.muxing import models as mux_models

logger = structlog.get_logger("codegate")

_muxrules_sgtn = None

_singleton_lock = Lock()


async def get_muxing_rules_registry():
    """Returns a singleton instance of the muxing rules registry."""

    global _muxrules_sgtn

    if _muxrules_sgtn is None:
        async with _singleton_lock:
            if _muxrules_sgtn is None:
                _muxrules_sgtn = MuxingRulesinWorkspaces()

    return _muxrules_sgtn


class ModelRoute:
    """A route for a model."""

    def __init__(
        self,
        model: db_models.ProviderModel,
        endpoint: db_models.ProviderEndpoint,
        auth_material: db_models.ProviderAuthMaterial,
    ):
        self.model = model
        self.endpoint = endpoint
        self.auth_material = auth_material


class MuxingRuleMatcher(ABC):
    """Base class for matching muxing rules."""

    def __init__(self, route: ModelRoute, matcher_blob: str):
        self._route = route
        self._matcher_blob = matcher_blob

    @abstractmethod
    def match(self, thing_to_match: mux_models.ThingToMatchMux) -> bool:
        """Return True if the rule matches the thing_to_match."""
        pass

    def destination(self) -> ModelRoute:
        """Return the destination of the rule."""

        return self._route


class MuxingMatcherFactory:
    """Factory for creating muxing matchers."""

    @staticmethod
    def create(mux_rule: db_models.MuxRule, route: ModelRoute) -> MuxingRuleMatcher:
        """Create a muxing matcher for the given endpoint and model."""

        factory: Dict[mux_models.MuxMatcherType, MuxingRuleMatcher] = {
            mux_models.MuxMatcherType.catch_all: CatchAllMuxingRuleMatcher,
            mux_models.MuxMatcherType.filename_match: FileMuxingRuleMatcher,
            mux_models.MuxMatcherType.request_type_match: RequestTypeMuxingRuleMatcher,
        }

        try:
            # Initialize the MuxingRuleMatcher
            return factory[mux_rule.matcher_type](route, mux_rule.matcher_blob)
        except KeyError:
            raise ValueError(f"Unknown matcher type: {mux_rule.matcher_type}")


class CatchAllMuxingRuleMatcher(MuxingRuleMatcher):
    """A catch all muxing rule matcher."""

    def match(self, thing_to_match: mux_models.ThingToMatchMux) -> bool:
        logger.info("Catch all rule matched")
        return True


class FileMuxingRuleMatcher(MuxingRuleMatcher):
    """A file muxing rule matcher."""

    def _extract_request_filenames(self, detected_client: ClientType, data: dict) -> set[str]:
        """
        Extract filenames from the request data.
        """
        try:
            body_extractor = BodyCodeExtractorFactory.create_snippet_extractor(detected_client)
            return body_extractor.extract_unique_filenames(data)
        except BodyCodeSnippetExtractorError as e:
            logger.error(f"Error extracting filenames from request: {e}")
            return set()

    def match(self, thing_to_match: mux_models.ThingToMatchMux) -> bool:
        """
        Retun True if there is a filename in the request that matches the matcher_blob.
        The matcher_blob is either an extension (e.g. .py) or a filename (e.g. main.py).
        """
        # If there is no matcher_blob, we don't match
        if not self._matcher_blob:
            return False
        filenames_to_match = self._extract_request_filenames(
            thing_to_match.client_type, thing_to_match.body
        )
        is_filename_match = any(self._matcher_blob in filename for filename in filenames_to_match)
        if is_filename_match:
            logger.info(
                "Filename rule matched", filenames=filenames_to_match, matcher=self._matcher_blob
            )
        return is_filename_match


class RequestTypeMuxingRuleMatcher(MuxingRuleMatcher):
    """A catch all muxing rule matcher."""

    def match(self, thing_to_match: mux_models.ThingToMatchMux) -> bool:
        """
        Return True if the request type matches the matcher_blob.
        The matcher_blob is either "fim" or "chat".
        """
        # If there is no matcher_blob, we don't match
        if not self._matcher_blob:
            return False
        incoming_request_type = "fim" if thing_to_match.is_fim_request else "chat"
        is_request_type_match = self._matcher_blob == incoming_request_type
        if is_request_type_match:
            logger.info(
                "Request type rule matched",
                matcher=self._matcher_blob,
                request_type=incoming_request_type,
            )
        return is_request_type_match


class MuxingRulesinWorkspaces:
    """A thread safe dictionary to store the muxing rules in workspaces."""

    def __init__(self) -> None:
        super().__init__()
        self._lock = Lock()
        self._active_workspace = ""
        self._ws_rules = {}

    async def get_ws_rules(self, workspace_name: str) -> List[MuxingRuleMatcher]:
        """Get the rules for the given workspace."""
        async with self._lock:
            return copy.deepcopy(self._ws_rules.get(workspace_name, []))

    async def set_ws_rules(self, workspace_name: str, rules: List[MuxingRuleMatcher]) -> None:
        """Set the rules for the given workspace."""
        async with self._lock:
            self._ws_rules[workspace_name] = rules

    async def delete_ws_rules(self, workspace_name: str) -> None:
        """Delete the rules for the given workspace."""
        async with self._lock:
            del self._ws_rules[workspace_name]

    async def set_active_workspace(self, workspace_name: str) -> None:
        """Set the active workspace."""
        self._active_workspace = workspace_name

    async def get_registries(self) -> List[str]:
        """Get the list of workspaces."""
        async with self._lock:
            return list(self._ws_rules.keys())

    async def get_match_for_active_workspace(
        self, thing_to_match: mux_models.ThingToMatchMux
    ) -> Optional[ModelRoute]:
        """Get the first match for the given thing_to_match."""

        # We iterate over all the rules and return the first match
        # Since we already do a deepcopy in __getitem__, we don't need to lock here
        try:
            rules = await self.get_ws_rules(self._active_workspace)
            for rule in rules:
                if rule.match(thing_to_match):
                    return rule.destination()
            return None
        except KeyError:
            raise RuntimeError("No rules found for the active workspace")
