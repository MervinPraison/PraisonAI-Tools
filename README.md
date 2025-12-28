# PraisonAI Tools

Base classes for creating **custom tools** for [PraisonAI Agents](https://github.com/MervinPraison/PraisonAI).

[![PyPI version](https://badge.fury.io/py/praisonai-tools.svg)](https://badge.fury.io/py/praisonai-tools)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

## What is this package?

This package provides **base classes** (`BaseTool`, `@tool` decorator) for creating custom tools that work with PraisonAI Agents.

> **Note:** Common tools like Tavily, Exa, You.com, DuckDuckGo, Wikipedia, arXiv, and many more are **already built into `praisonaiagents`**. You don't need this package for those - just use them directly from `praisonaiagents.tools`.

## Installation

```bash
pip install praisonai-tools
```

---

# All Ways to Add Tools to PraisonAI Agents

PraisonAI Agents supports **8 different ways** to add tools. Choose the method that best fits your use case:

| Method | Best For | Complexity |
|--------|----------|------------|
| [1. Plain Python Functions](#1-plain-python-functions) | Quick custom tools | ⭐ Easy |
| [2. Built-in Tools](#2-built-in-tools) | Common operations | ⭐ Easy |
| [3. @tool Decorator](#3-tool-decorator) | Custom tools with metadata | ⭐ Easy |
| [4. BaseTool Class](#4-basetool-class) | Complex tools with state | ⭐⭐ Medium |
| [5. Pydantic Class with run()](#5-pydantic-class-with-run) | Validated tools | ⭐⭐ Medium |
| [6. LangChain Tools](#6-langchain-tools) | LangChain ecosystem | ⭐⭐ Medium |
| [7. CrewAI Tools](#7-crewai-tools) | CrewAI ecosystem | ⭐⭐ Medium |
| [8. MCP Tools](#8-mcp-model-context-protocol-tools) | External services | ⭐⭐⭐ Advanced |

---

## 1. Plain Python Functions

The simplest way - just write a function with type hints and docstring:

```python
from praisonaiagents import Agent

def search_web(query: str, max_results: int = 5) -> list:
    """Search the web for information.
    
    Args:
        query: The search query
        max_results: Maximum number of results to return
    """
    # Your implementation
    return [{"title": "Result 1", "url": "https://..."}]

def calculate(expression: str) -> float:
    """Evaluate a mathematical expression."""
    return eval(expression)

# Just pass the functions!
agent = Agent(
    instructions="You are a helpful assistant",
    tools=[search_web, calculate]
)

agent.start("Search for Python tutorials and calculate 15 * 7")
```

**How it works:** PraisonAI automatically:
- Extracts function name as tool name
- Uses docstring as description
- Generates JSON schema from type hints
- Parses Args section for parameter descriptions

---

## 2. Built-in Tools

Use pre-built tools from `praisonaiagents.tools`:

```python
from praisonaiagents import Agent
from praisonaiagents.tools import (
    # Search
    tavily_search,
    exa_search,
    internet_search,  # DuckDuckGo
    
    # Wikipedia
    wiki_search,
    wiki_summary,
    
    # News
    get_article,
    get_trending_topics,
    
    # Files
    read_file,
    write_file,
    
    # Code
    execute_code,
    
    # And many more...
)

agent = Agent(
    instructions="You are a research assistant",
    tools=[tavily_search, wiki_search, read_file]
)

agent.start("Search for AI news and save a summary to a file")
```

### Available Built-in Tools

| Category | Tools |
|----------|-------|
| **Search** | `tavily_search`, `exa_search`, `ydc_search`, `internet_search`, `searxng_search` |
| **Wikipedia** | `wiki_search`, `wiki_summary`, `wiki_page`, `wiki_random` |
| **arXiv** | `search_arxiv`, `get_arxiv_paper`, `get_papers_by_author`, `get_papers_by_category` |
| **News** | `get_article`, `get_news_sources`, `get_articles_from_source`, `get_trending_topics` |
| **Web Crawling** | `crawl4ai`, `scrape_page`, `extract_links`, `extract_text` |
| **Files** | `read_file`, `write_file`, `list_files`, `copy_file`, `move_file`, `delete_file` |
| **Data** | `read_csv`, `write_csv`, `read_json`, `write_json`, `read_excel`, `read_yaml` |
| **Code** | `execute_code`, `analyze_code`, `format_code`, `lint_code` |
| **Shell** | `execute_command`, `list_processes`, `kill_process`, `get_system_info` |
| **Calculator** | `evaluate`, `solve_equation`, `convert_units`, `calculate_statistics` |
| **Finance** | `get_stock_price`, `get_stock_info`, `get_historical_data` |
| **Database** | `query` (DuckDB), `insert_document`, `find_documents` (MongoDB) |

---

## 3. @tool Decorator

Use the `@tool` decorator for custom tools with metadata:

```python
from praisonaiagents import Agent
from praisonai_tools import tool

@tool
def get_weather(location: str, units: str = "celsius") -> dict:
    """Get current weather for a location.
    
    Args:
        location: City name or coordinates
        units: Temperature units (celsius/fahrenheit)
    """
    # Your implementation
    return {"temp": 22, "condition": "sunny", "location": location}

@tool(name="custom_search", description="Search with custom parameters")
def my_search(query: str, limit: int = 10) -> list:
    """Custom search implementation."""
    return [{"result": query}]

agent = Agent(
    instructions="You are a weather assistant",
    tools=[get_weather, my_search]
)

agent.start("What's the weather in London?")
```

---

## 4. BaseTool Class

For complex tools with state, validation, or multiple methods:

```python
from praisonaiagents import Agent
from praisonai_tools import BaseTool

class DatabaseTool(BaseTool):
    name = "database_query"
    description = "Query a database and return results"
    
    def __init__(self, connection_string: str):
        self.connection_string = connection_string
        self._connection = None
        super().__init__()
    
    def run(self, query: str, limit: int = 100) -> list:
        """Execute a database query.
        
        Args:
            query: SQL query to execute
            limit: Maximum rows to return
        """
        # Your implementation
        return [{"id": 1, "name": "Example"}]

# Create instance with configuration
db_tool = DatabaseTool(connection_string="postgresql://...")

agent = Agent(
    instructions="You are a data analyst",
    tools=[db_tool]
)

agent.start("Query the users table for active users")
```

---

## 5. Pydantic Class with run()

Use Pydantic for validated tools with type checking:

```python
from praisonaiagents import Agent
from pydantic import BaseModel, Field
from typing import Optional
import requests

class APISearchTool(BaseModel):
    """Search tool using an external API."""
    
    api_url: str = "https://api.example.com/search"
    api_key: Optional[str] = None
    max_results: int = Field(default=10, ge=1, le=100)
    
    def run(self, query: str) -> dict:
        """Execute search query.
        
        Args:
            query: Search query string
        """
        headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
        response = requests.get(
            self.api_url,
            params={"q": query, "limit": self.max_results},
            headers=headers
        )
        return response.json()

# Pass the class (not instance) - PraisonAI will instantiate it
agent = Agent(
    instructions="You are a search assistant",
    tools=[APISearchTool]
)

agent.start("Search for machine learning tutorials")
```

---

## 6. LangChain Tools

Use any LangChain tool directly:

```python
from praisonaiagents import Agent
from langchain_community.tools import YouTubeSearchTool, DuckDuckGoSearchRun
from langchain_community.utilities import WikipediaAPIWrapper

# Method 1: Pass LangChain tool classes directly
agent = Agent(
    instructions="You are a research assistant",
    tools=[YouTubeSearchTool, WikipediaAPIWrapper]
)

agent.start("Find YouTube videos about Python and search Wikipedia for its history")
```

### Wrapping LangChain Tools

For more control, wrap LangChain tools in functions:

```python
from praisonaiagents import Agent
from langchain_community.tools import YouTubeSearchTool
from langchain_community.utilities import WikipediaAPIWrapper

def youtube_search(query: str, max_results: int = 5) -> str:
    """Search YouTube for videos.
    
    Args:
        query: Search query
        max_results: Number of results
    """
    yt = YouTubeSearchTool()
    return yt.run(f"{query}, {max_results}")

def wikipedia_search(query: str) -> str:
    """Search Wikipedia for information.
    
    Args:
        query: Search query
    """
    wiki = WikipediaAPIWrapper()
    return wiki.run(query)

agent = Agent(
    instructions="You are a research assistant",
    tools=[youtube_search, wikipedia_search]
)

agent.start("Find videos about AI and get Wikipedia info on machine learning")
```

### Using LangChain Toolkits

```python
from praisonaiagents import Agent
from langchain_agentql.tools import ExtractWebDataTool

def extract_web_data(url: str, query: str) -> dict:
    """Extract structured data from a webpage.
    
    Args:
        url: URL to extract from
        query: What data to extract
    """
    tool = ExtractWebDataTool()
    return tool.invoke({"url": url, "prompt": query})

agent = Agent(
    instructions="You are a web scraping assistant",
    tools=[extract_web_data]
)

agent.start("Extract product names and prices from https://example.com/products")
```

---

## 7. CrewAI Tools

Use CrewAI tools (classes with `_run` method):

```python
from praisonaiagents import Agent

# CrewAI-style tool class
class CrewAISearchTool:
    """A CrewAI-compatible search tool."""
    
    name = "web_search"
    description = "Search the web for information"
    
    def _run(self, query: str) -> str:
        """Execute the search.
        
        Args:
            query: Search query
        """
        # Your implementation
        return f"Results for: {query}"

# Pass the class - PraisonAI detects _run method
agent = Agent(
    instructions="You are a search assistant",
    tools=[CrewAISearchTool]
)

agent.start("Search for latest tech news")
```

---

## 8. MCP (Model Context Protocol) Tools

Use external tools via MCP servers:

### Filesystem MCP

```python
from praisonaiagents import Agent, MCP

agent = Agent(
    instructions="You are a file manager assistant",
    tools=MCP("npx -y @modelcontextprotocol/server-filesystem", 
              args=["/Users/username/Documents"])
)

agent.start("List all Python files in the Documents folder")
```

### Time MCP

```python
from praisonaiagents import Agent, MCP

agent = Agent(
    instructions="You are a time assistant",
    tools=MCP("python -m mcp_server_time --local-timezone=America/New_York")
)

agent.start("What time is it in New York? Convert to UTC.")
```

### GitHub MCP

```python
from praisonaiagents import Agent, MCP
import os

agent = Agent(
    instructions="You are a GitHub assistant",
    tools=MCP("npx -y @modelcontextprotocol/server-github",
              env={"GITHUB_TOKEN": os.environ["GITHUB_TOKEN"]})
)

agent.start("List my recent repositories")
```

### Multiple MCP Servers

```python
from praisonaiagents import Agent, MCP

agent = Agent(
    instructions="You are a multi-capable assistant",
    tools=[
        MCP("npx -y @modelcontextprotocol/server-filesystem", args=["/tmp"]),
        MCP("python -m mcp_server_time"),
        my_custom_function,  # Can mix with other tool types!
    ]
)

agent.start("Create a file with the current timestamp")
```

---

## Combining Multiple Tool Types

You can mix and match all tool types:

```python
from praisonaiagents import Agent, MCP
from praisonaiagents.tools import tavily_search, wiki_search
from praisonai_tools import tool, BaseTool
from langchain_community.tools import YouTubeSearchTool

# Plain function
def calculate(expression: str) -> float:
    """Calculate a math expression."""
    return eval(expression)

# @tool decorator
@tool
def format_output(data: dict) -> str:
    """Format data as a nice string."""
    return str(data)

# BaseTool class
class CustomTool(BaseTool):
    name = "custom"
    description = "A custom tool"
    def run(self, input: str) -> str:
        return f"Processed: {input}"

# Combine everything!
agent = Agent(
    instructions="You are a super assistant with many capabilities",
    tools=[
        # Built-in tools
        tavily_search,
        wiki_search,
        
        # Plain function
        calculate,
        
        # Decorated function
        format_output,
        
        # BaseTool instance
        CustomTool(),
        
        # LangChain tool
        YouTubeSearchTool,
        
        # MCP server
        MCP("python -m mcp_server_time"),
    ]
)

agent.start("Search for AI news, find related YouTube videos, and calculate 2^10")
```

---

## Creating Distributable Tool Packages

To create a pip-installable tool package:

### 1. Create your tool module

```python
# my_tools/weather.py
from praisonai_tools import BaseTool

class WeatherTool(BaseTool):
    name = "get_weather"
    description = "Get weather for a location"
    
    def run(self, location: str) -> dict:
        # Implementation
        return {"temp": 22, "location": location}

# Convenience instance
weather_tool = WeatherTool()
```

### 2. Create pyproject.toml

```toml
[project]
name = "my-weather-tools"
version = "0.1.0"
dependencies = ["praisonai-tools"]

[project.entry-points."praisonaiagents.tools"]
weather = "my_tools.weather:WeatherTool"
```

### 3. Users can then:

```python
from praisonaiagents import Agent
from my_tools.weather import weather_tool

agent = Agent(
    instructions="Weather assistant",
    tools=[weather_tool]
)
```

---

## 9. Video Editing Tools

```bash
python -m praisonai_tools.video probe input.mp4
```

```bash
python -m praisonai_tools.video transcribe input.mp4 --output transcript.srt
```

```bash
python -m praisonai_tools.video edit input.mp4 --output edited.mp4 --preset podcast
```

```bash
python -m praisonai_tools.video edit input.mp4 --output edited.mp4 --preset podcast -v
```

```bash
python -m praisonai_tools.video render input.mp4 --timeline plan.json --output output.mp4
```

| Feature | Code Docs | CLI Docs |
|---------|-----------|----------|
| Video Module | [docs/video-module.md](docs/video-module.md) | [docs/video-cli.md](docs/video-cli.md) |

---

## 10. Ready-to-Use Tools from praisonai-tools

This package also includes ready-to-use tools for common integrations:

### Communication Tools

```python
from praisonai_tools import EmailTool, SlackTool, DiscordTool

# Email (Gmail, Outlook, Yahoo)
email = EmailTool(provider="gmail")
email.send(to="user@example.com", subject="Hello", body="Message")
emails = email.read(limit=10)

# Slack
slack = SlackTool()  # Uses SLACK_TOKEN env var
slack.send_message(channel="#general", text="Hello from AI!")
channels = slack.list_channels()

# Discord (webhook or bot)
discord = DiscordTool(webhook_url="https://discord.com/api/webhooks/...")
discord.send_webhook(content="Hello!", embed=DiscordTool.create_embed(title="Alert"))
```

### Developer Tools

```python
from praisonai_tools import GitHubTool

github = GitHubTool()  # Uses GITHUB_TOKEN env var
repos = github.search_repos("machine learning python", limit=10)
github.create_issue(repo="owner/repo", title="Bug", body="Description")
prs = github.list_pull_requests(repo="owner/repo")
```

### AI/Media Tools

```python
from praisonai_tools import ImageTool, TTSTool, YouTubeTool

# Image Generation (DALL-E)
img = ImageTool(model="dall-e-3", quality="hd")
result = img.generate("A sunset over mountains")

# Text-to-Speech (OpenAI or ElevenLabs)
tts = TTSTool(provider="openai", voice="nova")
tts.speak("Hello world!", output_path="output.mp3")

# YouTube
yt = YouTubeTool()  # Uses YOUTUBE_API_KEY env var
videos = yt.search("python tutorial", limit=5)
transcript = yt.get_transcript("dQw4w9WgXcQ")
```

### Data Tools

```python
from praisonai_tools import WeatherTool

weather = WeatherTool(units="metric")  # Uses OPENWEATHER_API_KEY env var
current = weather.get_current("London")
forecast = weather.get_forecast("New York", days=5)
air = weather.get_air_quality("Tokyo")
```

### Environment Variables

| Tool | Required Environment Variable |
|------|------------------------------|
| EmailTool | `EMAIL_USERNAME`, `EMAIL_PASSWORD` |
| SlackTool | `SLACK_TOKEN` |
| DiscordTool | `DISCORD_BOT_TOKEN` or `DISCORD_WEBHOOK_URL` |
| GitHubTool | `GITHUB_TOKEN` |
| ImageTool | `OPENAI_API_KEY` |
| TTSTool | `OPENAI_API_KEY` or `ELEVENLABS_API_KEY` |
| YouTubeTool | `YOUTUBE_API_KEY` |
| WeatherTool | `OPENWEATHER_API_KEY` |

### Using with PraisonAI Agents

```python
from praisonaiagents import Agent
from praisonai_tools import EmailTool, SlackTool, GitHubTool, WeatherTool

agent = Agent(
    instructions="You are a helpful assistant with access to email, slack, github, and weather",
    tools=[
        EmailTool(provider="gmail"),
        SlackTool(),
        GitHubTool(),
        WeatherTool(),
    ]
)

agent.start("Check the weather in London and send a Slack message about it")
```

---

## Contributing

We welcome contributions! To add a new tool:

1. Fork this repository
2. Create your tool using `BaseTool` or `@tool` decorator
3. Add tests in `tests/`
4. Submit a pull request

---

## Testing

```bash
pip install praisonai-tools[dev]
pytest tests/ -v
```

---

## License

MIT License - see [LICENSE](LICENSE) for details.

## Author

**Mervin Praison** - [GitHub](https://github.com/MervinPraison)

## Links

- [PraisonAI Documentation](https://docs.praison.ai)
- [PraisonAI Agents](https://github.com/MervinPraison/PraisonAI)
- [PyPI](https://pypi.org/project/praisonai-tools/)
- [GitHub](https://github.com/MervinPraison/PraisonAI-Tools)
- [Issues](https://github.com/MervinPraison/PraisonAI-Tools/issues)