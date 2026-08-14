"""Tool-registry proxy connector for PraisonAI Agents.

Optional bring-your-own-account connector that lets an agent discover and call
a large catalogue of third-party API endpoints through a single proxy token,
with credentials injected server-side by the registry (never held by the agent).

Mirrors PraisonAI's deferred tool-search bridge:
    registry_search(query)      -> capability search over the catalogue
    registry_describe(tool_id)  -> params, price-per-call, example response
    registry_call(tool_id, ...) -> invoke via proxy (credential injected server-side)

The connector is disabled unless ``TOOL_PROXY_URL`` is configured. PraisonAI
ships no registry code, no bundled binary and no default endpoint - the user
supplies their own account token or self-hosted base URL.

Usage:
    from praisonai_tools.registry_proxy import (
        registry_search, registry_describe, registry_call,
    )

    agent = Agent(
        instructions="SEO analyst",
        tools=[registry_search, registry_describe, registry_call],
    )

Environment Variables:
    TOOL_PROXY_URL:   base URL of the tool registry (unset -> connector disabled)
    TOOL_PROXY_TOKEN: proxy token sent as the auth header
"""

from .registry_proxy import (
    RegistryProxyTool,
    registry_search,
    registry_describe,
    registry_call,
)

__all__ = [
    "RegistryProxyTool",
    "registry_search",
    "registry_describe",
    "registry_call",
]
