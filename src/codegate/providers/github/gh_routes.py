from typing import Dict, List

from pydantic import BaseModel, HttpUrl

# from pydantic_settings import BaseSettings


class ProxyRoute(BaseModel):
    """Pydantic model for proxy route validation"""
    path: str
    target: HttpUrl

    class Config:
        frozen = True

class GitHubRoutes(ProxyRoute):
    """Application settings"""
    HOST: str = "localhost"
    PORT: int = 8990
    CERT_DIR: str = "certs"
    CERT_FILE: str = "certs/server.crt"
    KEY_FILE: str = "certs/server.key"
    LOG_DIR: str = "logs"

    # Proxy routes configuration
    PROXY_ROUTES: List[tuple[str, str]] = [
        ("/github/login", "https://github.com/login"),
        ("/api/github/user", "https://api.github.com"),
        ("/api/github/copilot", "https://api.github.com/copilot_internal"),
        ("/copilot/telemetry", "https://copilot-telemetry.githubusercontent.com"),
        ("/vscode/ab", "https://default.exp-tas.com"),
        ("/copilot/proxy", "https://copilot-proxy.githubusercontent.com"),
        ("/origin-tracker", "https://origin-tracker.githubusercontent.com"),
        ("/copilot/suggestions", "https://githubcopilot.com"),
        ("/copilot/enterprise", "https://enterprise.githubcopilot.com"),
        ("/copilot/business", "https://business.githubcopilot.com"),
        ("/copilot/enterprise", "https://enterprise.githubcopilot.com"),
        ("/chat/completions", "https://api.enterprise.githubcopilot.com"),
        ("/copilot_internal/user", "https://api.github.com"),
        ("/copilot_internal/v2/token", "https://api.github.com"),
        ("/models", "https://api.enterprise.githubcopilot.com"),
        ("/agents", "https://api.enterprise.githubcopilot.com"),
        ("/_ping", "https://api.enterprise.githubcopilot.com"),
        ("/telemety", "https://copilot-telemetry.githubusercontent.com"),
        ("/", "https://github.com"),
        ("/login/oauth/access_token", "https://github.com/login/oauth/access_token"),
        ("/api/copilot", "https://api.github.com/copilot_internal"),
        ("/api/copilot_internal", "https://api.github.com/copilot_internal"),
        ("/v1/completions", "https://copilot-proxy.githubusercontent.com/v1/completions"),
        ("/v1", "https://copilot-proxy.githubusercontent.com/v1"),
        ("v1/engines/copilot-codex/completions", "https://proxy.enterprise.githubcopilot.com/v1/engines/copilot-codex/completions"),
    ]

    # Headers configuration
    PRESERVED_HEADERS: List[str] = [
        'authorization',
        'user-agent',
        'content-type',
        'accept',
        'accept-encoding',
        'connection',
        'x-github-token',
        'github-token',
        'x-request-id',
        'x-github-api-version',
        'openai-organization',
        'openai-intent',
        'openai-model',
        'editor-version',
        'editor-plugin-version',
        'vscode-sessionid',
        'vscode-machineid',
    ]

    REMOVED_HEADERS: List[str] = [
        'proxy-connection',
        'proxy-authenticate',
        'proxy-authorization',
        'connection',
        'keep-alive',
        'transfer-encoding',
        'te',
        'trailer',
        'proxy-authenticate',
        'upgrade',
        'expect',
    ]

    ENDPOINT_HEADERS: Dict[str, Dict[str, str]] = {
        '/v1/engines/copilot-codex/completions': {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'Editor-Version': 'vscode/1.95.3',
            'Editor-Plugin-Version': 'copilot/1.246.0',
            'Openai-Organization': 'github-copilot',
            'Openai-Intent': 'copilot-ghost',
            'User-Agent': 'GithubCopilot/1.246.0',
            'Accept-Encoding': 'gzip, deflate, br',
            'X-Github-Api-Version': '2022-11-28',
            'Host': 'copilot-proxy.githubusercontent.com'
        }
    }
    # Convert routes to validated ProxyRoute objects
    VALIDATED_ROUTES: List[ProxyRoute] = [
        ProxyRoute(path=path, target=target)
        for path, target in PROXY_ROUTES
    ]




