"""Integration tests for motion graphics team."""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

from praisonai_tools.video.motion_graphics.team import motion_graphics_team


class MockAgent:
    """Mock agent for testing."""
    
    def __init__(self, name="", instructions="", tools=None, llm=""):
        self.name = name
        self.instructions = instructions
        self.tools = tools or []
        self.llm = llm


class MockAgentTeam:
    """Mock agent team for testing."""
    
    def __init__(self, agents=None, leader=None, **kwargs):
        self.agents = agents or []
        self.leader = leader
        self.kwargs = kwargs


class MockSearch:
    """Mock web search tool."""
    pass


class MockGitTools:
    """Mock GitTools."""
    
    def __init__(self, base_dir=""):
        self.base_dir = base_dir


class TestMotionGraphicsTeam:
    """Test motion graphics team preset."""
    
    @patch('praisonai_tools.video.motion_graphics.team.AgentTeam', MockAgentTeam)
    @patch('praisonai_tools.video.motion_graphics.team.Agent', MockAgent)
    @patch('praisonai_tools.video.motion_graphics.team.search_web', MockSearch())
    def test_team_missing_praisonaiagents(self):
        """Test team creation when praisonaiagents is not available."""
        with patch('praisonai_tools.video.motion_graphics.team.AgentTeam', None):
            with pytest.raises(ImportError, match="praisonaiagents not available"):
                motion_graphics_team()
    
    @patch('praisonai_tools.video.motion_graphics.team.AgentTeam', MockAgentTeam)
    @patch('praisonai_tools.video.motion_graphics.team.Agent', MockAgent)
    @patch('praisonai_tools.video.motion_graphics.team.search_web', MockSearch())
    @patch('praisonai_tools.video.motion_graphics.team.create_motion_graphics_agent')
    def test_team_default_configuration(self, mock_create_agent):
        """Test team with default configuration."""
        mock_animator = MockAgent(name="animator")
        mock_create_agent.return_value = mock_animator
        
        with tempfile.TemporaryDirectory() as tmpdir:
            team = motion_graphics_team(workspace=tmpdir)
            
            assert isinstance(team, MockAgentTeam)
            assert len(team.agents) == 4  # coordinator, researcher, code_explorer, animator
            
            # Check coordinator
            coordinator = team.agents[0]
            assert coordinator.name == "coordinator"
            assert "motion graphics team coordinator" in coordinator.instructions.lower()
            
            # Check researcher
            researcher = team.agents[1]
            assert researcher.name == "researcher"
            assert "research specialist" in researcher.instructions.lower()
            
            # Check code explorer
            code_explorer = team.agents[2]
            assert code_explorer.name == "code_explorer"
            assert "code exploration specialist" in code_explorer.instructions.lower()
            
            # Check animator
            animator = team.agents[3]
            assert animator is mock_animator
    
    @patch('praisonai_tools.video.motion_graphics.team.AgentTeam', MockAgentTeam)
    @patch('praisonai_tools.video.motion_graphics.team.Agent', MockAgent)
    @patch('praisonai_tools.video.motion_graphics.team.search_web', None)  # No search available
    @patch('praisonai_tools.video.motion_graphics.team.create_motion_graphics_agent')
    def test_team_no_research(self, mock_create_agent):
        """Test team creation without research capability."""
        mock_animator = MockAgent(name="animator")
        mock_create_agent.return_value = mock_animator
        
        with tempfile.TemporaryDirectory() as tmpdir:
            team = motion_graphics_team(research=False, workspace=tmpdir)
            
            # Should have coordinator, code_explorer, animator (no researcher)
            assert len(team.agents) == 3
            agent_names = [agent.name for agent in team.agents]
            assert "coordinator" in agent_names
            assert "code_explorer" in agent_names
            assert "animator" in agent_names
            assert "researcher" not in agent_names
    
    @patch('praisonai_tools.video.motion_graphics.team.AgentTeam', MockAgentTeam)
    @patch('praisonai_tools.video.motion_graphics.team.Agent', MockAgent)
    @patch('praisonai_tools.video.motion_graphics.team.search_web', MockSearch())
    @patch('praisonai_tools.video.motion_graphics.team.create_motion_graphics_agent')
    def test_team_no_code_exploration(self, mock_create_agent):
        """Test team creation without code exploration."""
        mock_animator = MockAgent(name="animator")
        mock_create_agent.return_value = mock_animator
        
        with tempfile.TemporaryDirectory() as tmpdir:
            team = motion_graphics_team(code_exploration=False, workspace=tmpdir)
            
            # Should have coordinator, researcher, animator (no code_explorer)
            assert len(team.agents) == 3
            agent_names = [agent.name for agent in team.agents]
            assert "coordinator" in agent_names
            assert "researcher" in agent_names
            assert "animator" in agent_names
            assert "code_explorer" not in agent_names
    
    @patch('praisonai_tools.video.motion_graphics.team.AgentTeam', MockAgentTeam)
    @patch('praisonai_tools.video.motion_graphics.team.Agent', MockAgent)
    @patch('praisonai_tools.video.motion_graphics.team.search_web', MockSearch())
    @patch('praisonai_tools.video.motion_graphics.team.create_motion_graphics_agent')
    def test_team_minimal_configuration(self, mock_create_agent):
        """Test team with minimal configuration."""
        mock_animator = MockAgent(name="animator")
        mock_create_agent.return_value = mock_animator
        
        with tempfile.TemporaryDirectory() as tmpdir:
            team = motion_graphics_team(
                research=False,
                code_exploration=False,
                workspace=tmpdir
            )
            
            # Should have only coordinator and animator
            assert len(team.agents) == 2
            agent_names = [agent.name for agent in team.agents]
            assert "coordinator" in agent_names
            assert "animator" in agent_names
    
    @patch('praisonai_tools.video.motion_graphics.team.AgentTeam', MockAgentTeam)
    @patch('praisonai_tools.video.motion_graphics.team.Agent', MockAgent)
    @patch('praisonai_tools.video.motion_graphics.team.search_web', MockSearch())
    @patch('praisonai_tools.video.motion_graphics.team.create_motion_graphics_agent')
    def test_team_custom_parameters(self, mock_create_agent):
        """Test team with custom parameters."""
        mock_animator = MockAgent(name="animator")
        mock_create_agent.return_value = mock_animator
        
        with tempfile.TemporaryDirectory() as tmpdir:
            team = motion_graphics_team(
                workspace=tmpdir,
                backend="html",
                llm="gpt-4",
                custom_param="test"
            )
            
            # Check that custom parameters are passed through
            assert team.kwargs == {"custom_param": "test"}
            
            # Check that workspace is set
            assert team._motion_graphics_workspace == Path(tmpdir)
            assert team._motion_graphics_backend == "html"
    
    @patch('praisonai_tools.video.motion_graphics.team.AgentTeam', MockAgentTeam)
    @patch('praisonai_tools.video.motion_graphics.team.Agent', MockAgent)
    @patch('praisonai_tools.video.motion_graphics.team.search_web', MockSearch())
    @patch('praisonai_tools.video.motion_graphics.team.create_motion_graphics_agent')
    def test_team_workspace_creation(self, mock_create_agent):
        """Test team creates workspace directory."""
        mock_animator = MockAgent(name="animator")
        mock_create_agent.return_value = mock_animator
        
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace_path = Path(tmpdir) / "custom_team_workspace"
            
            team = motion_graphics_team(workspace=workspace_path)
            
            assert workspace_path.exists()
            assert team._motion_graphics_workspace == workspace_path
    
    @patch('praisonai_tools.video.motion_graphics.team.AgentTeam', MockAgentTeam)
    @patch('praisonai_tools.video.motion_graphics.team.Agent', MockAgent)
    @patch('praisonai_tools.video.motion_graphics.team.search_web', MockSearch())
    @patch('praisonai_tools.video.motion_graphics.team.create_motion_graphics_agent')
    def test_team_auto_workspace(self, mock_create_agent):
        """Test team creates workspace automatically."""
        mock_animator = MockAgent(name="animator")
        mock_create_agent.return_value = mock_animator
        
        team = motion_graphics_team()
        
        # Should create workspace automatically
        assert hasattr(team, '_motion_graphics_workspace')
        assert team._motion_graphics_workspace.exists()
        assert "motion_graphics_team_" in str(team._motion_graphics_workspace)
    
    @patch('praisonai_tools.video.motion_graphics.team.AgentTeam', MockAgentTeam)
    @patch('praisonai_tools.video.motion_graphics.team.Agent', MockAgent)
    @patch('praisonai_tools.video.motion_graphics.team.search_web', MockSearch())
    @patch('praisonai_tools.video.motion_graphics.team.create_motion_graphics_agent')
    def test_coordinator_is_leader(self, mock_create_agent):
        """Test that coordinator is set as team leader."""
        mock_animator = MockAgent(name="animator")
        mock_create_agent.return_value = mock_animator
        
        with tempfile.TemporaryDirectory() as tmpdir:
            team = motion_graphics_team(workspace=tmpdir)
            
            assert team.leader is not None
            assert team.leader.name == "coordinator"
    
    @patch('praisonai_tools.video.motion_graphics.team.AgentTeam', MockAgentTeam)
    @patch('praisonai_tools.video.motion_graphics.team.Agent', MockAgent)
    @patch('praisonai_tools.video.motion_graphics.team.search_web', MockSearch())
    @patch('praisonai_tools.video.motion_graphics.team.create_motion_graphics_agent')
    @patch('praisonai_tools.tools.git_tools.GitTools', MockGitTools)
    def test_code_explorer_tools(self, mock_create_agent):
        """Test code explorer gets GitTools."""
        mock_animator = MockAgent(name="animator") 
        mock_create_agent.return_value = mock_animator
        
        with tempfile.TemporaryDirectory() as tmpdir:
            team = motion_graphics_team(workspace=tmpdir)
            
            # Find code explorer
            code_explorer = None
            for agent in team.agents:
                if agent.name == "code_explorer":
                    code_explorer = agent
                    break
            
            assert code_explorer is not None
            assert len(code_explorer.tools) == 1
            assert isinstance(code_explorer.tools[0], MockGitTools)
    
    @patch('praisonai_tools.video.motion_graphics.team.AgentTeam', MockAgentTeam)
    @patch('praisonai_tools.video.motion_graphics.team.Agent', MockAgent)
    @patch('praisonai_tools.video.motion_graphics.team.search_web', MockSearch())
    @patch('praisonai_tools.video.motion_graphics.team.create_motion_graphics_agent')
    def test_researcher_tools(self, mock_create_agent):
        """Test researcher gets search tools.""" 
        mock_animator = MockAgent(name="animator")
        mock_create_agent.return_value = mock_animator
        
        with tempfile.TemporaryDirectory() as tmpdir:
            team = motion_graphics_team(workspace=tmpdir)
            
            # Find researcher
            researcher = None
            for agent in team.agents:
                if agent.name == "researcher":
                    researcher = agent
                    break
            
            assert researcher is not None
            assert len(researcher.tools) == 1
            assert isinstance(researcher.tools[0], MockSearch)
    
    @patch('praisonai_tools.video.motion_graphics.team.AgentTeam', MockAgentTeam)
    @patch('praisonai_tools.video.motion_graphics.team.Agent', MockAgent)
    @patch('praisonai_tools.video.motion_graphics.team.search_web', MockSearch())
    @patch('praisonai_tools.video.motion_graphics.team.create_motion_graphics_agent')
    def test_coordinator_instructions(self, mock_create_agent):
        """Test coordinator has proper instructions."""
        mock_animator = MockAgent(name="animator")
        mock_create_agent.return_value = mock_animator
        
        with tempfile.TemporaryDirectory() as tmpdir:
            team = motion_graphics_team(workspace=tmpdir)
            
            coordinator = team.leader
            instructions = coordinator.instructions.lower()
            
            assert "coordinator" in instructions
            assert "output validation" in instructions
            assert "never fabricate" in instructions
            assert "concrete file path" in instructions
            assert "route" in instructions or "routing" in instructions