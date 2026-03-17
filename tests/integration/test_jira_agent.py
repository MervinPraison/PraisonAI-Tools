"""
Test Jira Kanban integration with PraisonAI Agents.

Creates tasks, moves them through Kanban board stages.
Requires: JIRA_URL, JIRA_EMAIL, JIRA_API_TOKEN, OPENAI_API_KEY
"""

import os
import sys

# Add parent to path so praisonai_tools is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from praisonaiagents import Agent
from praisonai_tools import (
    jira_create_task,
    jira_search,
    jira_list_boards,
    jira_get_board_issues,
    jira_get_transitions,
    jira_move_issue,
)


def main():
    """Run Jira Kanban agent test."""
    
    # Create a project manager agent with Jira tools
    agent = Agent(
        name="JiraProjectManager",
        role="Jira Project Manager",
        goal="Manage Jira Kanban board: create tasks, track progress, and move tickets through workflow stages",
        instructions="""You are a Jira project manager. You have tools to interact with Jira.
        
The Jira project key is 'KAN' and the Kanban board ID is 2.

Follow these steps EXACTLY in order:

1. First, list all boards using jira_list_boards() to confirm the board exists
2. Get current board issues using jira_get_board_issues(board_id=2) to see what's there
3. Create a new task using jira_create_task(project="KAN", summary="Test Jira Kanban Integration", description="Automated test task created by PraisonAI agent to verify Kanban workflow")
4. After creating the task, note the issue key (e.g., KAN-XX) from the response
5. Get transitions for that new issue using jira_get_transitions(issue_key="KAN-XX") where KAN-XX is the actual key
6. Move the issue to "In Progress" using jira_move_issue(issue_key="KAN-XX", status="In Progress")
7. Then move it to "Done" using jira_move_issue(issue_key="KAN-XX", status="Done")
8. Finally, search for the issue using jira_search(jql="project = KAN AND summary ~ 'Test Jira Kanban Integration' ORDER BY created DESC") to confirm it's Done

Report the results of each step clearly.""",
        tools=[
            jira_create_task,
            jira_search,
            jira_list_boards,
            jira_get_board_issues,
            jira_get_transitions,
            jira_move_issue,
        ],
        llm="gpt-4o-mini",
    )
    
    result = agent.start(
        "Execute the Jira Kanban workflow: list boards, create a task in KAN project, "
        "move it through In Progress to Done, and verify the final status."
    )
    
    print("\n" + "=" * 60)
    print("AGENT RESULT:")
    print("=" * 60)
    print(result)


if __name__ == "__main__":
    main()
