#!/usr/bin/env python3
"""Example usage of motion graphics video pipeline.

This example demonstrates how to use the motion graphics pipeline to create
videos from natural language prompts using HTML/GSAP animations.

Requirements:
    pip install praisonai-tools[video-motion]
    playwright install chromium
"""

import asyncio
import tempfile
from pathlib import Path

try:
    from praisonai_tools.video.motion_graphics import (
        create_motion_graphics_agent,
        motion_graphics_team,
        HtmlRenderBackend,
        RenderOpts
    )
    from praisonai_tools.tools.git_tools import GitTools
except ImportError as e:
    print(f"Import error: {e}")
    print("Please install with: pip install praisonai-tools[video-motion]")
    exit(1)


async def example_basic_animation():
    """Example 1: Basic motion graphics with simple animations."""
    print("Example 1: Creating basic motion graphics animation...")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir)
        
        # Create a simple HTML composition
        html_content = """
        <!DOCTYPE html>
        <html>
        <head>
            <script src="https://cdnjs.cloudflare.com/ajax/libs/gsap/3.12.2/gsap.min.js"></script>
            <style>
                body { margin: 0; padding: 0; background: #1a1a1a; overflow: hidden; font-family: Arial, sans-serif; }
                #stage { width: 1920px; height: 1080px; position: relative; }
                .title { font-size: 72px; color: #ffffff; position: absolute; top: 50%; left: 50%; 
                        transform: translate(-50%, -50%); opacity: 0; }
                .subtitle { font-size: 36px; color: #888; position: absolute; top: 60%; left: 50%; 
                           transform: translate(-50%, -50%); opacity: 0; }
            </style>
        </head>
        <body>
            <div id="stage" data-duration="3.0">
                <div class="title">Motion Graphics</div>
                <div class="subtitle">Powered by PraisonAI</div>
            </div>
            
            <script>
                const tl = gsap.timeline({ paused: true });
                
                // Animate title in
                tl.to(".title", { 
                    duration: 1, 
                    opacity: 1, 
                    y: -20, 
                    ease: "power2.out" 
                })
                // Animate subtitle in
                .to(".subtitle", { 
                    duration: 0.8, 
                    opacity: 1, 
                    y: -10, 
                    ease: "power2.out" 
                }, "-=0.3")
                // Hold for a moment
                .to({}, { duration: 1 })
                // Fade out
                .to([".title", ".subtitle"], { 
                    duration: 0.5, 
                    opacity: 0, 
                    ease: "power2.in" 
                });
                
                // Required: Export timeline
                window.__timelines = [tl];
            </script>
        </body>
        </html>
        """
        
        # Save HTML file
        (workspace / "index.html").write_text(html_content)
        
        # Create backend and render
        backend = HtmlRenderBackend()
        
        # Lint first
        lint_result = await backend.lint(workspace)
        print(f"Lint result: {'✓ Passed' if lint_result.ok else '✗ Failed'}")
        if not lint_result.ok:
            print(f"  Errors: {', '.join(lint_result.messages)}")
        
        # Render video
        if lint_result.ok:
            render_opts = RenderOpts(
                output_name="basic_animation.mp4",
                fps=30,
                quality="standard"
            )
            
            print("Rendering video... (this may take a moment)")
            render_result = await backend.render(workspace, render_opts)
            
            if render_result.ok:
                print(f"✓ Video rendered successfully!")
                print(f"  Output: {render_result.output_path}")
                print(f"  Size: {render_result.size_kb}KB")
            else:
                print(f"✗ Render failed: {render_result.stderr}")


async def example_git_tools():
    """Example 2: Using GitTools for code exploration."""
    print("\nExample 2: Using GitTools for safe git operations...")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        git_tools = GitTools(base_dir=tmpdir)
        
        print("Testing repository URL parsing...")
        
        # Test different repository formats
        test_repos = [
            "octocat/Hello-World",  # owner/repo format
            "https://github.com/octocat/Hello-World.git",  # HTTPS URL
        ]
        
        for repo_input in test_repos:
            try:
                url, name = git_tools._parse_repo_input(repo_input)
                print(f"  {repo_input} -> URL: {url}, Name: {name}")
            except Exception as e:
                print(f"  {repo_input} -> Error: {e}")
        
        print("\nTesting file path safety...")
        
        # Test file path validation
        test_paths = [
            "README.md",  # Safe
            "src/main.py",  # Safe
            "../etc/passwd",  # Unsafe
            "../../secret.txt",  # Unsafe
        ]
        
        for path in test_paths:
            try:
                safe_path = git_tools._validate_file_path(path)
                print(f"  {path} -> ✓ Safe: {safe_path}")
            except ValueError as e:
                print(f"  {path} -> ✗ Unsafe: {e}")


def example_agent_factory():
    """Example 3: Using motion graphics agent factory."""
    print("\nExample 3: Creating motion graphics agent...")
    
    try:
        # This would normally require praisonaiagents to be installed
        agent = create_motion_graphics_agent(
            backend="html",
            max_retries=3,
            llm="claude-sonnet-4"
        )
        
        print("✓ Motion graphics agent created successfully!")
        print(f"  Backend: {agent._motion_graphics_backend.__class__.__name__}")
        print(f"  Workspace: {agent._motion_graphics_workspace}")
        print(f"  Max retries: {agent._motion_graphics_max_retries}")
        
    except ImportError as e:
        print(f"⚠ Agent creation skipped: {e}")
        print("  Install praisonaiagents to use agent features")


def example_team_preset():
    """Example 4: Using motion graphics team preset."""
    print("\nExample 4: Creating motion graphics team...")
    
    try:
        team = motion_graphics_team(
            research=True,
            code_exploration=True,
            backend="html"
        )
        
        print("✓ Motion graphics team created successfully!")
        print(f"  Agents: {[agent.name for agent in team.agents]}")
        print(f"  Leader: {team.leader.name}")
        print(f"  Workspace: {team._motion_graphics_workspace}")
        
    except ImportError as e:
        print(f"⚠ Team creation skipped: {e}")
        print("  Install praisonaiagents to use team features")


async def main():
    """Run all examples."""
    print("Motion Graphics Pipeline Examples")
    print("=" * 50)
    
    # Example 1: Basic animation (requires Playwright)
    try:
        await example_basic_animation()
    except ImportError as e:
        print(f"Example 1 skipped: {e}")
        print("Install with: pip install playwright && playwright install chromium")
    except Exception as e:
        print(f"Example 1 failed: {e}")
    
    # Example 2: GitTools (no extra dependencies)
    await example_git_tools()
    
    # Example 3: Agent factory (requires praisonaiagents)
    example_agent_factory()
    
    # Example 4: Team preset (requires praisonaiagents)
    example_team_preset()
    
    print("\n" + "=" * 50)
    print("Examples complete!")
    print("\nNext steps:")
    print("1. Install optional dependencies: pip install praisonai-tools[video-motion]")
    print("2. Install Playwright: playwright install chromium")
    print("3. Install praisonaiagents for agent features")
    print("4. Try creating your own motion graphics!")


if __name__ == "__main__":
    asyncio.run(main())