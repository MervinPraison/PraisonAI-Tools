# NEXUS Prediction Market Integration

This document provides comprehensive information about integrating the NEXUS prediction market API with PraisonAI agents.

## Overview

NEXUS provides live Kalshi/Polymarket prediction market data and arbitrage opportunities through a validated API. The integration allows PraisonAI agents to:

- Access real-time prediction market data
- Identify arbitrage opportunities between markets
- Analyze market sentiment and trends
- Build sophisticated trading and analysis workflows

## API Information

### Endpoints

- **Free Market Data**: `/kalshi?market={market_name}`
- **Paid Arbitrage Analysis**: `/arb/check?markets={market1,market2}` ($0.02 USDC on eip155:8453)
- **Agent Metadata**: `/.well-known/agent.json`

### Validation

The API is fully validated on Agentic Market:
- **Validation URL**: https://agentic.market/validate?url=https://nexus-agent-xa12.onrender.com/arb/check
- **API Card**: https://nexus-agent-xa12.onrender.com/.well-known/agent.json

### Usage Tracking

Include the `X-NEXUS-Source` header to track per-source call volume:
```
X-NEXUS-Source: your-bot-name
```

## Installation

```bash
pip install praisonai-tools
```

## Quick Start

### Basic Usage

```python
from praisonai_tools.tools import NexusPredictionMarketTool

# Initialize the tool
nexus = NexusPredictionMarketTool(source_name="my-agent")

# Get market data
fed_data = nexus.get_market_data("Fed")
print(fed_data)

# Check arbitrage opportunities (paid)
arb_data = nexus.check_arbitrage_opportunities(["Fed", "BTC"])
print(arb_data)
```

### Agent Integration

```python
from praisonaiagents import Agent, tool
from praisonai_tools.tools import nexus_prediction_market_tool

@tool
def get_market_data(market: str) -> str:
    """Get prediction market data."""
    return nexus_prediction_market_tool("get_market_data", market=market)

agent = Agent(
    name="MarketAnalyst",
    tools=[get_market_data],
    instructions="Analyze prediction markets using NEXUS data."
)

response = agent.start("What do Fed rate predictions show?")
```

## Features

### Free Features

1. **Market Data Queries**
   - Real-time price data
   - Volume and liquidity information
   - Market sentiment indicators
   - Historical trends

2. **Agent Metadata**
   - API capabilities and endpoints
   - Service status and version info
   - Usage guidelines

### Paid Features

1. **Arbitrage Analysis** ($0.02 USDC on eip155:8453)
   - Cross-market opportunity detection
   - Profit potential calculations
   - Risk assessment
   - Execution recommendations

## Supported Markets

Common market identifiers include:

- `Fed` - Federal Reserve interest rate predictions
- `BTC` - Bitcoin price predictions
- `Election` - Political election outcomes
- `ETH` - Ethereum price predictions
- `Inflation` - Inflation rate predictions

*Note: Market availability may vary. Check current markets via the API.*

## API Reference

### NexusPredictionMarketTool Class

```python
class NexusPredictionMarketTool:
    def __init__(self, source_name: Optional[str] = None, api_key: Optional[str] = None)
    def get_market_data(self, market: str) -> Dict[str, Any]
    def check_arbitrage_opportunities(self, markets: List[str]) -> Dict[str, Any]
    def get_agent_info(self) -> Dict[str, Any]
    def run(self, action: str, market: Optional[str] = None, markets: Optional[List[str]] = None) -> str
```

### Function Interface

```python
def nexus_prediction_market_tool(
    action: str,
    market: Optional[str] = None,
    markets: Optional[List[str]] = None,
    source_name: Optional[str] = None
) -> str
```

## Examples

### Market Analysis Agent

```python
from praisonaiagents import Agent
from praisonai_tools.tools import NexusPredictionMarketTool

class MarketAnalysisAgent:
    def __init__(self):
        self.nexus = NexusPredictionMarketTool(source_name="analysis-bot")
        
    def analyze_market_sentiment(self, market):
        """Analyze market sentiment for a specific prediction market."""
        data = self.nexus.get_market_data(market)
        
        if data["success"]:
            market_data = data["data"]
            # Analyze price, volume, trends etc.
            return f"Market sentiment for {market}: {self.interpret_data(market_data)}"
        else:
            return f"Error getting data: {data['error']}"
    
    def interpret_data(self, data):
        """Custom logic to interpret market data."""
        # Implementation specific to your analysis needs
        pass
```

### Multi-Agent Workflow

```python
from praisonaiagents import Agent, AgentTeam, Task

# Data collector agent
collector = Agent(
    name="DataCollector",
    tools=[get_market_data],
    instructions="Collect prediction market data from NEXUS."
)

# Analyst agent
analyst = Agent(
    name="Analyst", 
    instructions="Analyze market data and provide insights."
)

# Create workflow
team = AgentTeam(agents=[collector, analyst])

# Define tasks
collect_task = Task(
    name="collect_data",
    description="Collect data for Fed and BTC markets",
    agent=collector
)

analyze_task = Task(
    name="analyze_trends",
    description="Analyze the collected market data",
    agent=analyst,
    dependencies=[collect_task]
)

# Execute workflow
results = team.run(tasks=[collect_task, analyze_task])
```

## Error Handling

The tool provides comprehensive error handling for common scenarios:

### Network Errors
```python
{
    "success": False,
    "error": "Failed to fetch market data: Connection timeout",
    "market": "Fed"
}
```

### Payment Required (Arbitrage Features)
```python
{
    "success": False,
    "error": "Payment required for arbitrage analysis. Cost: $0.02 USDC on eip155:8453",
    "markets": ["Fed", "BTC"],
    "payment_info": "This feature requires payment on eip155:8453 blockchain"
}
```

### Invalid Parameters
```python
{
    "success": False,
    "error": "Market parameter required for get_market_data action"
}
```

## Best Practices

### 1. Source Identification
Always set a descriptive source name for tracking:
```python
nexus = NexusPredictionMarketTool(source_name="trading-bot-v1")
```

### 2. Error Handling
Always check the `success` field before processing results:
```python
result = nexus.get_market_data("Fed")
if result["success"]:
    data = result["data"]
    # Process data
else:
    print(f"Error: {result['error']}")
```

### 3. Rate Limiting
Implement appropriate delays between requests to avoid overwhelming the API:
```python
import time
import asyncio

async def batch_collect_data(markets):
    data = {}
    for market in markets:
        result = nexus.get_market_data(market)
        data[market] = result
        await asyncio.sleep(1)  # 1 second delay between requests
    return data
```

### 4. Caching
Cache results for frequently accessed data:
```python
from functools import lru_cache
import time

@lru_cache(maxsize=100)
def cached_market_data(market, timestamp):
    return nexus.get_market_data(market)

def get_cached_data(market, cache_duration=300):  # 5 minutes
    timestamp = int(time.time() // cache_duration)
    return cached_market_data(market, timestamp)
```

## Security Considerations

### 1. API Key Management
If using paid features, securely manage your API keys:
```python
import os
api_key = os.getenv("NEXUS_API_KEY")
nexus = NexusPredictionMarketTool(api_key=api_key)
```

### 2. Input Validation
Validate market identifiers before making requests:
```python
VALID_MARKETS = ["Fed", "BTC", "ETH", "Election", "Inflation"]

def validate_market(market):
    if market not in VALID_MARKETS:
        raise ValueError(f"Invalid market: {market}")
    return market
```

### 3. Rate Limiting
Implement client-side rate limiting to prevent abuse:
```python
from time import time, sleep

class RateLimiter:
    def __init__(self, max_calls_per_minute=60):
        self.max_calls = max_calls_per_minute
        self.calls = []
    
    def wait_if_needed(self):
        now = time()
        self.calls = [call_time for call_time in self.calls if now - call_time < 60]
        
        if len(self.calls) >= self.max_calls:
            sleep(1)
        
        self.calls.append(now)
```

## Troubleshooting

### Common Issues

1. **Connection Timeout**
   - Check internet connectivity
   - Verify the API endpoint is accessible
   - Implement retry logic with exponential backoff

2. **Invalid Market Identifier**
   - Verify the market name is correct
   - Check available markets via agent info endpoint
   - Use exact case-sensitive market names

3. **Payment Required Errors**
   - Ensure you have sufficient USDC balance on eip155:8453
   - Verify payment setup for arbitrage features
   - Contact NEXUS support if payment issues persist

4. **JSON Decode Errors**
   - Check API response format
   - Verify the endpoint returned valid JSON
   - Implement fallback error handling

### Debug Mode

Enable debug logging to troubleshoot issues:
```python
import logging
logging.basicConfig(level=logging.DEBUG)

nexus = NexusPredictionMarketTool(source_name="debug-agent")
# Requests will now be logged with full details
```

## Support and Resources

- **API Documentation**: https://nexus-agent-xa12.onrender.com/.well-known/agent.json
- **Validation Check**: https://agentic.market/validate?url=https://nexus-agent-xa12.onrender.com/arb/check
- **PraisonAI Documentation**: https://docs.praison.ai
- **Issue Tracking**: Report issues via GitHub issues in the PraisonAI-Tools repository

## Contributing

To contribute improvements or report bugs:

1. Fork the PraisonAI-Tools repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## License

This tool is part of the PraisonAI-Tools package and follows the same licensing terms.