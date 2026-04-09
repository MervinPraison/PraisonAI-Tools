# Joy Trust Integration for PraisonAI

Native Joy Trust Network integration for secure agent handoffs in PraisonAI.

## Overview

The Joy Trust integration provides automatic trust verification for agent handoffs, ensuring that tasks are only delegated to verified, trustworthy agents. This integration builds on the existing Joy Trust Network documentation and provides seamless, zero-configuration security for multi-agent workflows.

## Features

- **Automatic Trust Verification**: Environment variable configuration for seamless integration
- **Handoff Safety Checks**: Verify agent trustworthiness before delegation
- **Decorator-based Security**: `@trust_verified_handoff` decorator for secure functions
- **Configurable Thresholds**: Set minimum trust scores for different use cases
- **Caching**: Built-in result caching to reduce API calls
- **Fallback Handling**: Graceful degradation when trust verification fails

## Quick Start

### 1. Environment Variable Configuration

```bash
# Enable trust verification for all agents
export PRAISONAI_TRUST_PROVIDER=joy

# Set minimum trust score threshold (default: 3.0)
export PRAISONAI_TRUST_MIN_SCORE=3.5

# Enable automatic handoff verification (default: true)
export PRAISONAI_TRUST_AUTO_VERIFY=true

# Optional: Set Joy Trust API key for enhanced features
export JOY_TRUST_API_KEY=your_api_key_here
```

### 2. Basic Usage

```python
from praisonai_tools import check_trust_score, verify_handoff_safety

# Check an agent's trust score
result = check_trust_score("researcher_agent", min_score=3.0)
print(f"Trust Score: {result['trust_score']}")
print(f"Safe to use: {result['meets_threshold']}")

# Verify handoff safety with recommendations
verification = verify_handoff_safety("data_analyst", min_score=3.5)
print(f"Handoff Safe: {verification['handoff_safe']}")
print(f"Recommendation: {verification['recommendation']}")
```

### 3. Decorator-based Security

```python
from praisonai_tools import trust_verified_handoff

@trust_verified_handoff(min_score=4.0)
def delegate_analysis_task(agent_name: str, data: dict):
    # This function only executes if the agent meets trust requirements
    return perform_delegation(agent_name, data)

# The decorator automatically checks trust before execution
result = delegate_analysis_task("expert_analyst", {"data": "..."})
```

## API Reference

### Functions

#### `check_trust_score(agent_name: str, min_score: float = 3.0) -> dict`

Check an agent's trust score on the Joy Trust Network.

**Parameters:**
- `agent_name`: Name/identifier of the agent to check
- `min_score`: Minimum acceptable trust score

**Returns:**
```python
{
    "agent_name": str,
    "trust_score": float,
    "verified": bool,
    "meets_threshold": bool,
    "threshold_used": float,
    "reputation": dict,
    "recommendations": int,
    "error": str | None
}
```

#### `verify_handoff_safety(agent_name: str, min_score: float = 3.0) -> dict`

Verify if it's safe to hand off to the specified agent.

**Parameters:**
- `agent_name`: Target agent for handoff
- `min_score`: Minimum acceptable trust score

**Returns:**
```python
{
    "agent_name": str,
    "trust_score": float,
    "verified": bool,
    "handoff_safe": bool,
    "recommendation": str,
    "threshold_used": float,
    "verification_time": float,
    "error": str | None
}
```

#### `trust_verified_handoff(min_score: float = 3.0)`

Decorator for automatic trust verification before function execution.

**Parameters:**
- `min_score`: Minimum trust score required

**Usage:**
```python
@trust_verified_handoff(min_score=3.5)
def my_delegation_function(agent_name, task):
    return delegate_task(agent_name, task)
```

#### `is_trust_verification_enabled() -> bool`

Check if trust verification is enabled via environment variables.

#### `get_trust_config() -> TrustConfig`

Get current trust configuration from environment variables.

### Classes

#### `JoyTrustTool`

Enhanced tool class for Joy Trust Network verification.

```python
from praisonai_tools import JoyTrustTool

tool = JoyTrustTool(api_key="optional_key")
result = tool.check_trust("agent_name")
```

#### `TrustConfig`

Configuration dataclass for Joy Trust integration.

```python
from praisonai_tools.tools.joy_trust_tool import TrustConfig

config = TrustConfig.from_env()
print(f"Enabled: {config.enabled}")
print(f"Min Score: {config.min_score}")
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `PRAISONAI_TRUST_PROVIDER` | Set to 'joy' to enable trust verification | None |
| `PRAISONAI_TRUST_MIN_SCORE` | Minimum trust score threshold | 3.0 |
| `PRAISONAI_TRUST_AUTO_VERIFY` | Enable automatic handoff verification | true |
| `PRAISONAI_TRUST_TIMEOUT` | Request timeout in seconds | 10.0 |
| `PRAISONAI_TRUST_CACHE_DURATION` | Cache duration in seconds | 300 |
| `PRAISONAI_TRUST_FALLBACK` | Allow fallback on errors | true |
| `JOY_TRUST_API_KEY` | Joy Trust API key (optional) | None |

## Trust Score Ranges

The Joy Trust Network uses a 0-5 scale for trust scores:

- **4.5-5.0**: Excellent - Highly trusted, verified agents
- **3.5-4.4**: Good - Reliable agents with good reputation
- **2.5-3.4**: Moderate - Acceptable with caution
- **1.0-2.4**: Low - Not recommended for important tasks
- **0.0-0.9**: Very Low - Strongly discouraged

## Integration Patterns

### 1. Workflow-level Integration

```python
import os
from praisonai_tools import verify_handoff_safety

# Enable trust verification
os.environ['PRAISONAI_TRUST_PROVIDER'] = 'joy'

def secure_workflow(agents: list, min_score: float = 3.0):
    trusted_agents = []
    
    for agent in agents:
        verification = verify_handoff_safety(agent['name'], min_score)
        if verification['handoff_safe']:
            trusted_agents.append(agent)
        else:
            print(f"⚠️ Agent {agent['name']} failed trust check")
    
    return trusted_agents
```

### 2. Conditional Trust Checking

```python
from praisonai_tools import is_trust_verification_enabled, check_trust_score

def delegate_with_optional_trust(agent_name: str, task: str):
    if is_trust_verification_enabled():
        trust_result = check_trust_score(agent_name)
        if not trust_result['meets_threshold']:
            return {"error": f"Agent {agent_name} doesn't meet trust requirements"}
    
    return perform_delegation(agent_name, task)
```

### 3. Custom Trust Policies

```python
from praisonai_tools import JoyTrustTool
from praisonai_tools.tools.joy_trust_tool import TrustConfig

# Create custom configuration
custom_config = TrustConfig(
    enabled=True,
    min_score=4.0,  # High security requirement
    timeout_seconds=5.0,  # Fast timeout
    fallback_on_error=False  # Strict mode
)

tool = JoyTrustTool(config=custom_config)
result = tool.verify_handoff_safety("critical_agent")
```

## Error Handling

The integration provides robust error handling:

```python
from praisonai_tools import check_trust_score

result = check_trust_score("unknown_agent")

if result['error']:
    print(f"Trust check failed: {result['error']}")
    
    if result.get('fallback_used'):
        print("Using fallback behavior")
    else:
        print("Strict mode - blocking delegation")
else:
    print(f"Trust verification successful: {result['trust_score']}")
```

## Best Practices

1. **Start with moderate thresholds** (3.0-3.5) and adjust based on your security needs
2. **Use environment variables** for configuration to avoid hardcoding values
3. **Enable caching** in production to reduce API calls and improve performance
4. **Set appropriate timeouts** based on your application's requirements
5. **Use fallback mode** for non-critical operations to maintain availability
6. **Monitor trust scores** and update agent permissions accordingly

## Troubleshooting

### Common Issues

1. **"httpx is required" error**: Install httpx with `pip install httpx` or `pip install praisonai-tools[marketplace]`
2. **Connection timeouts**: Increase `PRAISONAI_TRUST_TIMEOUT` value
3. **False negatives**: Check if agent names match Joy Trust Network entries exactly
4. **API rate limits**: Enable caching with `PRAISONAI_TRUST_CACHE_DURATION`

### Debug Mode

Enable debug logging to troubleshoot issues:

```python
import logging
logging.basicConfig(level=logging.DEBUG)

from praisonai_tools import check_trust_score
result = check_trust_score("debug_agent")
```

## Contributing

To contribute to the Joy Trust integration:

1. Fork the PraisonAI-Tools repository
2. Create a feature branch
3. Add tests for new functionality
4. Submit a pull request

## Support

- **Documentation**: [Joy Trust Network Docs](https://docs.praison.ai/joy-trust-network)
- **Issues**: [PraisonAI-Tools Issues](https://github.com/MervinPraison/PraisonAI-Tools/issues)
- **Community**: [PraisonAI Discord](https://discord.gg/praisonai)