# Tool-Registry Proxy Connector

An **optional, bring-your-own-account** connector that lets any PraisonAI agent
discover and call a large catalogue of third-party API endpoints (SEO,
enrichment, social data, scraping, ads) through a single proxy token — with
**credentials injected server-side by the registry, never held by the agent**.

PraisonAI ships **no registry code, no bundled binary and no default endpoint**.
You supply your own account token or a self-hosted base URL. The connector is
disabled unless `TOOL_PROXY_URL` is configured.

## Overview

The connector mirrors PraisonAI's deferred tool-search bridge
(`tool_search` / `tool_describe` / `tool_call`) with three functions:

| Function | Cost | Purpose |
| --- | --- | --- |
| `registry_search(query)` | free | capability search over the catalogue |
| `registry_describe(tool_id)` | free | params, price-per-call, example response |
| `registry_call(tool_id, params)` | paid | invoke via proxy; credential injected server-side |

## Installation

```bash
pip install "praisonai-tools[registry-proxy]"
```

## Setup (3 lines)

```bash
export TOOL_PROXY_URL="https://your-registry.example.com"   # or a self-hosted instance
export TOOL_PROXY_TOKEN="your-proxy-token"
# Optional: override the auth header for registries that expect a custom header.
# Default is "Authorization" (sent as "Bearer <token>"); any other name (e.g.
# "X-Treg-Token") sends the raw token in that header.
export TOOL_PROXY_AUTH_HEADER="Authorization"
# Optional: override the describe route for registries with a different layout.
# Must contain "{tool_id}"; defaults to the live registry route below.
export TOOL_PROXY_DESCRIBE_PATH="/catalog/endpoints/{tool_id}"
```

```python
from praisonaiagents import Agent
from praisonai_tools.registry_proxy import (
    registry_search, registry_describe, registry_call,
)

agent = Agent(
    instructions="SEO analyst",
    tools=[registry_search, registry_describe, registry_call],
)
agent.start("Find the top backlink sources for example.com and summarise")
# → registry_search("backlinks for a domain") → describe → call
# one token, no vendor keys in the agent
```

## Spend safety

`registry_call` accepts optional budget guards. When a configured budget would
be exceeded, the call is **denied and reported** as a tool-result error (never
raised as an exception):

```python
registry_call(
    "seo.backlinks",
    {"domain": "example.com"},
    max_cost_per_call=0.10,     # deny if price-per-call exceeds this
    max_session_spend=5.00,     # deny if cumulative spend would exceed this
)
```

Per-call price is read from `registry_describe`, so guards work without any
vendor-specific configuration. Guards **fail closed**: if a budget is set but
the price cannot be validated, the call is denied. Cumulative `max_session_spend`
persists across separate `registry_call` invocations within the same process,
scoped per `(proxy_url, token)` so distinct accounts never share a budget.

## HTTP methods

The registry enforces each endpoint's declared HTTP method on `/call/{id}`.
`registry_call` derives the method automatically from `registry_describe`
(the endpoint doc carries `method`): `GET` endpoints send `params` as the query
string, `POST`/`PUT` send them as a JSON body. Pass `method="GET"` explicitly to
skip the describe lookup when you already know the method. Only the standard
`GET`/`POST`/`PUT`/`PATCH`/`DELETE` verbs are accepted; any other value (e.g. a
mislabelled endpoint doc) is rejected as a tool-result error before any request.
`tool_id` is URL-encoded before being placed in the describe/call route, so it
cannot alter the requested path.

## Passthrough-URL calls

Passthrough-URL calls require the upstream to be **registered on the registry
first**. Loopback/private upstreams (e.g. `127.0.0.1`, RFC-1918 addresses) are
**refused by the registry's SSRF guard by design** — the base URL must be a
public `http(s)` address. This is registry-side policy, not a connector setting.

## Credential safety

The proxy token is only sent to the endpoint it was configured for. If a caller
(or a prompt-injected agent) supplies an explicit `proxy_url` without a matching
`token`, the ambient `TOOL_PROXY_TOKEN` is **not** attached — preventing the
token from being exfiltrated to an untrusted endpoint. For normal use, leave
`proxy_url`/`token` unset and configure `TOOL_PROXY_URL`/`TOOL_PROXY_TOKEN` via
the environment.

## Error taxonomy

All failures are returned as `{"error": ...}` tool results:

- Authentication failed (HTTP 401/403)
- Insufficient balance (HTTP 402)
- Upstream 4xx/5xx passed through
- Request timeout
- `httpx` not installed → install hint

## Tier 0 — Skills directory compatibility (zero code)

Registries that expose `skill install <name>` install skills into
`./.claude/skills/`. PraisonAI **already scans** this directory, so
registry-installed skills are discoverable by PraisonAI agents today with no
additional code:

- `praisonaiagents/skills/discovery.py` — `.claude/skills` compatibility scan
  plus an ancestor walk for monorepos.

## Tier 2 — Environment / CLI passthrough (config-only)

A registry's `shell` / `run <vendor> -- args` inject vendor-CLI credentials at
execution time. Using a PraisonAI environment definition, install the registry
CLI and log in via a token env var in `setup:`; the agent's `execute_command`
then has authenticated vendor CLIs (e.g. `run gh -- pr list`) without any key in
the container. Sandbox / board workers inherit the same via the environment
definition.

## Licensing note

Some registries are Apache-2.0 **with additional terms** prohibiting embedding
in commercially distributed products without permission. This connector is
therefore **optional and bring-your-own-account only**: it ships no registry
code and no default endpoint — the same posture as other BYO-account connectors.
