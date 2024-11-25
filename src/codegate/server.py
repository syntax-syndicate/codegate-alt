from fastapi import APIRouter, FastAPI

from codegate import __description__, __version__
from codegate.providers.anthropic.provider import AnthropicProvider
from codegate.providers.llamacpp.provider import LlamaCppProvider
from codegate.providers.openai.provider import OpenAIProvider
from codegate.providers.registry import ProviderRegistry


def init_app() -> FastAPI:
    app = FastAPI(
        title="CodeGate",
        description=__description__,
        version=__version__,
    )

    # Create provider registry
    registry = ProviderRegistry(app)

    # Register all known providers
    registry.add_provider("openai", OpenAIProvider())
    registry.add_provider("anthropic", AnthropicProvider())
    registry.add_provider("llamacpp", LlamaCppProvider())

    # Create and add system routes
    system_router = APIRouter(tags=["System"])  # Tags group endpoints in the docs

    @system_router.get("/health")
    async def health_check():
        return {"status": "healthy"}

    # Include the router in the app - this exposes the health check endpoint
    app.include_router(system_router)

    return app
