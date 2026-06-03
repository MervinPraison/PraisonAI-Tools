# SwarmScore Integration for PraisonAI

SwarmScore is a portable trust rating system for AI agents that provides cryptographically signed reputation scores based on verified execution history. This integration allows PraisonAI agents to leverage trust ratings for enhanced security and decision-making.

## Overview

SwarmScore provides:
- **Portable Trust Ratings**: Cryptographically signed scores that travel with your agent across platforms
- **Verified Execution History**: Trust based on actual performance, not self-reported metrics
- **Consistency Tracking**: 80 jobs at 95% success rate beats 1 job at 100%
- **Agent-to-Agent Discovery**: Machine-readable trust data for autonomous agent interactions

## Installation

```bash
pip install praisonai-tools[swarmscore]
# or
pip install praisonai-tools requests
```

## Quick Start

### Basic Usage

```python
from praisonai_tools.tools import SwarmScoreTool

# Initialize the tool
swarmscore = SwarmScoreTool()

# Load your agent's trust score
result = swarmscore.load_swarmscore("your-agent-slug")

if result.success:
    score_data = result.data
    print(f"Trust Score: {score_data['score']}")
    print(f"Trust Tier: {score_data['tier']}")
    print(f"Success Rate: {score_data['success_rate']}%")
else:
    print(f"Error: {result.error}")
```

### Standalone Functions

```python
from praisonai_tools.tools import (
    load_swarmscore_by_slug,
    verify_swarmscore_freshness,
    get_agent_discovery_manifest
)

# Load score data
try:
    score_data = load_swarmscore_by_slug("your-agent-slug")
    print(f"Score: {score_data['score']}")
except Exception as e:
    print(f"Failed to load score: {e}")

# Verify score freshness
try:
    verification = verify_swarmscore_freshness(score_data['verify_payload'])
    print(f"Verification: {verification}")
except Exception as e:
    print(f"Verification failed: {e}")

# Get discovery manifest
try:
    manifest = get_agent_discovery_manifest()
    print(f"Discovery data: {manifest}")
except Exception as e:
    print(f"Failed to get manifest: {e}")
```

## Integration Patterns

### 1. Trust-Based Decision Making

```python
from praisonai_tools.tools import SwarmScoreTool

def execute_with_trust_level(agent_slug, task):
    """Execute task based on agent's trust level."""
    swarmscore = SwarmScoreTool()
    result = swarmscore.load_swarmscore(agent_slug)
    
    if not result.success:
        # Default to restricted mode if score unavailable
        return execute_restricted(task)
    
    trust_score = result.data.get('score', 0)
    
    if trust_score >= 80:
        # High trust - full autonomy
        return execute_autonomous(task)
    elif trust_score >= 60:
        # Medium trust - human oversight
        return execute_supervised(task)
    else:
        # Low trust - restricted operations
        return execute_restricted(task)
```

### 2. Agent Authentication

```python
def authenticate_agent(agent_slug):
    """Verify agent identity and trust level."""
    swarmscore = SwarmScoreTool()
    
    # Load and verify score
    load_result = swarmscore.load_swarmscore(agent_slug)
    if not load_result.success:
        return False, "Failed to load trust score"
    
    # Verify freshness
    verify_payload = load_result.data.get('verify_payload')
    if verify_payload:
        verify_result = swarmscore.verify_swarmscore(verify_payload)
        if not verify_result.success:
            return False, "Trust score verification failed"
    
    trust_score = load_result.data.get('score', 0)
    return trust_score >= 50, f"Trust score: {trust_score}"
```

### 3. Multi-Agent Coordination

```python
def find_trusted_collaborators(task_requirements):
    """Find agents suitable for collaboration based on trust scores."""
    swarmscore = SwarmScoreTool()
    
    # Get discovery manifest for agent lookup
    manifest_result = swarmscore.get_discovery_manifest()
    if not manifest_result.success:
        return []
    
    trusted_agents = []
    discovery_data = manifest_result.data
    
    # Example: Filter agents by trust score and capabilities
    for agent_id in discovery_data.get('agents', []):
        score_result = swarmscore.load_swarmscore(agent_id)
        if score_result.success:
            score_data = score_result.data
            if score_data.get('score', 0) >= 70:
                trusted_agents.append({
                    'id': agent_id,
                    'score': score_data['score'],
                    'capabilities': score_data.get('capabilities', [])
                })
    
    return trusted_agents
```

## PraisonAI Agent Integration

### Using with PraisonAI Agent Tools

```python
from praisonaiagents import Agent, tool
from praisonai_tools.tools import SwarmScoreTool

@tool
def check_agent_trust_score(agent_slug: str) -> str:
    """Check the trust score for an agent."""
    swarmscore = SwarmScoreTool()
    result = swarmscore.load_swarmscore(agent_slug)
    
    if result.success:
        score_data = result.data
        return f"Agent {agent_slug} has trust score {score_data.get('score', 'unknown')} with {score_data.get('success_rate', 'unknown')}% success rate"
    else:
        return f"Failed to load trust score for {agent_slug}: {result.error}"

# Create agent with SwarmScore capability
agent = Agent(
    name="trust-aware-agent",
    instructions="You can check agent trust scores using the check_agent_trust_score tool.",
    tools=[check_agent_trust_score]
)

# Use the agent
response = agent.start("What is the trust score for agent 'trading-bot-v2'?")
print(response)
```

### Agent with Built-in Trust Management

```python
from praisonaiagents import Agent
from praisonai_tools.tools import SwarmScoreTool

class TrustAwareAgent(Agent):
    """PraisonAI Agent with built-in SwarmScore integration."""
    
    def __init__(self, agent_slug: str, **kwargs):
        super().__init__(**kwargs)
        self.agent_slug = agent_slug
        self.swarmscore = SwarmScoreTool()
        self._trust_score = None
    
    async def check_trust_level(self):
        """Check and cache current trust level."""
        result = self.swarmscore.load_swarmscore(self.agent_slug)
        if result.success:
            self._trust_score = result.data.get('score', 0)
        return self._trust_score
    
    def can_execute_action(self, action_type: str) -> bool:
        """Determine if action can be executed based on trust level."""
        if self._trust_score is None:
            return False  # Default to safe
        
        # Define trust requirements for different actions
        trust_requirements = {
            'read': 30,
            'write': 60,
            'execute': 80,
            'admin': 95
        }
        
        required_trust = trust_requirements.get(action_type, 100)
        return self._trust_score >= required_trust

# Usage
agent = TrustAwareAgent(
    agent_slug="my-agent-123",
    name="secure-agent",
    instructions="Execute tasks based on trust level"
)

# Check trust before executing
trust_score = await agent.check_trust_level()
if agent.can_execute_action('execute'):
    print("Proceeding with high-trust execution")
else:
    print("Restricted to low-trust operations")
```

## API Reference

### SwarmScoreTool Class

#### Methods

**`__init__(api_base_url: str = "https://api.swarmsync.ai/v1/swarmscore/")`**
- Initialize SwarmScore tool
- `api_base_url`: Base URL for SwarmScore API

**`load_swarmscore(slug: str) -> ToolResult`**
- Load SwarmScore data by agent slug
- Returns: ToolResult with passport, certificate, and verification data

**`verify_swarmscore(verify_payload: Dict[str, Any]) -> ToolResult`**
- Verify SwarmScore freshness using verification payload
- Returns: ToolResult with verification status

**`get_discovery_manifest() -> ToolResult`**
- Get machine-readable agent discovery manifest
- Returns: ToolResult with discovery data

**`run(action: str, **kwargs) -> ToolResult`**
- Execute SwarmScore action
- Actions: 'load', 'verify', 'discover'

### Standalone Functions

**`load_swarmscore_by_slug(slug: str) -> Dict[str, Any]`**
- Load SwarmScore data by agent slug
- Raises: Exception if loading fails

**`verify_swarmscore_freshness(verify_payload: Dict[str, Any]) -> Dict[str, Any]`**
- Verify SwarmScore freshness
- Raises: Exception if verification fails

**`get_agent_discovery_manifest() -> Dict[str, Any]`**
- Get agent discovery manifest
- Raises: Exception if retrieval fails

## SwarmScore Data Structure

```json
{
  "score": 85,
  "tier": "gold",
  "jobs_completed": 150,
  "success_rate": 94.5,
  "consistency_score": 88,
  "signed_certificate": "...",
  "verify_payload": {
    "signature": "...",
    "timestamp": "...",
    "agent_id": "..."
  },
  "capabilities": ["trading", "analysis", "reporting"],
  "last_updated": "2024-01-15T10:30:00Z"
}
```

## Error Handling

```python
from praisonai_tools.tools import SwarmScoreTool

swarmscore = SwarmScoreTool()
result = swarmscore.load_swarmscore("agent-123")

if not result.success:
    error_msg = result.error
    
    if "network" in error_msg.lower():
        # Handle network issues
        print("Network connectivity problem")
    elif "not found" in error_msg.lower():
        # Handle missing agent
        print("Agent not registered in SwarmScore")
    else:
        # Handle other errors
        print(f"Unexpected error: {error_msg}")
```

## Best Practices

1. **Cache Trust Scores**: Cache scores temporarily to avoid excessive API calls
2. **Graceful Degradation**: Have fallback behavior when SwarmScore is unavailable
3. **Verify Freshness**: Always verify score freshness for critical decisions
4. **Trust Thresholds**: Define clear trust score requirements for different operations
5. **Error Handling**: Handle network and API errors gracefully

## Getting Started with SwarmScore

1. **Register**: Create an account at [SwarmSync.AI](https://swarmsync.ai)
2. **Get Your Slug**: Obtain your agent identifier from the dashboard
3. **Start Building**: Begin tracking execution history to build trust
4. **Integrate**: Use this tool to incorporate trust ratings into your workflows

## Resources

- [SwarmScore Documentation](https://swarmsync.ai/docs/protocol-specs/swarmscore)
- [SwarmScore GitHub Spec](https://github.com/swarmsync-ai/swarmscore-spec)
- [SwarmSync.AI Platform](https://swarmsync.ai)
- [Example Implementation](../examples/swarmscore_example.py)

## Contributing

To contribute improvements to the SwarmScore integration:

1. Fork the PraisonAI-Tools repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## License

This integration is part of PraisonAI-Tools and follows the same license terms.