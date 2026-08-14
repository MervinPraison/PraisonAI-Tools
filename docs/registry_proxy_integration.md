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
