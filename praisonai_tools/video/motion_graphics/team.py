"""Motion graphics team preset."""

import tempfile
from pathlib import Path
from typing import Union, Any, Optional

try:
    from praisonaiagents import Agent, AgentTeam
    from praisonaiagents.tools import FileTools, search_web
except ImportError:
    # Fallback for development
    Agent = None
    AgentTeam = None
    FileTools = None
    search_web = None

from .agent import create_motion_graphics_agent
from ..motion_graphics import protocols


def motion_graphics_team(
    *,
    research: bool = True,
    code_exploration: bool = True,
    backend: str = "html",
    workspace: Union[str, Path] = None,
    llm: str = "claude-sonnet-4",
    **team_kwargs: Any
) -> Any:
    """Create a motion graphics team preset.
    
    This team includes:
    - Coordinator: Routes requests and validates outputs
    - Researcher: Optional web search for content research  
    - CodeExplorer: Optional git repository exploration
    - Animator: HTML/GSAP composition authoring and rendering
    
    Args:
        research: Include research specialist
        code_exploration: Include code exploration specialist
        backend: Render backend name
        workspace: Workspace directory
        llm: LLM model to use
        **team_kwargs: Additional arguments for AgentTeam
        
    Returns:
        AgentTeam configured for motion graphics creation
    """
    if AgentTeam is None:
        raise ImportError(
            "praisonaiagents not available. Install with: pip install praisonaiagents"
        )
    
    # Set up workspace
    if workspace is None:
        workspace = Path(tempfile.mkdtemp(prefix="motion_graphics_team_"))
    else:
        workspace = Path(workspace)
    
    workspace.mkdir(parents=True, exist_ok=True)
    
    # Create agents
    agents = []
    
    # Coordinator agent with output validation
    coordinator = Agent(
        name="coordinator",
        instructions=f"""
You are the motion graphics team coordinator. Your role is to:

1. Analyze incoming requests and route them to appropriate specialists
2. Coordinate between team members 
3. Validate final outputs with strict rules
4. Return final results to users

CRITICAL OUTPUT VALIDATION RULES:
- A render succeeded ONLY IF the reply contains a concrete file path (e.g., '/renders/video_123.mp4') AND no error indicators
- Never fabricate file paths or claim success without concrete evidence
- Surface all errors from the Animator
- Stop work after maximum retry budget is exceeded

Routing guidelines:
- Use Researcher for gathering information about unfamiliar topics
- Use CodeExplorer for analyzing code repositories or programming concepts
- Always route to Animator for final HTML/GSAP authoring and rendering
- Validate that Animator provides concrete file paths before marking success

Team workspace: {workspace}
""",
        llm=llm
    )
    agents.append(coordinator)
    
    # Optional researcher
    if research and search_web is not None:
        researcher = Agent(
            name="researcher",
            instructions="""
You are a research specialist. Your role is to:

1. Search the web for information about topics in user requests
2. Gather relevant facts, concepts, and examples
3. Summarize findings in a brief that the Animator can use for on-screen content
4. Focus on visual concepts and explanations that work well in motion graphics

Keep research focused and concise - aim for key points that can become visual elements.
""",
            tools=[search_web],
            llm=llm
        )
        agents.append(researcher)
    
    # Optional code explorer  
    if code_exploration:
        from ...tools.git_tools import GitTools
        
        code_explorer = Agent(
            name="code_explorer", 
            instructions="""
You are a code exploration specialist. Your role is to:

1. Clone and explore git repositories on-demand
2. Read source code and understand implementations
3. Extract key algorithms, data structures, and concepts
4. Provide code walkthroughs that the Animator can visualize

IMPORTANT: You are READ-ONLY. Never write or modify code.
Always validate file paths to prevent directory traversal.

Focus on extracting the essential concepts that can be animated visually.
""",
            tools=[GitTools(base_dir=str(workspace / "repos"))],
            llm=llm
        )
        agents.append(code_explorer)
    
    # Animator - the core specialist
    animator = create_motion_graphics_agent(
        backend=backend,
        workspace=workspace / "animations",
        llm=llm
    )
    animator.name = "animator"
    agents.append(animator)
    
    # Create team with coordinator as leader
    team = AgentTeam(
        agents=agents,
        leader=coordinator,
        **team_kwargs
    )
    
    # Store team metadata
    team._motion_graphics_workspace = workspace
    team._motion_graphics_backend = backend
    
    return team