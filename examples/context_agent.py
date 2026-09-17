import os

from praisonaiagents import Agent
from praisonai_tools import ContextToolkit


tools = ContextToolkit(api_key=os.environ["CONTEXT_DEV_API_KEY"]).get_tools()
agent = Agent(
    name="web-researcher",
    instructions="Use Context.dev for current web research and cite source URLs.",
    tools=tools,
)
agent.start("Find Context.dev's latest public product updates and summarize them.")
