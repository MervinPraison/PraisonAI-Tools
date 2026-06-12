"""JIRA watch tools for PraisonAI Agents — monitor issues and projects for changes."""

import logging
import os
import re
import time
from typing import Optional

from praisonai_tools.tools.decorator import tool

logger = logging.getLogger(__name__)


def _get_jira_connection(
    url: Optional[str] = None,
    username: Optional[str] = None,
    token: Optional[str] = None,
    email: Optional[str] = None,
):
    """Create a JIRA connection with cloud or server authentication."""
    try:
        from jira import JIRA
    except ImportError as exc:
        raise ImportError(
            "JIRA library not installed. Install with: pip install jira"
        ) from exc

    url = url or os.getenv("JIRA_URL")
    username = username or os.getenv("JIRA_USERNAME")
    token = token or os.getenv("JIRA_API_TOKEN")
    email = email or os.getenv("JIRA_EMAIL")

    if not url:
        raise ValueError("JIRA URL is required (parameter or JIRA_URL env var)")

    if email and token:
        auth = (email, token)
    elif username and token:
        auth = (username, token)
    else:
        raise ValueError(
            "JIRA authentication required. Provide either:\n"
            "- email + token (for cloud JIRA)\n"
            "- username + token (for server JIRA)\n"
            "Or set JIRA_EMAIL, JIRA_USERNAME, and JIRA_API_TOKEN"
        )

    return JIRA(server=url, basic_auth=auth)


def _validate_project_key(project_key: str) -> bool:
    """Validate JIRA project key to prevent JQL injection."""
    if not re.match(r"^[A-Z][A-Z0-9_]*$", project_key):
        raise ValueError(
            f"Invalid project key format: {project_key}. "
            "Must start with a letter and contain only uppercase letters, numbers, and underscores."
        )
    return True


@tool
def jira_watch_issue(
    issue_key: str,
    url: Optional[str] = None,
    since_timestamp: Optional[str] = None,
    username: Optional[str] = None,
    token: Optional[str] = None,
    email: Optional[str] = None,
) -> str:
    """Check a specific JIRA issue for changes since a timestamp."""
    try:
        jira = _get_jira_connection(url, username, token, email)
        issue = jira.issue(issue_key, expand="changelog")
        current_updated = issue.fields.updated
        current_status = issue.fields.status.name

        if not since_timestamp:
            result = f"JIRA issue {issue_key} current state:\n"
            result += f"Status: {current_status}\n"
            result += f"Summary: {issue.fields.summary}\n"
            assignee = issue.fields.assignee.displayName if issue.fields.assignee else "Unassigned"
            result += f"Assignee: {assignee}\n"
            priority = issue.fields.priority.name if issue.fields.priority else "None"
            result += f"Priority: {priority}\n"
            result += f"Updated: {current_updated}\n"
            return result

        changes_detected = []
        if current_updated > since_timestamp:
            change_info = {
                "timestamp": current_updated,
                "status": current_status,
                "summary": issue.fields.summary,
                "assignee": issue.fields.assignee.displayName if issue.fields.assignee else "Unassigned",
                "priority": issue.fields.priority.name if issue.fields.priority else "None",
            }

            recent_changes = []
            if issue.changelog and issue.changelog.histories:
                for history in issue.changelog.histories[-3:]:
                    if history.created > since_timestamp:
                        for item in history.items:
                            recent_changes.append({
                                "field": item.field,
                                "from": item.fromString,
                                "to": item.toString,
                                "author": history.author.displayName,
                                "created": history.created,
                            })

            change_info["recent_changes"] = recent_changes
            changes_detected.append(change_info)

            comment_changes = []
            for comment in jira.comments(issue_key):
                if comment.created > since_timestamp:
                    comment_changes.append({
                        "author": comment.author.displayName,
                        "body": comment.body[:500],
                        "created": comment.created,
                    })
            if comment_changes:
                change_info["recent_comments"] = comment_changes

        if changes_detected:
            result = f"JIRA issue {issue_key} - changes detected since {since_timestamp}:\n"
            for i, change in enumerate(changes_detected, 1):
                result += f"\n--- Change {i} at {change['timestamp']} ---\n"
                result += f"Status: {change['status']}\n"
                result += f"Assignee: {change['assignee']}\n"
                result += f"Priority: {change['priority']}\n"
                if change.get("recent_changes"):
                    result += "Recent field changes:\n"
                    for rc in change["recent_changes"]:
                        result += f"  - {rc['field']}: '{rc['from']}' → '{rc['to']}' by {rc['author']}\n"
                if change.get("recent_comments"):
                    result += "Recent comments:\n"
                    for comment in change["recent_comments"]:
                        result += f"  - {comment['author']} ({comment['created']}): {comment['body'][:200]}...\n"
            return result

        return f"No changes detected in JIRA issue {issue_key} since {since_timestamp}"

    except Exception as e:
        logger.error("Failed to watch JIRA issue: %s", e)
        return f"Error watching JIRA issue {issue_key}: {e}"


@tool
def jira_watch_project(
    project_key: str,
    url: Optional[str] = None,
    since_timestamp: Optional[str] = None,
    username: Optional[str] = None,
    token: Optional[str] = None,
    email: Optional[str] = None,
) -> str:
    """Check a JIRA project for new issues and updates since a timestamp."""
    try:
        _validate_project_key(project_key)
        jira = _get_jira_connection(url, username, token, email)

        project_changes = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "new_issues": [],
            "updated_issues": [],
        }

        if not since_timestamp:
            recent_jql = f"project = {project_key} ORDER BY updated DESC"
            recent_issues = jira.search_issues(recent_jql, maxResults=20)
            result = f"JIRA project {project_key} recent activity ({len(recent_issues)} issues):\n"
            for issue in recent_issues[:10]:
                result += f"  {issue.key}: {issue.fields.summary[:60]}...\n"
                result += f"    Status: {issue.fields.status.name}, Updated: {issue.fields.updated}\n"
            return result

        new_jql = f'project = {project_key} AND created >= "{since_timestamp}" ORDER BY created DESC'
        for issue in jira.search_issues(new_jql, maxResults=50):
            project_changes["new_issues"].append({
                "key": issue.key,
                "summary": issue.fields.summary,
                "status": issue.fields.status.name,
                "assignee": issue.fields.assignee.displayName if issue.fields.assignee else "Unassigned",
                "creator": issue.fields.creator.displayName,
                "created": issue.fields.created,
            })

        updated_jql = (
            f'project = {project_key} AND updated >= "{since_timestamp}" '
            f'AND created < "{since_timestamp}" ORDER BY updated DESC'
        )
        for issue in jira.search_issues(updated_jql, maxResults=50):
            project_changes["updated_issues"].append({
                "key": issue.key,
                "summary": issue.fields.summary,
                "status": issue.fields.status.name,
                "assignee": issue.fields.assignee.displayName if issue.fields.assignee else "Unassigned",
                "updated": issue.fields.updated,
            })

        if project_changes["new_issues"] or project_changes["updated_issues"]:
            result = f"JIRA project {project_key} - changes detected since {since_timestamp}:\n"
            result += f"\n--- Activity at {project_changes['timestamp']} ---\n"
            if project_changes["new_issues"]:
                result += f"New issues ({len(project_changes['new_issues'])}):\n"
                for issue in project_changes["new_issues"]:
                    result += f"  {issue['key']}: {issue['summary'][:80]}...\n"
                    result += f"     Status: {issue['status']}, Assignee: {issue['assignee']}, Created: {issue['created']}\n"
            if project_changes["updated_issues"]:
                result += f"Updated issues ({len(project_changes['updated_issues'])}):\n"
                for issue in project_changes["updated_issues"]:
                    result += f"  {issue['key']}: {issue['summary'][:80]}...\n"
                    result += f"     Status: {issue['status']}, Updated: {issue['updated']}\n"
            return result

        return f"No changes detected in JIRA project {project_key} since {since_timestamp}"

    except Exception as e:
        logger.error("Failed to watch JIRA project: %s", e)
        return f"Error watching JIRA project {project_key}: {e}"


@tool
def jira_get_issue_info(
    issue_key: str,
    url: Optional[str] = None,
    username: Optional[str] = None,
    token: Optional[str] = None,
    email: Optional[str] = None,
) -> str:
    """Get detailed information about a specific JIRA issue."""
    try:
        jira = _get_jira_connection(url, username, token, email)
        issue = jira.issue(issue_key, expand="changelog,comments")

        result = f"JIRA Issue: {issue.key}\n"
        result += f"Summary: {issue.fields.summary}\n"
        result += f"Status: {issue.fields.status.name}\n"
        result += f"Priority: {issue.fields.priority.name if issue.fields.priority else 'None'}\n"
        assignee = issue.fields.assignee.displayName if issue.fields.assignee else "Unassigned"
        result += f"Assignee: {assignee}\n"
        result += f"Reporter: {issue.fields.reporter.displayName}\n"
        result += f"Created: {issue.fields.created}\n"
        result += f"Updated: {issue.fields.updated}\n"

        if issue.fields.description:
            result += f"Description: {issue.fields.description[:500]}...\n"

        comments = jira.comments(issue_key)
        if comments:
            result += f"\nRecent Comments ({len(comments[-3:])}):\n"
            for comment in comments[-3:]:
                result += f"  - {comment.author.displayName} ({comment.created}): {comment.body[:200]}...\n"

        return result

    except Exception as e:
        logger.error("Failed to get JIRA issue info: %s", e)
        return f"Error getting JIRA issue {issue_key}: {e}"


@tool
def jira_search_issues(
    jql: str,
    url: Optional[str] = None,
    max_results: int = 20,
    username: Optional[str] = None,
    token: Optional[str] = None,
    email: Optional[str] = None,
) -> str:
    """Search JIRA issues using JQL (JIRA Query Language)."""
    try:
        jira = _get_jira_connection(url, username, token, email)
        issues = jira.search_issues(jql, maxResults=max_results)

        if not issues:
            return f"No issues found for JQL: {jql}"

        result = f"Found {len(issues)} issues for JQL: {jql}\n\n"
        for issue in issues:
            assignee = issue.fields.assignee.displayName if issue.fields.assignee else "Unassigned"
            result += f"{issue.key}: {issue.fields.summary}\n"
            result += f"  Status: {issue.fields.status.name}\n"
            result += f"  Assignee: {assignee}\n"
            result += f"  Updated: {issue.fields.updated}\n\n"

        return result

    except Exception as e:
        logger.error("Failed to search JIRA issues: %s", e)
        return f"Error searching JIRA issues: {e}"


def jira_tools():
    """Return all JIRA watch tools as a collection for agent registration."""
    return [
        jira_watch_issue,
        jira_watch_project,
        jira_get_issue_info,
        jira_search_issues,
    ]
