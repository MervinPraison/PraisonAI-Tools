# PraisonAI Tools

Base classes for creating **custom tools** for [PraisonAI Agents](https://github.com/MervinPraison/PraisonAI).

[![PyPI version](https://badge.fury.io/py/praisonai-tools.svg)](https://badge.fury.io/py/praisonai-tools)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

## What is this package?

This package provides **base classes** (`BaseTool`, `@tool` decorator) for creating custom tools that work with PraisonAI Agents.

> **Note:** Common tools like Tavily, Exa, You.com, DuckDuckGo, Wikipedia, arXiv, and many more are **already built into `praisonaiagents`**. You don't need this package for those - just use them directly from `praisonaiagents.tools`.

**Use this package when you want to:**
- Create your own custom tools
- Build reusable tool plugins
- Distribute tools as pip packages

## Installation

```bash
pip install praisonai-tools
```

## Quick Start

### Creating Custom Tools

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

## Using with PraisonAI Agents

### Use Built-in Tools (Recommended)

For common tools, use them directly from `praisonaiagents`:

```python
from praisonaiagents import Agent
from praisonaiagents.tools import tavily_search, exa_search, wiki_search

agent = Agent(
    instructions="You are a research assistant",
    tools=[tavily_search, exa_search, wiki_search]
)

result = agent.start("Search for latest AI news")
```

### Use Custom Tools from praisonai-tools

For your own custom tools:

```python
from praisonaiagents import Agent
from praisonai_tools import tool

@tool
def my_custom_tool(query: str, limit: int = 10) -> dict:
    """My custom tool that does something special.
    
    Args:
        query: The search query
        limit: Maximum results to return
    """
    # Your custom implementation
    return {"results": [...]}

agent = Agent(
    instructions="You are an assistant",
    tools=[my_custom_tool]
)
```

## Built-in Tools in praisonaiagents

These tools are **already available** in `praisonaiagents.tools`:

| Category | Tools |
|----------|-------|
| **Search** | `tavily_search`, `exa_search`, `ydc_search`, `internet_search` (DuckDuckGo), `searxng_search` |
| **Wikipedia** | `wiki_search`, `wiki_summary`, `wiki_page` |
| **arXiv** | `search_arxiv`, `get_arxiv_paper`, `get_papers_by_author` |
| **News** | `get_article`, `get_news_sources`, `get_trending_topics` |
| **Web Crawling** | `crawl4ai`, `scrape_page`, `extract_links` |
| **Files** | `read_file`, `write_file`, `list_files` |
| **Data** | `read_csv`, `read_json`, `read_excel`, `read_yaml` |
| **Code** | `execute_code`, `analyze_code` |
| **Shell** | `execute_command`, `list_processes` |
| **Calculator** | `evaluate`, `solve_equation`, `convert_units` |
| **Finance** | `get_stock_price`, `get_stock_info` |

See [praisonaiagents documentation](https://docs.praison.ai) for full list.

## Testing

```bash
pip install praisonai-tools[dev]
pytest tests/test_base.py -v
```

## API Reference

### BaseTool

Abstract base class for creating tools:

```python
from praisonai_tools import BaseTool

class MyTool(BaseTool):
    name = "my_tool"           # Required
    description = "..."        # Required  
    version = "1.0.0"          # Optional
    
    def run(self, **kwargs):   # Required
        return result
```

### @tool Decorator

Convert functions to tools:

```python
from praisonai_tools import tool

@tool
def my_func(arg: str) -> str:
    """Description here."""
    return result

@tool(name="custom_name", description="Custom description")
def another_func(arg: str) -> str:
    return result
```

### Helper Functions

| Function | Description |
|----------|-------------|
| `is_tool(obj)` | Check if object is a tool |
| `get_tool_schema(obj)` | Get OpenAI-compatible schema |
| `validate_tool(obj)` | Validate tool configuration |

## License

MIT License - see [LICENSE](LICENSE) for details.

## Author

**Mervin Praison** - [GitHub](https://github.com/MervinPraison)

## Links

- [Documentation](https://docs.praison.ai/tools)
- [PyPI](https://pypi.org/project/praisonai-tools/)
- [GitHub](https://github.com/MervinPraison/PraisonAI-Tools)
- [Issues](https://github.com/MervinPraison/PraisonAI-Tools/issues)