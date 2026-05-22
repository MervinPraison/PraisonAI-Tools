"""Example: Using NEXUS Prediction Market Tool with PraisonAI

This example demonstrates how to use the NEXUS prediction market tool to:
1. Get free market data for prediction markets
2. Check arbitrage opportunities between markets (paid feature)
3. Build an intelligent prediction market analysis agent

NEXUS API Information:
- Free endpoint: /kalshi?market={market_name}
- Paid endpoint: /arb/check?markets={market1,market2} ($0.02 USDC on eip155:8453)
- Validation: https://agentic.market/validate?url=https://nexus-agent-xa12.onrender.com/arb/check
"""

from praisonaiagents import Agent, tool
from praisonai_tools.tools.nexus_prediction_market_tool import NexusPredictionMarketTool
import json


# Example 1: Direct tool usage
def example_direct_usage():
    """Example of using the NEXUS tool directly."""
    print("=== Direct NEXUS Tool Usage ===\n")
    
    # Initialize the tool
    nexus_tool = NexusPredictionMarketTool(source_name="praisonai-example")
    
    # Get market data for Fed predictions
    print("1. Getting Fed market data...")
    fed_data = nexus_tool.get_market_data("Fed")
    print(json.dumps(fed_data, indent=2))
    print()
    
    # Get BTC market data  
    print("2. Getting BTC market data...")
    btc_data = nexus_tool.get_market_data("BTC")
    print(json.dumps(btc_data, indent=2))
    print()
    
    # Check arbitrage opportunities (paid feature)
    print("3. Checking arbitrage opportunities between Fed and BTC markets...")
    arb_data = nexus_tool.check_arbitrage_opportunities(["Fed", "BTC"])
    print(json.dumps(arb_data, indent=2))
    print()
    
    # Get agent information
    print("4. Getting NEXUS agent information...")
    agent_info = nexus_tool.get_agent_info()
    print(json.dumps(agent_info, indent=2))


# Example 2: Create a custom tool wrapper for agents
@tool
def get_prediction_market_data(market: str) -> str:
    """Get prediction market data for a specific market.
    
    Args:
        market: Market identifier (e.g., 'Fed', 'BTC', 'Election')
        
    Returns:
        JSON string with market data including prices and trends
    """
    nexus_tool = NexusPredictionMarketTool(source_name="praisonai-agent")
    return nexus_tool.run(action="get_market_data", market=market)


@tool  
def check_prediction_market_arbitrage(markets: str) -> str:
    """Check for arbitrage opportunities between prediction markets.
    
    Args:
        markets: Comma-separated list of markets to analyze (e.g., 'Fed,BTC')
        
    Returns:
        JSON string with arbitrage opportunities and analysis
        
    Note:
        This is a paid feature requiring $0.02 USDC on eip155:8453
    """
    markets_list = [m.strip() for m in markets.split(',')]
    nexus_tool = NexusPredictionMarketTool(source_name="praisonai-agent")
    return nexus_tool.run(action="check_arbitrage", markets=markets_list)


# Example 3: Prediction market analysis agent
def example_prediction_market_agent():
    """Example of a prediction market analysis agent."""
    print("\n=== Prediction Market Analysis Agent ===\n")
    
    # Create an agent with NEXUS prediction market tools
    market_agent = Agent(
        name="PredictionMarketAnalyst",
        instructions="""You are an expert prediction market analyst. 
        
        Your capabilities:
        - Analyze prediction market data from Kalshi and Polymarket via NEXUS API
        - Identify market trends and sentiment
        - Spot potential arbitrage opportunities
        - Provide insights on market dynamics
        
        When analyzing markets:
        1. First get current market data
        2. Analyze the data for trends and insights
        3. Look for arbitrage opportunities if requested
        4. Provide clear explanations of your findings
        
        Be thorough in your analysis and cite specific data points.""",
        
        tools=[get_prediction_market_data, check_prediction_market_arbitrage],
        llm="gpt-4o-mini"
    )
    
    # Example queries
    queries = [
        "Get the current Fed interest rate prediction market data and analyze what it shows about market sentiment.",
        "Compare Fed and BTC prediction markets. What insights can you derive?",
        "Check if there are any arbitrage opportunities between Fed and BTC markets."
    ]
    
    for i, query in enumerate(queries, 1):
        print(f"Query {i}: {query}")
        response = market_agent.start(query)
        print(f"Response: {response}\n")
        print("-" * 80)


# Example 4: Multi-agent prediction market workflow
def example_multi_agent_workflow():
    """Example of a multi-agent workflow for comprehensive market analysis."""
    print("\n=== Multi-Agent Prediction Market Workflow ===\n")
    
    # Data gathering agent
    data_agent = Agent(
        name="MarketDataCollector",
        instructions="""You collect prediction market data from NEXUS API.
        Focus on gathering comprehensive data for analysis.""",
        tools=[get_prediction_market_data]
    )
    
    # Analysis agent  
    analysis_agent = Agent(
        name="MarketAnalyst", 
        instructions="""You analyze prediction market data to identify trends, 
        sentiment, and trading opportunities. Provide detailed insights.""",
        tools=[]
    )
    
    # Arbitrage agent
    arbitrage_agent = Agent(
        name="ArbitrageSpecialist",
        instructions="""You specialize in finding arbitrage opportunities 
        between prediction markets. Assess risk and profitability.""",
        tools=[check_prediction_market_arbitrage]
    )
    
    # Example workflow
    markets = ["Fed", "BTC", "Election"]
    
    print("Step 1: Collecting market data...")
    market_data = {}
    for market in markets:
        print(f"Collecting data for {market} market...")
        data = data_agent.start(f"Get current market data for {market}")
        market_data[market] = data
        print(f"Data collected for {market}: {len(data)} characters")
    
    print("\nStep 2: Analyzing market trends...")
    combined_data = "\n".join([f"{market}: {data}" for market, data in market_data.items()])
    analysis = analysis_agent.start(f"Analyze this prediction market data and identify key trends:\n{combined_data}")
    print(f"Analysis: {analysis[:200]}...")
    
    print("\nStep 3: Checking arbitrage opportunities...")
    arb_analysis = arbitrage_agent.start("Check for arbitrage opportunities between Fed,BTC markets")
    print(f"Arbitrage analysis: {arb_analysis[:200]}...")


if __name__ == "__main__":
    print("NEXUS Prediction Market Tool Examples")
    print("=" * 50)
    
    # Run examples
    try:
        example_direct_usage()
        example_prediction_market_agent()
        example_multi_agent_workflow()
        
    except Exception as e:
        print(f"Error running examples: {e}")
        print("\nNote: Some features require API access or payment.")
        print("Free features: Market data queries")
        print("Paid features: Arbitrage analysis ($0.02 USDC on eip155:8453)")
    
    print("\n" + "=" * 50)
    print("Examples completed!")
    print("\nTo use in your own projects:")
    print("1. Install: pip install praisonai-tools")
    print("2. Import: from praisonai_tools.tools import NexusPredictionMarketTool")
    print("3. Use: tool = NexusPredictionMarketTool()")
    print("\nFor arbitrage features, ensure you have the required payment setup.")