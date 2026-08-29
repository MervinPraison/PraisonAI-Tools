"""Context.dev tools for PraisonAI agents.

Install with ``pip install praisonai-tools[context]`` and set
``CONTEXT_DEV_API_KEY`` (or the legacy ``CONTEXT_API_KEY`` alias).
"""

from __future__ import annotations

import base64
import binascii
import copy
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import quote

from praisonai_tools.tools.base import BaseTool

__all__ = [
    "ContextTool",
    "ContextSearch",
    "ContextScrape",
    "ContextCrawl",
    "ContextSitemap",
    "ContextExtract",
    "ContextParse",
    "ContextWebToolkit",
    "ContextBrandToolkit",
    "ContextMonitorToolkit",
    "ContextBatchToolkit",
    "ContextToolkit",
    "context_search",
    "context_scrape",
]

DEFAULT_API_BASE = "https://api.context.dev/v1"
DEFAULT_TIMEOUT_SECONDS = 180.0
OMITTED_RESPONSE_FIELDS = {"debug", "key_metadata", "request_id", "trace_id"}


def _property(kind: str, description: str, **constraints: Any) -> Dict[str, Any]:
    return {"type": kind, "description": description, **constraints}


def _string(description: str) -> Dict[str, Any]:
    return _property("string", description)


def _integer(description: str, **constraints: Any) -> Dict[str, Any]:
    return _property("integer", description, **constraints)


def _boolean(description: str) -> Dict[str, Any]:
    return _property("boolean", description)


def _object(description: str) -> Dict[str, Any]:
    return _property("object", description, additionalProperties=True)


def _array(description: str) -> Dict[str, Any]:
    return _property("array", description, items={})

COMMON_OPTIONS = _object(
    "Additional Context.dev API parameters supported by this endpoint. Use documented API field names."
)
TRACKING = {
    "timeoutMS": _integer("Maximum request duration in milliseconds.", minimum=1),
    "tags": _array("Caller-defined tags used to track this request."),
}


@dataclass(frozen=True)
class _Endpoint:
    method: str
    path: str
    description: str
    group: str
    required: Tuple[str, ...] = ()
    properties: Optional[Dict[str, Any]] = None
    path_fields: Tuple[str, ...] = ()
    header_fields: Tuple[str, ...] = ()
    binary: bool = False
    read_only: bool = True
    destructive: bool = False
    open_world: bool = False


def _web_properties(properties: Dict[str, Any]) -> Dict[str, Any]:
    return {**properties, **TRACKING, "options": COMMON_OPTIONS}


_ENDPOINTS: Dict[str, _Endpoint] = {
    "parse-document": _Endpoint(
        "POST", "/parse", "Parse a PDF, Office document, image, code file, or text file into clean Markdown.", "web",
        properties={
            "file_base64": _string("Base64-encoded file bytes when no local path is available."),
            "extension": _string("Optional file extension hint such as pdf, docx, png, or csv."),
            "includeLinks": _boolean("Preserve hyperlinks in the Markdown output."),
            "includeImages": _boolean("Include image references in the Markdown output."),
            "ocr": _boolean("OCR scanned PDF pages that do not have a usable text layer."),
            "pdf": _object("Optional inclusive PDF page range with start and end fields."),
            "zdr": _string("Set to enabled when zero-data-retention is configured for the account."),
            "tags": _array("Caller-defined tags used to track this request."),
            "options": COMMON_OPTIONS,
        }, binary=True, read_only=False,
    ),
    "web-scrape-html": _Endpoint(
        "GET", "/web/scrape/html", "Fetch raw HTML from one known URL, including rendered content when requested.", "web",
        ("url",), _web_properties({
            "url": _string("Full HTTP or HTTPS URL to scrape."),
            "useMainContentOnly": _boolean("Return only the page's main content."),
            "includeFrames": _boolean("Render iframe contents into the response."),
            "includeSelectors": _array("CSS selectors whose matching subtrees should be kept."),
            "excludeSelectors": _array("CSS selectors to remove from the result."),
            "waitForMs": _integer("Browser wait after page load in milliseconds.", minimum=0, maximum=30000),
            "actions": _array("Ordered browser actions to perform before capture."),
            "country": _string("ISO 3166-1 alpha-2 proxy country code."),
        }), open_world=True,
    ),
    "web-scrape-markdown": _Endpoint(
        "GET", "/web/scrape/markdown", "Turn one known URL into clean, LLM-ready Markdown.", "web",
        ("url",), _web_properties({
            "url": _string("Full HTTP or HTTPS URL to scrape."),
            "includeLinks": _boolean("Preserve hyperlinks in Markdown."),
            "includeImages": _boolean("Include image references in Markdown."),
            "useMainContentOnly": _boolean("Remove navigation, headers, footers, and sidebars."),
            "includeHTML": _boolean("Also include the source HTML used for conversion."),
            "includeSelectors": _array("CSS selectors whose matching subtrees should be kept."),
            "excludeSelectors": _array("CSS selectors to remove before Markdown conversion."),
            "waitForMs": _integer("Browser wait after page load in milliseconds.", minimum=0, maximum=30000),
            "actions": _array("Ordered browser actions to perform before capture."),
            "country": _string("ISO 3166-1 alpha-2 proxy country code."),
        }), open_world=True,
    ),
    "web-scrape-images": _Endpoint(
        "GET", "/web/scrape/images", "Find useful images on a web page with optional enrichment and deduplication.", "web",
        ("url",), _web_properties({
            "url": _string("Full HTTP or HTTPS page URL to inspect."),
            "dedupe": _boolean("Remove visually duplicate images."),
            "enrichment": _object("Optional image enrichment settings."),
            "waitForMs": _integer("Browser wait after page load in milliseconds.", minimum=0, maximum=30000),
            "actions": _array("Ordered browser actions to perform before image collection."),
        }), open_world=True,
    ),
    "web-scrape-sitemap": _Endpoint(
        "GET", "/web/scrape/sitemap", "Discover, filter, and search URLs from a website sitemap.", "web",
        ("domain",), _web_properties({
            "domain": _string("Domain whose sitemap should be discovered."),
            "maxLinks": _integer("Maximum number of URLs to return.", minimum=1, maximum=100000),
            "sitemapUrl": _string("Explicit sitemap URL to use instead of discovery."),
            "urlRegex": _string("RE2-compatible regex used to filter returned URLs."),
            "search": _string("Natural-language topic used to rank and filter sitemap URLs."),
        }), open_world=True,
    ),
    "web-crawl": _Endpoint(
        "POST", "/web/crawl", "Crawl linked pages from a starting URL and return clean Markdown for each page.", "web",
        ("url",), _web_properties({
            "url": _string("HTTP or HTTPS URL where the crawl starts."),
            "maxPages": _integer("Maximum pages to crawl.", minimum=1, maximum=500),
            "maxDepth": _integer("Maximum link depth from the starting URL.", minimum=0),
            "urlRegex": _string("Regex that followed and scraped URLs must match."),
            "includeLinks": _boolean("Preserve hyperlinks in Markdown."),
            "includeImages": _boolean("Include image references in Markdown."),
            "followSubdomains": _boolean("Allow links on subdomains of the starting domain."),
            "country": _string("ISO 3166-1 alpha-2 proxy country code."),
        }), open_world=True,
    ),
    "web-extract": _Endpoint(
        "POST", "/web/extract", "Extract structured JSON from one or more web pages using a caller-provided JSON Schema.", "web",
        ("url", "schema"), _web_properties({
            "url": _string("HTTP or HTTPS URL where extraction starts."),
            "schema": _object("JSON Schema describing the structured object to return."),
            "instructions": _string("Guidance about facts to prioritize or how fields should be interpreted."),
            "factCheck": _boolean("Require returned values to be grounded in page content."),
            "followSubdomains": _boolean("Allow extraction to follow links on subdomains."),
            "maxPages": _integer("Maximum pages to analyze.", minimum=1, maximum=50),
            "maxDepth": _integer("Maximum link depth from the starting page.", minimum=0),
        }), open_world=True,
    ),
    "web-search": _Endpoint(
        "POST", "/web/search", "Search the live web with domain, freshness, geography, and inline Markdown controls.", "web",
        ("query",), _web_properties({
            "query": _string("Natural-language query or Google-style search expression."),
            "numResults": _integer("Number of search results to return.", minimum=10, maximum=100),
            "includeDomains": _array("Allowlist of domains to include."),
            "excludeDomains": _array("Blocklist of domains to exclude."),
            "freshness": _string("Freshness window used to restrict published content."),
            "country": _string("ISO 3166-1 alpha-2 country code for localized results."),
            "queryFanout": _boolean("Expand the request into parallel query variants for broader recall."),
            "markdownOptions": _object("Inline Markdown scraping settings for each result."),
        }), open_world=True,
    ),
    "brand-retrieve-unified": _Endpoint(
        "POST", "/brand/retrieve", "Retrieve logos, colors, fonts, descriptions, socials, links, industry, and other brand intelligence.", "brand",
        ("body",), {"body": _object("Exactly one brand lookup type and its value."), "options": COMMON_OPTIONS}, open_world=True,
    ),
    "web-styleguide": _Endpoint(
        "GET", "/web/styleguide", "Extract a website's visual style guide, including colors and design tokens.", "brand",
        properties=_web_properties({
            "domain": _string("Domain to inspect."), "directUrl": _string("Specific URL to inspect directly."),
            "colorScheme": _string("Browser color scheme: light or dark."),
        }), open_world=True,
    ),
    "web-fonts": _Endpoint(
        "GET", "/web/fonts", "Identify fonts and typography used by a website.", "brand",
        properties=_web_properties({"domain": _string("Domain to inspect."), "directUrl": _string("Specific URL to inspect directly.")}), open_world=True,
    ),
    "web-screenshot": _Endpoint(
        "GET", "/web/screenshot", "Capture a viewport or full-page screenshot of a website.", "web",
        properties=_web_properties({
            "domain": _string("Domain to capture."), "directUrl": _string("Specific URL to capture directly."),
            "fullScreenshot": _string("Set to true for a full-page screenshot."),
            "viewport": _object("Viewport width and height."), "colorScheme": _string("Browser color scheme: light or dark."),
            "country": _string("ISO 3166-1 alpha-2 proxy country code."),
        }), open_world=True,
    ),
    "web-naics": _Endpoint(
        "GET", "/web/naics", "Classify a company or domain using NAICS industry codes.", "brand", ("input",),
        _web_properties({"input": _string("Company name or domain to classify."), "minResults": _integer("Minimum classifications to return.", minimum=1), "maxResults": _integer("Maximum classifications to return.", minimum=1, maximum=10)}), open_world=True,
    ),
    "web-sic": _Endpoint(
        "GET", "/web/sic", "Classify a company or domain using SIC industry codes.", "brand", ("input",),
        _web_properties({"input": _string("Company name or domain to classify."), "type": _string("SIC dataset to use."), "minResults": _integer("Minimum classifications to return.", minimum=1), "maxResults": _integer("Maximum classifications to return.", minimum=1, maximum=10)}), open_world=True,
    ),
}


def _resource_endpoint(
    method: str,
    path: str,
    description: str,
    group: str,
    required: Tuple[str, ...] = (),
    properties: Optional[Dict[str, Any]] = None,
    *,
    destructive: bool = False,
) -> _Endpoint:
    return _Endpoint(
        method, path, description, group, required, properties or {"options": COMMON_OPTIONS},
        tuple(field for field in ("monitor_id", "change_id", "run_id", "batch_id") if "{" + field + "}" in path),
        ("Idempotency-Key",) if group == "batches" and method == "POST" and path.endswith("submit") else (),
        read_only=method == "GET", destructive=destructive,
    )


_MONITOR_LIST = {
    "limit": _integer("Maximum items returned per page.", minimum=1, maximum=100),
    "cursor": _string("Opaque pagination cursor from the previous response."),
    "status": _string("Lifecycle status filter."),
    "options": COMMON_OPTIONS,
}
_ENDPOINTS.update({
    "list-monitors": _resource_endpoint("GET", "/monitors", "List and search website monitors.", "monitors", properties={"q": _string("Free-text monitor search."), "tag": _string("Required monitor tag."), **_MONITOR_LIST}),
    "create-monitor": _resource_endpoint("POST", "/monitors", "Create a recurring website monitor and its initial baseline run.", "monitors", ("name", "target"), {"name": _string("Human-readable monitor name."), "target": _object("What the monitor watches."), "change_detection": _object("How changes are detected."), "schedule": _object("Interval schedule for the monitor."), "webhook": _object("Optional webhook configuration."), "tags": _array("Monitor tags."), "options": COMMON_OPTIONS}, destructive=True),
    "get-monitor": _resource_endpoint("GET", "/monitors/{monitor_id}", "Get one monitor's configuration.", "monitors", ("monitor_id",), {"monitor_id": _string("Monitor identifier.")}),
    "update-monitor": _resource_endpoint("PATCH", "/monitors/{monitor_id}", "Update an existing monitor's configuration or lifecycle status.", "monitors", ("monitor_id",), {"monitor_id": _string("Monitor identifier."), "name": _string("Updated monitor name."), "status": _string("Updated lifecycle status."), "target": _object("Updated monitor target."), "change_detection": _object("Updated change detection settings."), "schedule": _object("Updated interval schedule."), "webhook": _object("Updated webhook configuration."), "tags": _array("Updated monitor tags."), "options": COMMON_OPTIONS}, destructive=True),
    "delete-monitor": _resource_endpoint("DELETE", "/monitors/{monitor_id}", "Delete an existing website monitor.", "monitors", ("monitor_id",), {"monitor_id": _string("Monitor identifier.")}, destructive=True),
    "list-monitor-runs": _resource_endpoint("GET", "/monitors/{monitor_id}/runs", "List execution runs for one monitor.", "monitors", ("monitor_id",), {"monitor_id": _string("Monitor identifier."), **_MONITOR_LIST}),
    "list-monitor-changes": _resource_endpoint("GET", "/monitors/{monitor_id}/changes", "List detected changes for one monitor.", "monitors", ("monitor_id",), {"monitor_id": _string("Monitor identifier."), "since": _string("Inclusive ISO 8601 start time."), "until": _string("Exclusive ISO 8601 end time."), "tag": _string("Required change tag."), **_MONITOR_LIST}),
    "list-account-runs": _resource_endpoint("GET", "/monitors/runs", "List monitor runs across the account.", "monitors", properties=_MONITOR_LIST),
    "list-monitor-credit-usage": _resource_endpoint("GET", "/monitors/credit-usage", "Get monitor credit usage for a time range.", "monitors", properties={"since": _string("Inclusive ISO 8601 start time."), "until": _string("Exclusive ISO 8601 end time."), "options": COMMON_OPTIONS}),
    "list-changes": _resource_endpoint("GET", "/monitors/changes", "List detected changes across the account.", "monitors", properties={"monitor_id": _string("Optional monitor identifier filter."), "since": _string("Inclusive ISO 8601 start time."), "until": _string("Exclusive ISO 8601 end time."), "tag": _string("Required change tag."), **_MONITOR_LIST}),
    "get-change": _resource_endpoint("GET", "/monitors/changes/{change_id}", "Get one detected monitor change.", "monitors", ("change_id",), {"change_id": _string("Detected change identifier.")}),
    "run-monitor-now": _resource_endpoint("POST", "/monitors/{monitor_id}/run", "Run an existing monitor immediately.", "monitors", ("monitor_id",), {"monitor_id": _string("Monitor identifier.")}, destructive=True),
    "get-monitor-run": _resource_endpoint("GET", "/monitors/{monitor_id}/runs/{run_id}", "Get one execution run for a monitor.", "monitors", ("monitor_id", "run_id"), {"monitor_id": _string("Monitor identifier."), "run_id": _string("Monitor run identifier.")}),
    "submit-batch": _resource_endpoint("POST", "/batch/submit", "Submit up to 25,000 URLs or a site crawl as an asynchronous batch job.", "batches", ("input",), {"input": _object("URL-list or crawl batch input."), "webhookUrl": _string("Webhook notified when the batch finishes."), "tags": _array("Batch tags."), "Idempotency-Key": _string("Unique key that makes submission retries idempotent."), "options": COMMON_OPTIONS}, destructive=True),
    "list-batches": _resource_endpoint("GET", "/batch/list", "List and search asynchronous scraping batches.", "batches", properties={"q": _string("Free-text batch search."), "tags": _string("Comma-separated batch tag filter."), **_MONITOR_LIST}),
    "get-batch": _resource_endpoint("GET", "/batch/{batch_id}", "Get one asynchronous batch and its status.", "batches", ("batch_id",), {"batch_id": _string("Batch identifier.")}),
    "delete-batch": _resource_endpoint("DELETE", "/batch/{batch_id}", "Delete an asynchronous batch record.", "batches", ("batch_id",), {"batch_id": _string("Batch identifier.")}, destructive=True),
    "get-batch-results": _resource_endpoint("GET", "/batch/{batch_id}/results", "Read one page of results from a completed batch.", "batches", ("batch_id",), {"batch_id": _string("Batch identifier."), "limit": _integer("Maximum results returned per page.", minimum=1), "cursor": _string("Cursor from the previous result page."), "options": COMMON_OPTIONS}),
    "cancel-batch": _resource_endpoint("POST", "/batch/{batch_id}/cancel", "Cancel an asynchronous batch that has not completed.", "batches", ("batch_id",), {"batch_id": _string("Batch identifier.")}, destructive=True),
})

ACTION_ENDPOINTS = {"web-scrape-html", "web-scrape-markdown", "web-scrape-images"}
WRITE_ENDPOINTS = {
    "create-monitor",
    "update-monitor",
    "delete-monitor",
    "run-monitor-now",
    "submit-batch",
    "delete-batch",
    "cancel-batch",
}


def _query_pairs(name: str, value: Any) -> List[Tuple[str, str]]:
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        return [pair for item in value for pair in _query_pairs(name, item)]
    if isinstance(value, dict):
        return [pair for key, item in value.items() for pair in _query_pairs(f"{name}[{key}]", item)]
    if isinstance(value, bool):
        return [(name, "true" if value else "false")]
    return [(name, str(value))]


def _response_value(response: Any) -> Any:
    try:
        payload = response.json()
    except ValueError:
        payload = None
    if response.is_error:
        record = payload if isinstance(payload, dict) else {}
        message = next((record[key] for key in ("message", "error", "error_description") if isinstance(record.get(key), str)), response.text.strip() or "Request failed")
        raise RuntimeError(f"Context API {response.status_code}: {message}")
    if isinstance(payload, dict):
        return {key: value for key, value in payload.items() if key not in OMITTED_RESPONSE_FIELDS}
    return payload if payload is not None else response.text


class ContextTool(BaseTool):
    """One agent-callable Context.dev API endpoint."""

    version = "1.0.0"

    def __init__(
        self,
        endpoint: str,
        api_key: Optional[str] = None,
        api_base: Optional[str] = None,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
        client: Any = None,
        allow_browser_actions: bool = False,
        allow_local_files: bool = False,
        upload_dir: Optional[str | Path] = None,
    ):
        if endpoint not in _ENDPOINTS:
            raise ValueError(f"Unknown Context.dev endpoint: {endpoint}")
        self.endpoint = endpoint
        self.api_key = api_key
        self.api_base = (api_base or os.getenv("CONTEXT_API_BASE") or DEFAULT_API_BASE).rstrip("/")
        self.timeout = timeout
        self.client = client
        self.allow_browser_actions = allow_browser_actions
        self.allow_local_files = allow_local_files
        self.upload_dir = Path(upload_dir).expanduser().resolve() if upload_dir else None
        if endpoint == "parse-document" and allow_local_files:
            if self.upload_dir is None or not self.upload_dir.is_dir():
                raise ValueError("upload_dir must be an existing directory when local file access is enabled.")
        spec = _ENDPOINTS[endpoint]
        self.name = f"context_{endpoint.replace('-', '_')}"
        self.description = spec.description
        self.annotations = {
            "readOnlyHint": spec.read_only,
            "destructiveHint": spec.destructive,
            "openWorldHint": spec.open_world,
        }
        properties = copy.deepcopy(spec.properties or {})
        if endpoint == "parse-document" and allow_local_files:
            properties["file_path"] = _string("Path to a file inside the configured upload directory.")
        if endpoint in ACTION_ENDPOINTS and not allow_browser_actions:
            properties.pop("actions", None)
            self.annotations = {**self.annotations, "readOnlyHint": True, "destructiveHint": False}
            self.description += " Browser actions are disabled for this tool instance."
        self.parameters = {
            "type": "object",
            "properties": properties,
            "required": list(spec.required),
            "additionalProperties": False,
        }
        super().__init__()

    def _api_key(self) -> str:
        value = self.api_key or os.getenv("CONTEXT_DEV_API_KEY") or os.getenv("CONTEXT_API_KEY")
        if not value or not value.strip():
            raise ValueError("Context.dev API key missing. Pass api_key or set CONTEXT_DEV_API_KEY.")
        return value.strip()

    def _binary_body(self, arguments: Dict[str, Any]) -> bytes:
        file_path = arguments.pop("file_path", None)
        encoded = arguments.pop("file_base64", None)
        if file_path and encoded:
            raise ValueError("Provide either file_path or file_base64, not both.")
        if file_path:
            if not self.allow_local_files or self.upload_dir is None:
                raise ValueError("Local file access is disabled. Use file_base64 or explicitly configure an upload directory.")
            try:
                path = Path(file_path).expanduser().resolve(strict=True)
                path.relative_to(self.upload_dir)
            except (FileNotFoundError, ValueError) as exc:
                raise ValueError("file_path must resolve to a file inside the configured upload directory.") from exc
            if not path.is_file():
                raise ValueError(f"File not found: {path}")
            return path.read_bytes()
        if encoded:
            try:
                return base64.b64decode(encoded, validate=True)
            except (binascii.Error, ValueError) as exc:
                raise ValueError("file_base64 must contain valid base64-encoded bytes.") from exc
        raise ValueError("Provide file_path or file_base64.")

    def run(self, **kwargs: Any) -> Any:
        spec = _ENDPOINTS[self.endpoint]
        arguments = {key: value for key, value in kwargs.items() if value is not None}
        options = arguments.pop("options", {})
        if options and not isinstance(options, dict):
            raise ValueError("options must be an object.")
        overlap = set(arguments).intersection(options)
        if overlap:
            raise ValueError(f"Duplicate values in options: {', '.join(sorted(overlap))}")
        if self.endpoint in ACTION_ENDPOINTS and not self.allow_browser_actions and "actions" in options:
            raise ValueError("Browser actions are disabled for this tool instance.")
        arguments = {**arguments, **options}
        missing = [field for field in spec.required if arguments.get(field) is None]
        if missing:
            raise ValueError(f"Missing required input: {', '.join(missing)}")

        path = spec.path
        for field in spec.path_fields:
            path = path.replace("{" + field + "}", quote(str(arguments.pop(field)), safe=""))
        headers = {
            "Authorization": f"Bearer {self._api_key()}",
            "User-Agent": "praisonai-tools-context/1.0",
        }
        for field in spec.header_fields:
            value = arguments.pop(field, None)
            if value is not None:
                headers[field] = str(value)

        content = None
        if spec.binary:
            content = self._binary_body(arguments)
            headers["Content-Type"] = "application/octet-stream"
        request_kwargs: Dict[str, Any] = {
            "method": spec.method,
            "url": f"{self.api_base}{path}",
            "headers": headers,
        }
        if spec.method in {"GET", "DELETE"} or spec.binary:
            request_kwargs["params"] = [pair for key, value in arguments.items() for pair in _query_pairs(key, value)]
            if spec.binary:
                request_kwargs["content"] = content
        else:
            request_kwargs["json"] = arguments.pop("body") if set(arguments) == {"body"} else arguments

        if self.client is not None:
            response = self.client.request(**request_kwargs)
        else:
            try:
                import httpx
            except ImportError as exc:
                raise ImportError("Install Context.dev tools with: pip install 'praisonai-tools[context]'") from exc
            with httpx.Client(timeout=self.timeout) as client:
                response = client.request(**request_kwargs)
        return _response_value(response)


class _NamedContextEndpoint(ContextTool):
    endpoint_name = ""

    def __init__(self, **kwargs: Any):
        super().__init__(self.endpoint_name, **kwargs)


class ContextSearch(_NamedContextEndpoint):
    """Search the live web with Context.dev."""

    endpoint_name = "web-search"


class ContextScrape(_NamedContextEndpoint):
    """Scrape one URL into clean Markdown with Context.dev."""

    endpoint_name = "web-scrape-markdown"


class ContextCrawl(_NamedContextEndpoint):
    """Crawl linked pages with Context.dev."""

    endpoint_name = "web-crawl"


class ContextSitemap(_NamedContextEndpoint):
    """Discover and search website sitemap URLs with Context.dev."""

    endpoint_name = "web-scrape-sitemap"


class ContextExtract(_NamedContextEndpoint):
    """Extract structured JSON from the web with Context.dev."""

    endpoint_name = "web-extract"


class ContextParse(_NamedContextEndpoint):
    """Parse a file into Markdown with Context.dev."""

    endpoint_name = "parse-document"


class _ContextToolkitBase:
    groups: Tuple[str, ...] = ()

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_base: Optional[str] = None,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
        client: Any = None,
        include_write_tools: bool = False,
        allow_browser_actions: bool = False,
        allow_local_files: bool = False,
        upload_dir: Optional[str | Path] = None,
    ):
        self.api_key = api_key
        self.api_base = api_base
        self.timeout = timeout
        self.client = client
        self.include_write_tools = include_write_tools
        self.allow_browser_actions = allow_browser_actions
        self.allow_local_files = allow_local_files
        self.upload_dir = upload_dir

    def get_tools(self) -> List[ContextTool]:
        endpoint_names = [
            name for name, endpoint in _ENDPOINTS.items()
            if endpoint.group in self.groups and (self.include_write_tools or name not in WRITE_ENDPOINTS)
        ]
        return [
            ContextTool(
                name,
                api_key=self.api_key,
                api_base=self.api_base,
                timeout=self.timeout,
                client=self.client,
                allow_browser_actions=self.allow_browser_actions,
                allow_local_files=self.allow_local_files,
                upload_dir=self.upload_dir,
            )
            for name in endpoint_names
        ]


class ContextWebToolkit(_ContextToolkitBase):
    """Web search, scraping, crawling, extraction, screenshot, and parsing tools."""

    groups = ("web",)


class ContextBrandToolkit(_ContextToolkitBase):
    """Brand intelligence, style guide, font, NAICS, and SIC tools."""

    groups = ("brand",)


class ContextMonitorToolkit(_ContextToolkitBase):
    """Read-only monitor tools by default, with writes available by explicit opt-in."""

    groups = ("monitors",)


class ContextBatchToolkit(_ContextToolkitBase):
    """Read-only batch tools by default, with writes available by explicit opt-in."""

    groups = ("batches",)


class ContextToolkit(_ContextToolkitBase):
    """Complete public Context.dev tool catalog with safe defaults."""

    groups = ("web", "brand", "monitors", "batches")


def context_search(query: str, num_results: int = 10, **kwargs: Any) -> Any:
    """Search the live web with Context.dev."""
    return ContextSearch().run(query=query, numResults=num_results, **kwargs)


def context_scrape(url: str, **kwargs: Any) -> Any:
    """Scrape one URL into clean Markdown with Context.dev."""
    return ContextScrape().run(url=url, **kwargs)
