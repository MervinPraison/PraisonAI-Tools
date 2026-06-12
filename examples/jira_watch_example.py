#!/usr/bin/env python3
"""JIRA Agent watch example using praisonai-tools.

Setup:
    pip install praisonai-tools jira
    export JIRA_URL=https://yourcompany.atlassian.net
    export JIRA_EMAIL=your_email@example.com
    export JIRA_API_TOKEN=your_api_token
"""

import os

from praisonaiagents import Agent
from praisonai_tools import jira_tools


def main():
    if not os.getenv("JIRA_API_TOKEN"):
        print("Set JIRA_API_TOKEN, JIRA_EMAIL (or JIRA_USERNAME), and JIRA_URL")
        return

    agent = Agent(
        name="JIRA Monitor Agent",
        instructions=(
            "You monitor JIRA issues and projects. Use jira_watch_issue, "
            "jira_watch_project, jira_get_issue_info, and jira_search_issues."
        ),
        tools=jira_tools(),
        llm="gpt-4o-mini",
    )

    print("JIRA watch tools ready. Example prompts:")
    print("  Get info for PROJ-123")
    print("  Search open issues: project = PROJ AND status = Open")
    print("  Watch PROJ-123 for changes since 2024-01-01T00:00:00")

    while True:
        try:
            user_input = input("\nYou: ").strip()
            if user_input.lower() in {"quit", "exit", "q"}:
                break
            if not user_input:
                continue
            print("Agent:", agent.start(user_input))
        except KeyboardInterrupt:
            break


if __name__ == "__main__":
    main()
