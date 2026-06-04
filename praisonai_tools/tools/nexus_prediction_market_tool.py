"""NEXUS Prediction Market Tool for PraisonAI

Provides access to live Kalshi/Polymarket prediction market data and arbitrage opportunities
through the NEXUS API (https://nexus-agent-xa12.onrender.com).

Features:
- Free market data queries
- Paid arbitrage opportunity detection
- Real-time prediction market insights

API Documentation:
- Free endpoint: /kalshi?market={market_name}
- Paid endpoint: /arb/check?markets={market1,market2}
- Validation: https://agentic.market/validate?url=https://nexus-agent-xa12.onrender.com/arb/check
"""

from typing import Optional, List, Dict, Any
import requests
import json
from praisonai_tools.tools.base import BaseTool


class NexusPredictionMarketTool(BaseTool):
    """Tool for accessing NEXUS prediction market data and arbitrage opportunities."""
    
    name: str = "nexus_prediction_market"
    description: str = """Access live Kalshi/Polymarket prediction market data and arbitrage opportunities.
    
    Features:
    - Query free market data for specific markets (Fed, BTC, etc.)
    - Check arbitrage opportunities between prediction markets (requires payment)
    - Get real-time market insights and pricing data
    
    Use cases:
    - Market research and analysis
    - Arbitrage opportunity identification
    - Prediction market trend monitoring
    """
    
    def __init__(self, source_name: Optional[str] = None, api_key: Optional[str] = None):
        """Initialize the NEXUS Prediction Market Tool.
        
        Args:
            source_name: Optional source identifier for tracking (sent as X-NEXUS-Source header)
            api_key: Optional API key for paid features (if implemented)
        """
        super().__init__()
        self.base_url = "https://nexus-agent-xa12.onrender.com"
        self.source_name = source_name or "praisonai-agent"
        self.api_key = api_key
        self.headers = {
            "X-NEXUS-Source": self.source_name,
            "User-Agent": "PraisonAI-NEXUS-Tool/1.0",
            "Accept": "application/json"
        }
        if self.api_key:
            self.headers["Authorization"] = f"Bearer {self.api_key}"
    
    def get_market_data(self, market: str) -> Dict[str, Any]:
        """Get free market data for a specific prediction market.
        
        Args:
            market: Market identifier (e.g., 'Fed', 'BTC', 'Election')
            
        Returns:
            Dict containing market data including prices, volumes, and trends
        """
        try:
            url = f"{self.base_url}/kalshi"
            params = {"market": market}
            
            response = requests.get(url, params=params, headers=self.headers, timeout=30)
            response.raise_for_status()
            
            return {
                "success": True,
                "market": market,
                "data": response.json(),
                "source": "nexus-free-api"
            }
            
        except requests.RequestException as e:
            return {
                "success": False,
                "error": f"Failed to fetch market data: {str(e)}",
                "market": market
            }
        except json.JSONDecodeError as e:
            return {
                "success": False,
                "error": f"Invalid JSON response: {str(e)}",
                "market": market
            }
    
    def check_arbitrage_opportunities(self, markets: List[str]) -> Dict[str, Any]:
        """Check for arbitrage opportunities between prediction markets (paid feature).
        
        Args:
            markets: List of market identifiers to analyze for arbitrage
            
        Returns:
            Dict containing arbitrage opportunities and analysis
            
        Note:
            This is a paid feature requiring $0.02 USDC on eip155:8453
        """
        try:
            url = f"{self.base_url}/arb/check"
            markets_param = ",".join(markets)
            params = {"markets": markets_param}
            
            response = requests.get(url, params=params, headers=self.headers, timeout=30)
            response.raise_for_status()
            
            return {
                "success": True,
                "markets": markets,
                "arbitrage_data": response.json(),
                "source": "nexus-paid-api",
                "note": "This is a paid feature ($0.02 USDC on eip155:8453)"
            }
            
        except requests.RequestException as e:
            if e.response and e.response.status_code == 402:
                return {
                    "success": False,
                    "error": "Payment required for arbitrage analysis. Cost: $0.02 USDC on eip155:8453",
                    "markets": markets,
                    "payment_info": "This feature requires payment on eip155:8453 blockchain"
                }
            return {
                "success": False,
                "error": f"Failed to check arbitrage opportunities: {str(e)}",
                "markets": markets
            }
        except json.JSONDecodeError as e:
            return {
                "success": False,
                "error": f"Invalid JSON response: {str(e)}",
                "markets": markets
            }
    
    def get_agent_info(self) -> Dict[str, Any]:
        """Get NEXUS agent information and capabilities.
        
        Returns:
            Dict containing agent metadata and API information
        """
        try:
            url = f"{self.base_url}/.well-known/agent.json"
            
            response = requests.get(url, headers=self.headers, timeout=30)
            response.raise_for_status()
            
            return {
                "success": True,
                "agent_info": response.json(),
                "source": "nexus-agent-metadata"
            }
            
        except requests.RequestException as e:
            return {
                "success": False,
                "error": f"Failed to fetch agent info: {str(e)}"
            }
        except json.JSONDecodeError as e:
            return {
                "success": False,
                "error": f"Invalid JSON response: {str(e)}"
            }
    
    def run(self, 
           action: str, 
           market: Optional[str] = None,
           markets: Optional[List[str]] = None) -> str:
        """Execute NEXUS prediction market operations.
        
        Args:
            action: Action to perform ('get_market_data', 'check_arbitrage', 'get_agent_info')
            market: Single market identifier (for get_market_data)
            markets: List of markets (for check_arbitrage)
            
        Returns:
            JSON string with operation results
        """
        try:
            if action == "get_market_data":
                if not market:
                    return json.dumps({
                        "success": False,
                        "error": "Market parameter required for get_market_data action"
                    })
                result = self.get_market_data(market)
                
            elif action == "check_arbitrage":
                if not markets or not isinstance(markets, list):
                    return json.dumps({
                        "success": False,
                        "error": "Markets parameter (list) required for check_arbitrage action"
                    })
                result = self.check_arbitrage_opportunities(markets)
                
            elif action == "get_agent_info":
                result = self.get_agent_info()
                
            else:
                return json.dumps({
                    "success": False,
                    "error": f"Unknown action: {action}. Available actions: get_market_data, check_arbitrage, get_agent_info"
                })
            
            return json.dumps(result, indent=2)
            
        except Exception as e:
            return json.dumps({
                "success": False,
                "error": f"Unexpected error: {str(e)}"
            })


# For backward compatibility and ease of use
def nexus_prediction_market_tool(
    action: str,
    market: Optional[str] = None,
    markets: Optional[List[str]] = None,
    source_name: Optional[str] = None
) -> str:
    """Function-based interface for NEXUS prediction market operations.
    
    Args:
        action: Action to perform ('get_market_data', 'check_arbitrage', 'get_agent_info')
        market: Single market identifier (for get_market_data)
        markets: List of markets (for check_arbitrage)  
        source_name: Optional source identifier for tracking
        
    Returns:
        JSON string with operation results
        
    Examples:
        # Get Fed market data
        result = nexus_prediction_market_tool("get_market_data", market="Fed")
        
        # Check arbitrage between Fed and BTC markets
        result = nexus_prediction_market_tool("check_arbitrage", markets=["Fed", "BTC"])
        
        # Get agent info
        result = nexus_prediction_market_tool("get_agent_info")
    """
    tool = NexusPredictionMarketTool(source_name=source_name)
    return tool.run(action=action, market=market, markets=markets)


__all__ = ["NexusPredictionMarketTool", "nexus_prediction_market_tool"]