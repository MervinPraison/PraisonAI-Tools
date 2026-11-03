import os
import re
from datetime import date
from types import MappingProxyType
from typing import Literal, Optional
from urllib.parse import quote

from praisonai_tools.tools.base import BaseTool, ToolResult

__all__ = ["AdanosTool"]

_SOURCES = MappingProxyType({
    "reddit_stocks": "/reddit/stocks/v1",
    "x_stocks": "/x/stocks/v1",
    "news_stocks": "/news/stocks/v1",
    "polymarket_stocks": "/polymarket/stocks/v1",
    "reddit_crypto": "/reddit/crypto/v1",
})


def _safe_asset(value):
    # Syntax and issuer eligibility remain provider-owned, including News keys.
    return isinstance(value, str) and re.fullmatch(r"\$?[A-Za-z0-9]+(?:[.-][A-Za-z0-9]+)?", value) is not None


def _valid_data(data, operation, source):
    crypto = source == "reddit_crypto"
    identity = "symbol" if crypto else "ticker"

    def rows(value):
        return isinstance(value, list) and all(
            isinstance(row, dict) and isinstance(row.get(identity), str) for row in value
        )

    if operation == "trending":
        return rows(data) and all("buzz_score" in row for row in data)
    if not isinstance(data, dict):
        return False
    if operation == "asset":
        return isinstance(data.get(identity), str)
    if operation == "market_sentiment":
        activity = "trade_count" if source == "polymarket_stocks" else "mentions"
        return "buzz_score" in data and type(data.get(activity)) is int
    if type(data.get("period_days")) is not int:
        return False
    if operation == "compare":
        return rows(data.get("tokens" if crypto else "stocks"))
    return (isinstance(data.get("query"), str) and type(data.get("count")) is int
            and rows(data.get("results")))


class AdanosTool(BaseTool):
    """Read one page of Adanos research evidence per call."""

    name = "adanos_query"
    description = "Query source-labelled Adanos market sentiment, trending assets, asset detail, comparison or search."

    def __init__(self, api_key: Optional[str] = None):
        self._api_key = api_key if api_key is not None else os.getenv("ADANOS_API_KEY")
        super().__init__()

    def to_openai_tool(self):
        return self.get_schema()

    def run(
        self,
        source: Literal["reddit_stocks", "x_stocks", "news_stocks", "polymarket_stocks", "reddit_crypto"],
        operation: Literal["trending", "asset", "compare", "search", "market_sentiment"],
        asset: Optional[str] = None,
        assets: Optional[list[str]] = None,
        query: Optional[str] = None,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> ToolResult:
        """Fetch unmodified provider data, or an explicit failed ToolResult.

        Args:
            source: Research namespace, not an arbitrary URL.
            operation: One of the five supported research operations.
            asset: Stock ticker, unchanged News company key, or crypto symbol for asset.
            assets: One to ten keys for compare. Crypto uses symbols, stocks use tickers.
            query: Search text with at least two non-$ characters.
            from_date: Inclusive UTC start date in YYYY-MM-DD, except for search.
            to_date: Inclusive UTC end date in YYYY-MM-DD, except for search.
            limit: Trending 1-100 or search 1-50. Omit for the provider default.
        """
        if not self._api_key:
            return ToolResult(None, success=False, error="Configure ADANOS_API_KEY or constructor api_key.")
        if (not isinstance(self._api_key, str) or not self._api_key.isascii()
                or "\r" in self._api_key or "\n" in self._api_key):
            return ToolResult(None, success=False, error="Invalid Adanos API key configuration.")
        try:
            if not isinstance(source, str) or source not in _SOURCES:
                raise ValueError("Unsupported source.")
            if operation not in ("trending", "asset", "compare", "search", "market_sentiment"):
                raise ValueError("Unsupported operation.")
            if ((asset is not None and operation != "asset")
                    or (assets is not None and operation != "compare")
                    or (query is not None and operation != "search")):
                raise ValueError("asset, assets and query apply only to asset, compare and search respectively.")
            params = {}
            for key, value in (("from", from_date), ("to", to_date)):
                if value is not None:
                    if operation == "search":
                        raise ValueError("Search does not accept dates.")
                    if not isinstance(value, str) or not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value):
                        raise ValueError("Dates must use YYYY-MM-DD.")
                    try:
                        date.fromisoformat(value)
                    except ValueError:
                        raise ValueError("Invalid calendar date.") from None
                    params[key] = value
            if from_date is not None and to_date is not None and from_date > to_date:
                raise ValueError("from_date must not follow to_date.")
            if limit is not None:
                if operation not in ("trending", "search"):
                    raise ValueError("limit applies only to trending or search.")
                maximum = 50 if operation == "search" else 100
                if type(limit) is not int or not 1 <= limit <= maximum:
                    raise ValueError("limit is outside the supported range.")
                params["limit"] = limit
            crypto = source == "reddit_crypto"
            route = operation.replace("_", "-")
            if operation == "asset":
                if not _safe_asset(asset):
                    raise ValueError("A safe asset key is required.")
                route = ("token/" if crypto else "stock/") + quote(asset, safe="")
            elif operation == "compare":
                if not isinstance(assets, list) or not 1 <= len(assets) <= 10 or not all(map(_safe_asset, assets)):
                    raise ValueError("compare requires one to ten safe asset keys.")
                params["symbols" if crypto else "tickers"] = ",".join(assets)
            elif operation == "search":
                if not isinstance(query, str) or len(query.strip().replace("$", "").strip()) < 2:
                    raise ValueError("Search requires at least two non-$ characters.")
                if ((source == "news_stocks" and len(query) > 100)
                        or (source == "polymarket_stocks" and len(query) > 50)):
                    raise ValueError("Search query exceeds the source limit.")
                params["q"] = query
        except ValueError as error:
            return ToolResult(None, success=False, error=str(error))

        try:
            import httpx
        except ImportError:
            return ToolResult(None, success=False, error="Install praisonai-tools[adanos] to use AdanosTool.")
        try:
            with httpx.Client(timeout=30.0, follow_redirects=False) as client:
                response = client.get(
                    "https://api.adanos.com" + _SOURCES[source] + "/" + route,
                    params=params,
                    headers={"X-API-Key": self._api_key},
                )
        except httpx.HTTPError:
            return ToolResult(None, success=False, error="Adanos request failed or timed out.")
        if response.status_code != 200:
            return ToolResult(None, success=False, error=f"Adanos HTTP {response.status_code}.")
        try:
            data = response.json()
        except ValueError:
            return ToolResult(None, success=False, error="Adanos returned invalid JSON.")
        if not _valid_data(data, operation, source):
            return ToolResult(None, success=False, error="Adanos returned an unexpected response shape.")
        return ToolResult({
            "source": source,
            "operation": operation,
            "requested_period": {"from": from_date, "to": to_date},
            "data": data,
        })
