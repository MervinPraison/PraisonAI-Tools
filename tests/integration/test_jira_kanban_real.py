"""Real integration test for Jira Kanban.

This test requires actual Jira credentials set in environment variables:
- JIRA_URL
- JIRA_EMAIL  
- JIRA_API_TOKEN

Run with: python tests/integration/test_jira_kanban_real.py
"""

import os
import sys

# Add parent to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Load .env file from project root
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), ".env"))
except ImportError:
    pass  # python-dotenv not installed, rely on environment variables

def test_jira_kanban_real():
    """Test Jira Kanban integration with real API."""
    
    # Credentials must be set via environment variables
    required_vars = ["JIRA_URL", "JIRA_EMAIL", "JIRA_API_TOKEN"]
    missing = [v for v in required_vars if not os.environ.get(v)]
    if missing:
        print(f"Skipping: missing environment variables: {', '.join(missing)}")
        return False
    
    from praisonai_tools import JiraTool
    
    jira = JiraTool()
    
    print("=" * 60)
    print("JIRA KANBAN INTEGRATION TEST")
    print("=" * 60)
    
    # Test 1: List projects (uses standard Jira API)
    print("\n1. Listing projects...")
    projects = jira.list_projects()
    print(f"   Found {len(projects)} projects:")
    for p in projects[:5]:
        if "error" not in p:
            print(f"   - {p.get('key')}: {p.get('name')}")
        else:
            print(f"   Error: {p.get('error')}")
    
    # Test 2: Search issues with JQL (uses standard Jira API)
    print("\n2. Searching issues in KAN project...")
    issues = jira.search(jql="project = KAN ORDER BY created DESC", max_results=10)
    print(f"   Found {len(issues)} issues:")
    for i in issues[:5]:
        if "error" not in i:
            print(f"   - {i.get('key')}: {i.get('summary')} [{i.get('status')}]")
        else:
            print(f"   Error: {i.get('error')}")
    
    # Test 3: Get transitions for an issue (if we have issues)
    if issues and "error" not in issues[0]:
        issue_key = issues[0].get("key")
        print(f"\n3. Getting transitions for {issue_key}...")
        transitions = jira.get_transitions(issue_key=issue_key)
        print("   Available transitions:")
        for t in transitions:
            if "error" not in t:
                print(f"   - {t.get('name')} -> {t.get('to')}")
            else:
                print(f"   Error: {t.get('error')}")
        
        # Test 4: Get issue details
        print(f"\n4. Getting issue details for {issue_key}...")
        issue = jira.get_issue(issue_key=issue_key)
        if "error" not in issue:
            print(f"   Key: {issue.get('key')}")
            print(f"   Summary: {issue.get('summary')}")
            print(f"   Status: {issue.get('status')}")
            print(f"   Assignee: {issue.get('assignee')}")
        else:
            print(f"   Error: {issue.get('error')}")
    
    # Test 5: Create a test task
    print("\n5. Creating a test task...")
    result = jira.create_issue(
        project="KAN",
        summary="Test task from PraisonAI Agent",
        description="This is a test task created by the Jira Kanban integration test.",
        issue_type="Task"
    )
    if "error" not in result:
        print(f"   ✓ Created: {result.get('key')}")
        new_issue_key = result.get("key")
        
        # Test 6: Move the issue to In Progress
        print(f"\n6. Moving {new_issue_key} to 'In Progress'...")
        move_result = jira.move_issue(issue_key=new_issue_key, status="In Progress")
        if "error" not in move_result:
            print(f"   ✓ Moved to: {move_result.get('status')}")
        else:
            print(f"   Error: {move_result.get('error')}")
        
        # Test 7: Add a comment
        print(f"\n7. Adding comment to {new_issue_key}...")
        comment_result = jira.add_comment(issue_key=new_issue_key, comment="Test comment from PraisonAI Agent")
        if "error" not in comment_result:
            print("   ✓ Comment added")
        else:
            print(f"   Error: {comment_result.get('error')}")
    else:
        print(f"   Error: {result.get('error')}")
    
    # Test 8: List boards (Agile API - may fail if no permissions)
    print("\n8. Listing boards (Agile API)...")
    boards = jira.list_boards()
    print(f"   Found {len(boards)} boards:")
    for b in boards[:5]:
        if "error" not in b:
            print(f"   - ID: {b.get('id')}, Name: {b.get('name')}, Type: {b.get('type')}")
        else:
            print(f"   Note: Agile API may require additional permissions: {b.get('error')[:100]}...")
    
    print("\n" + "=" * 60)
    print("TEST COMPLETE")
    print("=" * 60)
    
    return True


if __name__ == "__main__":
    test_jira_kanban_real()
