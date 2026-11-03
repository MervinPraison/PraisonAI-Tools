# Adanos market sentiment research

[Adanos](https://adanos.org/) is a commercial, plan-limited data provider.
An API key is required. Source availability, history, quotas, and rate limits
depend on the account plan. This tool follows API 1.54.1.
See the [API documentation](https://api.adanos.org/docs).

## Use with a researcher

Install `praisonai-tools[adanos]` and set `ADANOS_API_KEY` in the process
environment. The key can also be passed to the constructor. It is not an agent
tool parameter.

```python
from praisonaiagents import Agent
from praisonai_tools import AdanosTool

tool = AdanosTool()
researcher = Agent(name="Researcher", tools=[tool])

result = researcher.execute_tool("adanos_query", {
    "source": "news_stocks",
    "operation": "asset",
    "asset": "BRK",
    "from_date": "2026-10-01",
    "to_date": "2026-10-07",
})
if result.success:
    print(result.output)
else:
    print(result.error)
```

The callable tool, `run()`, and `safe_run()` return native `ToolResult` objects.
Success output contains `source`, `operation`, `requested_period` with `from`
and `to`, and unmodified provider JSON in `data`. Omitted dates remain `None`
in the requested period, not a claim about the provider's resolved window.
Failures have `success=False`, `output=None`, and a safe error message.
HTTP errors include only the status code, never the provider error body.

## Supported requests

Every operation below supports all five sources. Source values are
`reddit_stocks`, `x_stocks`, `news_stocks`, `polymarket_stocks`, and `reddit_crypto`.

| Operation | Inputs beyond source and operation | Provider response root |
| --- | --- | --- |
| `trending` | Optional dates and `limit` 1-100 | Array |
| `asset` | Required `asset`, optional dates | Object |
| `compare` | Required `assets` list of 1-10 keys, optional dates | Object with `stocks`, or crypto `tokens` |
| `search` | Required `query`, optional `limit` 1-50, no dates | Object with `results` |
| `market_sentiment` | Optional dates | Object |

Dates are inclusive UTC calendar dates in `YYYY-MM-DD`. `from_date` and
`to_date` become `from` and `to`. Omitted limits use the provider default of 20.
Search requires at least two non-$ characters after trimming. News caps query
length at 100 characters, Polymarket at 50. Other source restrictions and plan
eligibility remain provider-owned.

Crypto uses `/token/{symbol}` and compare `symbols`. Stock sources use
`/stock/{ticker}` and compare `tickers`. Keys retain their original spelling.
News company keys are issuer keys, not share-class tickers. Use `BRK`, not
`BRK.A` or `BRK-B`. The tool does not repair or normalize keys. The provider
rejects invalid News keys. Compare can return zero-activity entries for unknown
keys. Use search to check support. Null metrics and empty lists remain intact.

This is a 25-combination subset, not full API support. Excluded endpoints are
raw mentions, explain, sector and country rankings, stats, health, and direct
text analysis. Extra filters and pagination are also excluded.

Each invocation makes one GET request to the fixed `https://api.adanos.com`
host with a local, context-managed HTTP client, a 30-second timeout, no
redirects, and no automatic retries. No arbitrary URL, method, headers, or
query parameters are exposed. The tool checks JSON containers and identifying
fields, not every nested provider field. It does not compute a composite score.

Historical responses have no point-in-time guarantee. They may reflect later
corrections and are not a historical trading backtest feed or price data.
