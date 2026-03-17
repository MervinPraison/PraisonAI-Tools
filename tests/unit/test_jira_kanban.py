"""TDD Tests for Jira Kanban integration.

Tests for new Kanban features:
- Board operations (list, get, configuration)
- Issue transitions (get transitions, transition issue)
- Backlog management
- Standalone tool functions for agents
"""

from unittest.mock import Mock, patch
import os


class TestJiraKanbanBoards:
    """Test board-related operations."""
    
    @patch.dict(os.environ, {
        "JIRA_URL": "https://test.atlassian.net",
        "JIRA_EMAIL": "test@example.com",
        "JIRA_API_TOKEN": "test-token"
    })
    def test_list_boards_returns_boards(self):
        """Test listing all boards."""
        from praisonai_tools import JiraTool
        
        jira = JiraTool()
        
        # Mock the client to use boards() method
        mock_client = Mock()
        jira._client = mock_client
        
        # Create mock board objects
        mock_board1 = Mock()
        mock_board1.id = 1
        mock_board1.name = "KAN board"
        mock_board1.type = "kanban"
        mock_board1.location = Mock()
        mock_board1.location.projectKey = "KAN"
        
        mock_board2 = Mock()
        mock_board2.id = 2
        mock_board2.name = "SCRUM board"
        mock_board2.type = "scrum"
        mock_board2.location = Mock()
        mock_board2.location.projectKey = "SCRUM"
        
        mock_client.boards.return_value = [mock_board1, mock_board2]
        
        boards = jira.list_boards()
        
        assert len(boards) == 2
        assert boards[0]["id"] == 1
        assert boards[0]["name"] == "KAN board"
        assert boards[0]["type"] == "kanban"
    
    @patch.dict(os.environ, {
        "JIRA_URL": "https://test.atlassian.net",
        "JIRA_EMAIL": "test@example.com",
        "JIRA_API_TOKEN": "test-token"
    })
    def test_list_boards_filter_by_type(self):
        """Test filtering boards by type (kanban/scrum)."""
        from praisonai_tools import JiraTool
        
        jira = JiraTool()
        
        # Mock the client
        mock_client = Mock()
        jira._client = mock_client
        
        mock_board = Mock()
        mock_board.id = 1
        mock_board.name = "KAN board"
        mock_board.type = "kanban"
        mock_board.location = Mock()
        mock_board.location.projectKey = "KAN"
        
        mock_client.boards.return_value = [mock_board]
        
        boards = jira.list_boards(board_type="kanban")
        
        mock_client.boards.assert_called_once()
        # Check that type parameter was passed
        call_args = mock_client.boards.call_args
        assert call_args[1]["type"] == "kanban"
    
    @patch.dict(os.environ, {
        "JIRA_URL": "https://test.atlassian.net",
        "JIRA_EMAIL": "test@example.com",
        "JIRA_API_TOKEN": "test-token"
    })
    def test_get_board_returns_details(self):
        """Test getting a specific board."""
        from praisonai_tools import JiraTool
        
        jira = JiraTool()
        
        with patch.object(jira, '_agile_request') as mock_request:
            mock_request.return_value = {
                "id": 2,
                "name": "KAN board",
                "type": "kanban",
                "location": {"projectKey": "KAN"}
            }
            
            board = jira.get_board(board_id=2)
            
            assert board["id"] == 2
            assert board["name"] == "KAN board"
            assert board["type"] == "kanban"
    
    @patch.dict(os.environ, {
        "JIRA_URL": "https://test.atlassian.net",
        "JIRA_EMAIL": "test@example.com",
        "JIRA_API_TOKEN": "test-token"
    })
    def test_get_board_configuration(self):
        """Test getting board configuration (columns)."""
        from praisonai_tools import JiraTool
        
        jira = JiraTool()
        
        with patch.object(jira, '_agile_request') as mock_request:
            mock_request.return_value = {
                "columnConfig": {
                    "columns": [
                        {"name": "To Do", "statuses": [{"id": "1"}]},
                        {"name": "In Progress", "statuses": [{"id": "2"}]},
                        {"name": "Done", "statuses": [{"id": "3"}]},
                    ]
                }
            }
            
            config = jira.get_board_configuration(board_id=2)
            
            assert "columns" in config
            assert len(config["columns"]) == 3
            assert config["columns"][0]["name"] == "To Do"
    
    @patch.dict(os.environ, {
        "JIRA_URL": "https://test.atlassian.net",
        "JIRA_EMAIL": "test@example.com",
        "JIRA_API_TOKEN": "test-token"
    })
    def test_get_board_issues(self):
        """Test getting issues on a board."""
        from praisonai_tools import JiraTool
        
        jira = JiraTool()
        
        with patch.object(jira, '_agile_request') as mock_request:
            mock_request.return_value = {
                "issues": [
                    {"key": "KAN-1", "fields": {"summary": "Task 1", "status": {"name": "To Do"}}},
                    {"key": "KAN-2", "fields": {"summary": "Task 2", "status": {"name": "In Progress"}}},
                ]
            }
            
            issues = jira.get_board_issues(board_id=2)
            
            assert len(issues) == 2
            assert issues[0]["key"] == "KAN-1"


class TestJiraTransitions:
    """Test issue transition operations."""
    
    @patch.dict(os.environ, {
        "JIRA_URL": "https://test.atlassian.net",
        "JIRA_EMAIL": "test@example.com",
        "JIRA_API_TOKEN": "test-token"
    })
    def test_get_transitions(self):
        """Test getting available transitions for an issue."""
        from praisonai_tools import JiraTool
        
        jira = JiraTool()
        # Pre-set _client to avoid import
        mock_client = Mock()
        jira._client = mock_client
        
        mock_client.transitions.return_value = [
            {"id": "11", "name": "To Do", "to": {"name": "To Do"}},
            {"id": "21", "name": "In Progress", "to": {"name": "In Progress"}},
            {"id": "31", "name": "Done", "to": {"name": "Done"}},
        ]
        
        transitions = jira.get_transitions(issue_key="KAN-1")
        
        assert len(transitions) == 3
        assert transitions[0]["name"] == "To Do"
        assert transitions[1]["name"] == "In Progress"
    
    @patch.dict(os.environ, {
        "JIRA_URL": "https://test.atlassian.net",
        "JIRA_EMAIL": "test@example.com",
        "JIRA_API_TOKEN": "test-token"
    })
    def test_transition_issue_by_id(self):
        """Test transitioning an issue by transition ID."""
        from praisonai_tools import JiraTool
        
        jira = JiraTool()
        mock_client = Mock()
        jira._client = mock_client
        
        mock_client.transition_issue.return_value = None
        
        result = jira.transition_issue(issue_key="KAN-1", transition_id="21")
        
        assert result["success"] is True
        mock_client.transition_issue.assert_called_once()
    
    @patch.dict(os.environ, {
        "JIRA_URL": "https://test.atlassian.net",
        "JIRA_EMAIL": "test@example.com",
        "JIRA_API_TOKEN": "test-token"
    })
    def test_transition_issue_by_name(self):
        """Test transitioning an issue by transition name."""
        from praisonai_tools import JiraTool
        
        jira = JiraTool()
        mock_client = Mock()
        jira._client = mock_client
        
        # Mock get_transitions to return available transitions
        mock_client.transitions.return_value = [
            {"id": "21", "name": "In Progress", "to": {"name": "In Progress"}},
        ]
        mock_client.transition_issue.return_value = None
        
        result = jira.transition_issue(issue_key="KAN-1", transition_name="In Progress")
        
        assert result["success"] is True
    
    @patch.dict(os.environ, {
        "JIRA_URL": "https://test.atlassian.net",
        "JIRA_EMAIL": "test@example.com",
        "JIRA_API_TOKEN": "test-token"
    })
    def test_move_issue_to_column(self):
        """Test moving an issue to a specific column (convenience method)."""
        from praisonai_tools import JiraTool
        
        jira = JiraTool()
        mock_client = Mock()
        jira._client = mock_client
        
        mock_client.transitions.return_value = [
            {"id": "31", "name": "Done", "to": {"name": "Done"}},
        ]
        mock_client.transition_issue.return_value = None
        
        result = jira.move_issue(issue_key="KAN-1", status="Done")
        
        assert result["success"] is True


class TestJiraBacklog:
    """Test backlog operations."""
    
    @patch.dict(os.environ, {
        "JIRA_URL": "https://test.atlassian.net",
        "JIRA_EMAIL": "test@example.com",
        "JIRA_API_TOKEN": "test-token"
    })
    def test_get_backlog(self):
        """Test getting backlog issues."""
        from praisonai_tools import JiraTool
        
        jira = JiraTool()
        
        with patch.object(jira, '_agile_request') as mock_request:
            mock_request.return_value = {
                "issues": [
                    {"key": "KAN-5", "fields": {"summary": "Backlog item 1"}},
                    {"key": "KAN-6", "fields": {"summary": "Backlog item 2"}},
                ]
            }
            
            backlog = jira.get_backlog(board_id=2)
            
            assert len(backlog) == 2
            assert backlog[0]["key"] == "KAN-5"


class TestJiraStandaloneFunctions:
    """Test standalone tool functions for agent usage."""
    
    @patch.dict(os.environ, {
        "JIRA_URL": "https://test.atlassian.net",
        "JIRA_EMAIL": "test@example.com",
        "JIRA_API_TOKEN": "test-token"
    })
    def test_jira_list_boards_function(self):
        """Test standalone jira_list_boards function."""
        from praisonai_tools import jira_list_boards
        
        with patch('praisonai_tools.tools.jira_tool.JiraTool.list_boards') as mock_method:
            mock_method.return_value = [{"id": 1, "name": "Test Board"}]
            
            boards = jira_list_boards()
            
            assert len(boards) == 1
            mock_method.assert_called_once()
    
    @patch.dict(os.environ, {
        "JIRA_URL": "https://test.atlassian.net",
        "JIRA_EMAIL": "test@example.com",
        "JIRA_API_TOKEN": "test-token"
    })
    def test_jira_get_board_issues_function(self):
        """Test standalone jira_get_board_issues function."""
        from praisonai_tools import jira_get_board_issues
        
        with patch('praisonai_tools.tools.jira_tool.JiraTool.get_board_issues') as mock_method:
            mock_method.return_value = [{"key": "KAN-1", "summary": "Task 1"}]
            
            issues = jira_get_board_issues(board_id=2)
            
            assert len(issues) == 1
            mock_method.assert_called_once_with(board_id=2, jql=None)
    
    @patch.dict(os.environ, {
        "JIRA_URL": "https://test.atlassian.net",
        "JIRA_EMAIL": "test@example.com",
        "JIRA_API_TOKEN": "test-token"
    })
    def test_jira_move_issue_function(self):
        """Test standalone jira_move_issue function."""
        from praisonai_tools import jira_move_issue
        
        with patch('praisonai_tools.tools.jira_tool.JiraTool.move_issue') as mock_method:
            mock_method.return_value = {"success": True}
            
            result = jira_move_issue(issue_key="KAN-1", status="Done")
            
            assert result["success"] is True
            mock_method.assert_called_once_with(issue_key="KAN-1", status="Done")
    
    @patch.dict(os.environ, {
        "JIRA_URL": "https://test.atlassian.net",
        "JIRA_EMAIL": "test@example.com",
        "JIRA_API_TOKEN": "test-token"
    })
    def test_jira_create_task_function(self):
        """Test standalone jira_create_task function."""
        from praisonai_tools import jira_create_task
        
        with patch('praisonai_tools.tools.jira_tool.JiraTool.create_issue') as mock_method:
            mock_method.return_value = {"success": True, "key": "KAN-10"}
            
            result = jira_create_task(
                project="KAN",
                summary="New task",
                description="Task description"
            )
            
            assert result["success"] is True
            assert result["key"] == "KAN-10"
    
    @patch.dict(os.environ, {
        "JIRA_URL": "https://test.atlassian.net",
        "JIRA_EMAIL": "test@example.com",
        "JIRA_API_TOKEN": "test-token"
    })
    def test_jira_get_transitions_function(self):
        """Test standalone jira_get_transitions function."""
        from praisonai_tools import jira_get_transitions
        
        with patch('praisonai_tools.tools.jira_tool.JiraTool.get_transitions') as mock_method:
            mock_method.return_value = [
                {"id": "11", "name": "To Do"},
                {"id": "21", "name": "In Progress"},
            ]
            
            transitions = jira_get_transitions(issue_key="KAN-1")
            
            assert len(transitions) == 2


class TestJiraRunAction:
    """Test the run() method with new Kanban actions."""
    
    @patch.dict(os.environ, {
        "JIRA_URL": "https://test.atlassian.net",
        "JIRA_EMAIL": "test@example.com",
        "JIRA_API_TOKEN": "test-token"
    })
    def test_run_list_boards_action(self):
        """Test run() with list_boards action."""
        from praisonai_tools import JiraTool
        
        jira = JiraTool()
        
        with patch.object(jira, 'list_boards') as mock_method:
            mock_method.return_value = [{"id": 1}]
            
            result = jira.run(action="list_boards")
            
            mock_method.assert_called_once()
    
    @patch.dict(os.environ, {
        "JIRA_URL": "https://test.atlassian.net",
        "JIRA_EMAIL": "test@example.com",
        "JIRA_API_TOKEN": "test-token"
    })
    def test_run_get_board_action(self):
        """Test run() with get_board action."""
        from praisonai_tools import JiraTool
        
        jira = JiraTool()
        
        with patch.object(jira, 'get_board') as mock_method:
            mock_method.return_value = {"id": 2}
            
            result = jira.run(action="get_board", board_id=2)
            
            mock_method.assert_called_once_with(board_id=2)
    
    @patch.dict(os.environ, {
        "JIRA_URL": "https://test.atlassian.net",
        "JIRA_EMAIL": "test@example.com",
        "JIRA_API_TOKEN": "test-token"
    })
    def test_run_transition_issue_action(self):
        """Test run() with transition_issue action."""
        from praisonai_tools import JiraTool
        
        jira = JiraTool()
        
        with patch.object(jira, 'transition_issue') as mock_method:
            mock_method.return_value = {"success": True}
            
            result = jira.run(
                action="transition_issue",
                issue_key="KAN-1",
                transition_name="In Progress"
            )
            
            mock_method.assert_called_once()


class TestJiraAgileRequest:
    """Test the internal _agile_request method."""
    
    @patch.dict(os.environ, {
        "JIRA_URL": "https://test.atlassian.net",
        "JIRA_EMAIL": "test@example.com",
        "JIRA_API_TOKEN": "test-token"
    })
    def test_agile_request_get(self):
        """Test _agile_request makes correct GET request."""
        from praisonai_tools import JiraTool
        
        jira = JiraTool()
        
        # Mock the session property
        mock_session = Mock()
        mock_response = Mock()
        mock_response.json.return_value = {"values": []}
        mock_response.raise_for_status = Mock()
        mock_response.text = '{"values": []}'
        mock_session.get.return_value = mock_response
        jira._session = mock_session
        
        result = jira._agile_request("/board")
        
        mock_session.get.assert_called_once()
        call_args = mock_session.get.call_args
        assert "rest/agile/1.0/board" in call_args[0][0]
        assert result == {"values": []}
    
    @patch.dict(os.environ, {
        "JIRA_URL": "https://test.atlassian.net",
        "JIRA_EMAIL": "test@example.com",
        "JIRA_API_TOKEN": "test-token"
    })
    def test_agile_request_with_params(self):
        """Test _agile_request with query parameters."""
        from praisonai_tools import JiraTool
        
        jira = JiraTool()
        
        # Mock the session property
        mock_session = Mock()
        mock_response = Mock()
        mock_response.json.return_value = {"values": []}
        mock_response.raise_for_status = Mock()
        mock_response.text = '{"values": []}'
        mock_session.get.return_value = mock_response
        jira._session = mock_session
        
        result = jira._agile_request("/board", params={"type": "kanban"})
        
        call_args = mock_session.get.call_args
        assert call_args[1]["params"]["type"] == "kanban"
