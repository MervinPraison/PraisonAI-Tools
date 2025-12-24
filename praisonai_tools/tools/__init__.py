"""Tools package for PraisonAI Tools.

This module provides base classes and ready-to-use tools for AI agents.

Base classes for custom tools:
- BaseTool, @tool decorator, FunctionTool

Ready-to-use tools:
- EmailTool: Send/read emails via SMTP/IMAP
- SlackTool: Send messages to Slack
- DiscordTool: Send messages to Discord
- GitHubTool: Interact with GitHub repos/issues
- ImageTool: Generate images with DALL-E
- WeatherTool: Get weather data
- YouTubeTool: Search YouTube, get transcripts
- TTSTool: Text-to-speech conversion
"""

from praisonai_tools.tools.base import BaseTool, ToolResult, ToolValidationError, validate_tool
from praisonai_tools.tools.decorator import tool, FunctionTool, is_tool, get_tool_schema

# Lazy imports for tools to avoid loading dependencies until needed
def __getattr__(name):
    """Lazy load tool classes."""
    tool_map = {
        # Email
        "EmailTool": "email_tool",
        "send_email": "email_tool",
        "read_emails": "email_tool",
        "search_emails": "email_tool",
        # Slack
        "SlackTool": "slack_tool",
        "send_slack_message": "slack_tool",
        "get_slack_channels": "slack_tool",
        "get_slack_history": "slack_tool",
        # Discord
        "DiscordTool": "discord_tool",
        "send_discord_webhook": "discord_tool",
        "send_discord_message": "discord_tool",
        # GitHub
        "GitHubTool": "github_tool",
        "search_github_repos": "github_tool",
        "get_github_repo": "github_tool",
        "create_github_issue": "github_tool",
        # Image Generation
        "ImageTool": "image_tool",
        "generate_image": "image_tool",
        # Weather
        "WeatherTool": "weather_tool",
        "get_weather": "weather_tool",
        "get_forecast": "weather_tool",
        "get_air_quality": "weather_tool",
        # YouTube
        "YouTubeTool": "youtube_tool",
        "search_youtube": "youtube_tool",
        "get_youtube_video": "youtube_tool",
        "get_youtube_transcript": "youtube_tool",
        # Text-to-Speech
        "TTSTool": "tts_tool",
        "text_to_speech": "tts_tool",
        "list_tts_voices": "tts_tool",
        # Telegram
        "TelegramTool": "telegram_tool",
        "send_telegram_message": "telegram_tool",
        # Notion
        "NotionTool": "notion_tool",
        "search_notion": "notion_tool",
        "create_notion_page": "notion_tool",
        # PostgreSQL
        "PostgresTool": "postgres_tool",
        "query_postgres": "postgres_tool",
        "list_postgres_tables": "postgres_tool",
        # Reddit
        "RedditTool": "reddit_tool",
        "search_reddit": "reddit_tool",
        "get_reddit_hot": "reddit_tool",
        # Docker
        "DockerTool": "docker_tool",
        "list_docker_containers": "docker_tool",
        "run_docker_container": "docker_tool",
        # MySQL
        "MySQLTool": "mysql_tool",
        "query_mysql": "mysql_tool",
        # SQLite
        "SQLiteTool": "sqlite_tool",
        "query_sqlite": "sqlite_tool",
        # MongoDB
        "MongoDBTool": "mongodb_tool",
        "query_mongodb": "mongodb_tool",
        # Redis
        "RedisTool": "redis_tool",
        "redis_get": "redis_tool",
        "redis_set": "redis_tool",
        # DuckDuckGo
        "DuckDuckGoTool": "duckduckgo_tool",
        "duckduckgo_search": "duckduckgo_tool",
        # Tavily
        "TavilyTool": "tavily_tool",
        "tavily_search": "tavily_tool",
        # Wikipedia
        "WikipediaTool": "wikipedia_tool",
        "wikipedia_search": "wikipedia_tool",
        # ArXiv
        "ArxivTool": "arxiv_tool",
        "arxiv_search": "arxiv_tool",
        # Calculator
        "CalculatorTool": "calculator_tool",
        "calculate": "calculator_tool",
        # Shell
        "ShellTool": "shell_tool",
        "shell_execute": "shell_tool",
        # File
        "FileTool": "file_tool",
        "read_file": "file_tool",
        "write_file": "file_tool",
        # Firecrawl
        "FirecrawlTool": "firecrawl_tool",
        "firecrawl_scrape": "firecrawl_tool",
        # Serper
        "SerperTool": "serper_tool",
        "serper_search": "serper_tool",
        # Jina
        "JinaTool": "jina_tool",
        "jina_read": "jina_tool",
        # Google Calendar
        "GoogleCalendarTool": "google_calendar_tool",
        "list_calendar_events": "google_calendar_tool",
        # Google Sheets
        "GoogleSheetsTool": "google_sheets_tool",
        "read_google_sheet": "google_sheets_tool",
        # Jira
        "JiraTool": "jira_tool",
        "jira_search": "jira_tool",
        # Trello
        "TrelloTool": "trello_tool",
        "list_trello_boards": "trello_tool",
        # YFinance
        "YFinanceTool": "yfinance_tool",
        "get_stock_price": "yfinance_tool",
        # Pinecone
        "PineconeTool": "pinecone_tool",
        "pinecone_query": "pinecone_tool",
        # Qdrant
        "QdrantTool": "qdrant_tool",
        "qdrant_search": "qdrant_tool",
        # Chroma
        "ChromaTool": "chroma_tool",
        "chroma_query": "chroma_tool",
        # HackerNews
        "HackerNewsTool": "hackernews_tool",
        "get_hackernews_top": "hackernews_tool",
        # Twilio
        "TwilioTool": "twilio_tool",
        "send_sms": "twilio_tool",
        # Spotify
        "SpotifyTool": "spotify_tool",
        "spotify_search": "spotify_tool",
        # Linear
        "LinearTool": "linear_tool",
        "list_linear_issues": "linear_tool",
        # Crawl4AI
        "Crawl4AITool": "crawl4ai_tool",
        "crawl4ai_crawl": "crawl4ai_tool",
        # Exa
        "ExaTool": "exa_tool",
        "exa_search": "exa_tool",
        # DuckDB
        "DuckDBTool": "duckdb_tool",
        "duckdb_query": "duckdb_tool",
        # Neo4j
        "Neo4jTool": "neo4j_tool",
        "neo4j_query": "neo4j_tool",
        # Weaviate
        "WeaviateTool": "weaviate_tool",
        "weaviate_search": "weaviate_tool",
        # LanceDB
        "LanceDBTool": "lancedb_tool",
        "lancedb_search": "lancedb_tool",
        # Supabase
        "SupabaseTool": "supabase_tool",
        "supabase_select": "supabase_tool",
        # Milvus
        "MilvusTool": "milvus_tool",
        "milvus_search": "milvus_tool",
        # Google Maps
        "GoogleMapsTool": "google_maps_tool",
        "geocode_address": "google_maps_tool",
        # Zendesk
        "ZendeskTool": "zendesk_tool",
        "list_zendesk_tickets": "zendesk_tool",
        # Shopify
        "ShopifyTool": "shopify_tool",
        "list_shopify_products": "shopify_tool",
        # Brave Search
        "BraveSearchTool": "brave_search_tool",
        "brave_search": "brave_search_tool",
        # PubMed
        "PubMedTool": "pubmed_tool",
        "pubmed_search": "pubmed_tool",
        # SerpAPI
        "SerpAPITool": "serpapi_tool",
        "serpapi_search": "serpapi_tool",
        # SearxNG
        "SearxNGTool": "searxng_tool",
        "searxng_search": "searxng_tool",
        # LinkUp
        "LinkUpTool": "linkup_tool",
        "linkup_search": "linkup_tool",
        # Baidu Search
        "BaiduSearchTool": "baidu_search_tool",
        "baidu_search": "baidu_search_tool",
        # Valyu
        "ValyuTool": "valyu_tool",
        "valyu_search": "valyu_tool",
        # Gmail
        "GmailTool": "gmail_tool",
        "list_gmail_emails": "gmail_tool",
        # WhatsApp
        "WhatsAppTool": "whatsapp_tool",
        "send_whatsapp_message": "whatsapp_tool",
        # Zoom
        "ZoomTool": "zoom_tool",
        "list_zoom_meetings": "zoom_tool",
        # Webex
        "WebexTool": "webex_tool",
        "list_webex_rooms": "webex_tool",
        # X (Twitter)
        "XTool": "x_tool",
        "post_to_x": "x_tool",
        # Newspaper
        "NewspaperTool": "newspaper_tool",
        "extract_article": "newspaper_tool",
        # Trafilatura
        "TrafilaturaTool": "trafilatura_tool",
        "trafilatura_extract": "trafilatura_tool",
        # Spider
        "SpiderTool": "spider_tool",
        "spider_crawl": "spider_tool",
        # BrowserBase
        "BrowserBaseTool": "browserbase_tool",
        "browserbase_scrape": "browserbase_tool",
        # BrightData
        "BrightDataTool": "brightdata_tool",
        "brightdata_scrape": "brightdata_tool",
        # Oxylabs
        "OxylabsTool": "oxylabs_tool",
        "oxylabs_scrape": "oxylabs_tool",
        # ScrapeGraph
        "ScrapeGraphTool": "scrapegraph_tool",
        "scrapegraph_scrape": "scrapegraph_tool",
        # AgentQL
        "AgentQLTool": "agentql_tool",
        "agentql_query": "agentql_tool",
        # DynamoDB
        "DynamoDBTool": "dynamodb_tool",
        "dynamodb_scan": "dynamodb_tool",
        # Firestore
        "FirestoreTool": "firestore_tool",
        "firestore_list": "firestore_tool",
        # GCS
        "GCSTool": "gcs_tool",
        "gcs_list_objects": "gcs_tool",
        # BigQuery
        "BigQueryTool": "bigquery_tool",
        "bigquery_query": "bigquery_tool",
        # SingleStore
        "SingleStoreTool": "singlestore_tool",
        "singlestore_query": "singlestore_tool",
        # SurrealDB
        "SurrealDBTool": "surrealdb_tool",
        "surrealdb_query": "surrealdb_tool",
        # CSV
        "CSVTool": "csv_tool",
        "read_csv": "csv_tool",
        # Pandas
        "PandasTool": "pandas_tool",
        "pandas_read_csv": "pandas_tool",
        # Redshift
        "RedshiftTool": "redshift_tool",
        "redshift_query": "redshift_tool",
        # ElevenLabs
        "ElevenLabsTool": "elevenlabs_tool",
        "elevenlabs_speak": "elevenlabs_tool",
        # Replicate
        "ReplicateTool": "replicate_tool",
        "replicate_run": "replicate_tool",
        # Fal
        "FalTool": "fal_tool",
        "fal_run": "fal_tool",
        # Giphy
        "GiphyTool": "giphy_tool",
        "giphy_search": "giphy_tool",
        # Apify
        "ApifyTool": "apify_tool",
        "apify_run_actor": "apify_tool",
        # Airflow
        "AirflowTool": "airflow_tool",
        "list_airflow_dags": "airflow_tool",
        # AWS Lambda
        "AWSLambdaTool": "aws_lambda_tool",
        "invoke_lambda": "aws_lambda_tool",
        # AWS SES
        "AWSSESTool": "aws_ses_tool",
        "ses_send_email": "aws_ses_tool",
        # Resend
        "ResendTool": "resend_tool",
        "resend_send_email": "resend_tool",
        # ClickUp
        "ClickUpTool": "clickup_tool",
        "clickup_list_tasks": "clickup_tool",
        # Confluence
        "ConfluenceTool": "confluence_tool",
        "confluence_search": "confluence_tool",
        # Todoist
        "TodoistTool": "todoist_tool",
        "todoist_list_tasks": "todoist_tool",
        # Bitbucket
        "BitbucketTool": "bitbucket_tool",
        "bitbucket_list_repos": "bitbucket_tool",
        # OpenBB
        "OpenBBTool": "openbb_tool",
        "openbb_stock": "openbb_tool",
        # E2B
        "E2BTool": "e2b_tool",
        "e2b_run_code": "e2b_tool",
        # Sleep
        "SleepTool": "sleep_tool",
        "sleep_wait": "sleep_tool",
        # Python
        "PythonTool": "python_tool",
        "python_execute": "python_tool",
        # Mem0
        "Mem0Tool": "mem0_tool",
        "mem0_add": "mem0_tool",
        # PGVector
        "PGVectorTool": "pgvector_tool",
        "pgvector_search": "pgvector_tool",
        # Cassandra
        "CassandraTool": "cassandra_tool",
        "cassandra_query": "cassandra_tool",
        # ClickHouse
        "ClickHouseTool": "clickhouse_tool",
        "clickhouse_query": "clickhouse_tool",
        # Upstash
        "UpstashTool": "upstash_tool",
        "upstash_get": "upstash_tool",
        # Couchbase
        "CouchbaseTool": "couchbase_tool",
        "couchbase_get": "couchbase_tool",
        # Google Drive
        "GoogleDriveTool": "google_drive_tool",
        "list_drive_files": "google_drive_tool",
        # LumaLabs
        "LumaLabsTool": "lumalabs_tool",
        "lumalabs_generate": "lumalabs_tool",
        # OpenCV
        "OpenCVTool": "opencv_tool",
        "opencv_resize": "opencv_tool",
        # CalCom
        "CalComTool": "calcom_tool",
        "calcom_list_bookings": "calcom_tool",
        # Cartesia
        "CartesiaTool": "cartesia_tool",
        "cartesia_speak": "cartesia_tool",
        # Brandfetch
        "BrandfetchTool": "brandfetch_tool",
        "brandfetch_get_brand": "brandfetch_tool",
        # Daytona
        "DaytonaTool": "daytona_tool",
        "daytona_list_workspaces": "daytona_tool",
        # Composio
        "ComposioTool": "composio_tool",
        "composio_execute": "composio_tool",
        # JSON
        "JSONTool": "json_tool",
        "read_json": "json_tool",
        # Zep
        "ZepTool": "zep_tool",
        "zep_add_memory": "zep_tool",
        # WebBrowser
        "WebBrowserTool": "webbrowser_tool",
        "webbrowser_get_page": "webbrowser_tool",
        # WebTools
        "WebToolsTool": "webtools_tool",
        "webtools_fetch": "webtools_tool",
        # LocalFileSystem
        "LocalFileSystemTool": "local_filesystem_tool",
        "list_local_directory": "local_filesystem_tool",
        # Knowledge
        "KnowledgeTool": "knowledge_tool",
        "knowledge_search": "knowledge_tool",
        # Visualization
        "VisualizationTool": "visualization_tool",
        "create_bar_chart": "visualization_tool",
    }
    
    if name in tool_map:
        module_name = tool_map[name]
        from importlib import import_module
        module = import_module(f".{module_name}", __package__)
        return getattr(module, name)
    
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = [
    # Base classes
    "BaseTool",
    "ToolResult",
    "ToolValidationError",
    "validate_tool",
    # Decorator
    "tool",
    "FunctionTool",
    "is_tool",
    "get_tool_schema",
    # Email Tool
    "EmailTool",
    "send_email",
    "read_emails",
    "search_emails",
    # Slack Tool
    "SlackTool",
    "send_slack_message",
    "get_slack_channels",
    "get_slack_history",
    # Discord Tool
    "DiscordTool",
    "send_discord_webhook",
    "send_discord_message",
    # GitHub Tool
    "GitHubTool",
    "search_github_repos",
    "get_github_repo",
    "create_github_issue",
    # Image Tool
    "ImageTool",
    "generate_image",
    # Weather Tool
    "WeatherTool",
    "get_weather",
    "get_forecast",
    "get_air_quality",
    # YouTube Tool
    "YouTubeTool",
    "search_youtube",
    "get_youtube_video",
    "get_youtube_transcript",
    # TTS Tool
    "TTSTool",
    "text_to_speech",
    "list_tts_voices",
    # Telegram Tool
    "TelegramTool",
    "send_telegram_message",
    # Notion Tool
    "NotionTool",
    "search_notion",
    "create_notion_page",
    # PostgreSQL Tool
    "PostgresTool",
    "query_postgres",
    "list_postgres_tables",
    # Reddit Tool
    "RedditTool",
    "search_reddit",
    "get_reddit_hot",
    # Docker Tool
    "DockerTool",
    "list_docker_containers",
    "run_docker_container",
    # MySQL Tool
    "MySQLTool",
    "query_mysql",
    # SQLite Tool
    "SQLiteTool",
    "query_sqlite",
    # MongoDB Tool
    "MongoDBTool",
    "query_mongodb",
    # Redis Tool
    "RedisTool",
    "redis_get",
    "redis_set",
    # DuckDuckGo Tool
    "DuckDuckGoTool",
    "duckduckgo_search",
    # Tavily Tool
    "TavilyTool",
    "tavily_search",
    # Wikipedia Tool
    "WikipediaTool",
    "wikipedia_search",
    # ArXiv Tool
    "ArxivTool",
    "arxiv_search",
    # Calculator Tool
    "CalculatorTool",
    "calculate",
    # Shell Tool
    "ShellTool",
    "shell_execute",
    # File Tool
    "FileTool",
    "read_file",
    "write_file",
    # Firecrawl Tool
    "FirecrawlTool",
    "firecrawl_scrape",
    # Serper Tool
    "SerperTool",
    "serper_search",
    # Jina Tool
    "JinaTool",
    "jina_read",
    # Google Calendar Tool
    "GoogleCalendarTool",
    "list_calendar_events",
    # Google Sheets Tool
    "GoogleSheetsTool",
    "read_google_sheet",
    # Jira Tool
    "JiraTool",
    "jira_search",
    # Trello Tool
    "TrelloTool",
    "list_trello_boards",
    # YFinance Tool
    "YFinanceTool",
    "get_stock_price",
    # Pinecone Tool
    "PineconeTool",
    "pinecone_query",
    # Qdrant Tool
    "QdrantTool",
    "qdrant_search",
    # Chroma Tool
    "ChromaTool",
    "chroma_query",
    # HackerNews Tool
    "HackerNewsTool",
    "get_hackernews_top",
    # Twilio Tool
    "TwilioTool",
    "send_sms",
    # Spotify Tool
    "SpotifyTool",
    "spotify_search",
    # Linear Tool
    "LinearTool",
    "list_linear_issues",
    # Crawl4AI Tool
    "Crawl4AITool",
    "crawl4ai_crawl",
    # Exa Tool
    "ExaTool",
    "exa_search",
    # DuckDB Tool
    "DuckDBTool",
    "duckdb_query",
    # Neo4j Tool
    "Neo4jTool",
    "neo4j_query",
    # Weaviate Tool
    "WeaviateTool",
    "weaviate_search",
    # LanceDB Tool
    "LanceDBTool",
    "lancedb_search",
    # Supabase Tool
    "SupabaseTool",
    "supabase_select",
    # Milvus Tool
    "MilvusTool",
    "milvus_search",
    # Google Maps Tool
    "GoogleMapsTool",
    "geocode_address",
    # Zendesk Tool
    "ZendeskTool",
    "list_zendesk_tickets",
    # Shopify Tool
    "ShopifyTool",
    "list_shopify_products",
]
