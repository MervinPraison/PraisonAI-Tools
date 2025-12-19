"""Integration test: praisonai-tools custom tools with praisonaiagents built-in tools.

This test verifies:
1. Built-in tools from praisonaiagents work (tavily_search)
2. Custom tools from praisonai-tools work (@tool decorator)
3. Both can be combined in an Agent

Usage:
    export OPENAI_API_KEY=your_openai_key
    export TAVILY_API_KEY=your_tavily_key
    python test_integration.py
"""

import os
import sys

print("=" * 60)
print("PraisonAI Tools Integration Test")
print("=" * 60)

# Test 1: Verify praisonai-tools imports work
print("\n[Test 1] Importing praisonai-tools...")
try:
    from praisonai_tools import BaseTool, tool, FunctionTool, is_tool, get_tool_schema
    print("✅ praisonai-tools imports successful")
except ImportError as e:
    print(f"❌ Failed to import praisonai-tools: {e}")
    sys.exit(1)

# Test 2: Verify praisonaiagents imports work
print("\n[Test 2] Importing praisonaiagents...")
try:
    from praisonaiagents import Agent
    from praisonaiagents.tools import tavily_search
    print("✅ praisonaiagents imports successful")
except ImportError as e:
    print(f"❌ Failed to import praisonaiagents: {e}")
    sys.exit(1)

# Test 3: Create custom tool with @tool decorator
print("\n[Test 3] Creating custom tool with @tool decorator...")

@tool
def my_calculator(expression: str) -> str:
    """Calculate a mathematical expression.
    
    Args:
        expression: Math expression to evaluate (e.g., '2 + 2')
    """
    try:
        result = eval(expression)
        return f"Result: {result}"
    except Exception as e:
        return f"Error: {e}"

print(f"✅ Custom tool created: {my_calculator.name}")
print(f"   Description: {my_calculator.description}")
print(f"   Is tool: {is_tool(my_calculator)}")

# Test 4: Get schema from custom tool
print("\n[Test 4] Getting OpenAI schema from custom tool...")
schema = get_tool_schema(my_calculator)
print(f"✅ Schema generated:")
print(f"   Function name: {schema['function']['name']}")
print(f"   Parameters: {list(schema['function']['parameters']['properties'].keys())}")

# Test 5: Execute custom tool directly
print("\n[Test 5] Executing custom tool directly...")
result = my_calculator(expression="10 * 5 + 2")
print(f"✅ Tool execution result: {result}")

# Test 6: Verify built-in tavily_search tool
print("\n[Test 6] Checking built-in tavily_search tool...")
print(f"✅ tavily_search function: {tavily_search.__name__}")

# Test 7: Test tavily_search with real API call (if key available)
tavily_key = os.environ.get("TAVILY_API_KEY")
if tavily_key:
    print("\n[Test 7] Testing tavily_search with real API call...")
    try:
        result = tavily_search("Python programming", max_results=2)
        if "error" not in result:
            print(f"✅ Tavily search successful!")
            print(f"   Found {len(result.get('results', []))} results")
            for r in result.get('results', [])[:2]:
                print(f"   - {r.get('title', 'No title')[:50]}...")
        else:
            print(f"⚠️ Tavily returned error: {result.get('error')}")
    except Exception as e:
        print(f"❌ Tavily search failed: {e}")
else:
    print("\n[Test 7] Skipped - TAVILY_API_KEY not set")

# Test 8: Create Agent with combined tools (without calling LLM)
print("\n[Test 8] Creating Agent with combined tools...")
openai_key = os.environ.get("OPENAI_API_KEY")
if openai_key:
    try:
        agent = Agent(
            instructions="You are a helpful assistant",
            tools=[tavily_search, my_calculator],
            verbose=False
        )
        print(f"✅ Agent created with {len(agent.tools)} tools:")
        for t in agent.tools:
            name = getattr(t, '__name__', getattr(t, 'name', str(t)))
            print(f"   - {name}")
    except Exception as e:
        print(f"❌ Agent creation failed: {e}")
else:
    print("⚠️ Skipped Agent creation - OPENAI_API_KEY not set")
    print("   To test full integration, set OPENAI_API_KEY")

print("\n" + "=" * 60)
print("Integration test completed!")
print("=" * 60)
