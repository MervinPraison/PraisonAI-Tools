# PraisonAI Tools

A comprehensive toolkit for AI agents providing web search, content extraction, and research capabilities.

[![PyPI version](https://badge.fury.io/py/praisonai-tools.svg)](https://badge.fury.io/py/praisonai-tools)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

## Features

- **Tavily Tools** - AI-powered web search, content extraction, crawling, and site mapping
- **Exa Tools** - Neural search, content retrieval, similar page discovery, and AI answers
- **You.com Tools** - Unified web/news search, content extraction, and image search
- **Extensible Base Classes** - Create custom tools with `BaseTool` and `@tool` decorator

## Installation

```bash
# Basic installation (no external dependencies)
pip install praisonai-tools

# With specific tool support
pip install praisonai-tools[tavily]    # Tavily tools
pip install praisonai-tools[exa]       # Exa tools
pip install praisonai-tools[youdotcom] # You.com tools

# All tools
pip install praisonai-tools[all]

# Development
pip install praisonai-tools[dev]
```

## Quick Start

### Tavily Search

```python
from praisonai_tools import tavily_search

# Basic search
results = tavily_search("What is machine learning?")
print(results)

# Advanced search with answer
results = tavily_search(
    "Latest AI developments 2024",
    include_answer=True,
    topic="news",
    max_results=5
)
print(results["answer"])
```

### Exa Search

```python
from praisonai_tools import exa_search, exa_answer

# Search
results = exa_search("AI startups", num_results=5)

# Get AI-generated answer with citations
answer = exa_answer("What are the benefits of Python?")
print(answer["answer"])
print(answer["citations"])
```

### You.com Search

```python
from praisonai_tools import ydc_search, ydc_contents

# Unified search (web + news)
results = ydc_search("technology trends", count=10)

# Extract content from URLs
content = ydc_contents("https://example.com", format="markdown")
```

## Environment Variables

Set the following environment variables for the tools you want to use:

```bash
# Tavily (https://tavily.com)
export TAVILY_API_KEY=your_tavily_api_key

# Exa (https://exa.ai)
export EXA_API_KEY=your_exa_api_key

# You.com (https://you.com/api)
export YDC_API_KEY=your_ydc_api_key
```

## Tool Classes

For more control, use the tool classes directly:

### TavilyTools

```python
from praisonai_tools import TavilyTools

tavily = TavilyTools()

# Search
results = tavily.search("Python programming", max_results=5)

# Extract content from URLs
content = tavily.extract(["https://python.org", "https://docs.python.org"])

# Crawl a website
crawl_results = tavily.crawl("https://docs.python.org", max_depth=2, limit=20)

# Get site map
sitemap = tavily.map("https://docs.python.org", limit=50)
```

### ExaTools

```python
from praisonai_tools import ExaTools

exa = ExaTools()

# Basic search
results = exa.search("machine learning papers", category="research paper")

# Search with content
results = exa.search_and_contents("AI news", text=True, highlights=True)

# Find similar pages
similar = exa.find_similar("https://openai.com", num_results=5)

# Get answer with citations
answer = exa.answer("What is GPT-4?", text=True)
```

### YouTools

```python
from praisonai_tools import YouTools

you = YouTools()

# Unified search
results = you.search("latest tech news", count=10, freshness="week")

# Extract content
content = you.get_contents("https://example.com", format="markdown")

# Live news
news = you.live_news("AI developments", count=5)

# Image search
images = you.images("python programming")
```

## Creating Custom Tools

### Using BaseTool

```python
from praisonai_tools import BaseTool

class WeatherTool(BaseTool):
    name = "get_weather"
    description = "Get current weather for a location"
    
    def run(self, location: str, units: str = "celsius") -> dict:
        # Your implementation here
        return {"location": location, "temp": 22, "units": units}

# Use the tool
weather = WeatherTool()
result = weather.run(location="London")
print(result)

# Get OpenAI-compatible schema
schema = weather.get_schema()
```

### Using @tool Decorator

```python
from praisonai_tools import tool

@tool
def calculate(expression: str) -> float:
    """Evaluate a mathematical expression."""
    return eval(expression)

# Use directly
result = calculate(expression="2 + 2 * 3")
print(result)  # 8

# Get schema
schema = calculate.get_schema()
```

## API Reference

### Tavily Functions

| Function | Description |
|----------|-------------|
| `tavily_search(query, ...)` | Search the web with AI-powered ranking |
| `tavily_extract(urls, ...)` | Extract content from URLs |
| `tavily_crawl(url, ...)` | Crawl a website |
| `tavily_map(url, ...)` | Get a sitemap |

### Exa Functions

| Function | Description |
|----------|-------------|
| `exa_search(query, ...)` | Neural web search |
| `exa_search_contents(query, ...)` | Search with full content |
| `exa_find_similar(url, ...)` | Find similar pages |
| `exa_answer(query, ...)` | Get AI answer with citations |

### You.com Functions

| Function | Description |
|----------|-------------|
| `ydc_search(query, ...)` | Unified web and news search |
| `ydc_contents(urls, ...)` | Extract content from URLs |
| `ydc_news(query, ...)` | Live news search |
| `ydc_images(query)` | Image search |

## Testing

Run tests with real API keys:

```bash
# Install dev dependencies
pip install praisonai-tools[dev]

# Run all tests
pytest tests/ -v

# Run specific tool tests
pytest tests/test_tavily.py -v -m tavily
pytest tests/test_exa.py -v -m exa
pytest tests/test_youdotcom.py -v -m youdotcom

# Run base tests (no API keys needed)
pytest tests/test_base.py -v
```

## License

MIT License - see [LICENSE](LICENSE) for details.

## Author

**Mervin Praison** - [GitHub](https://github.com/MervinPraison)

## Links

- [Documentation](https://docs.praison.ai/tools)
- [PyPI](https://pypi.org/project/praisonai-tools/)
- [GitHub](https://github.com/MervinPraison/PraisonAI-Tools)
- [Issues](https://github.com/MervinPraison/PraisonAI-Tools/issues)