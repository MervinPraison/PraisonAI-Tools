"""Inkog Security Analysis Tool for PraisonAI Agents.

Security analysis for AI agent code using Inkog.
Detects token bombing, prompt injection, missing oversight, and compliance gaps.

Usage:
    from praisonai_tools import InkogTool
    
    inkog = InkogTool()
    results = inkog.scan_directory("./my-agent")
    
    # Or use standalone functions
    from praisonai_tools.tools.inkog_tool import scan_agent_code
    results = scan_agent_code("./my-agent")

Features:
- Static analysis of AI agent code
- Token bombing detection
- Prompt injection vulnerability scanning  
- Recursive tool calling detection
- EU AI Act / NIST / OWASP compliance mapping
- Support for 21+ frameworks (LangChain, CrewAI, AutoGen, etc.)
- Multiple output formats (text, JSON, HTML, SARIF)

Environment Variables:
    INKOG_API_KEY: API key from app.inkog.io (required)
    INKOG_SERVER_URL: Custom server URL (optional)
"""

import os
import json
import logging
import subprocess
from typing import Any, Dict, Optional, Union

from praisonai_tools.tools.base import BaseTool

logger = logging.getLogger(__name__)


def _check_inkog_available(api_key: Optional[str] = None) -> tuple[bool, Optional[str]]:
    """Check if inkog CLI is available and properly configured.
    
    Args:
        api_key: Optional API key to validate. Falls back to the
            INKOG_API_KEY environment variable when not provided.
    
    Returns:
        Tuple of (is_available, error_message)
    """
    # Check if inkog CLI is installed
    try:
        result = subprocess.run(
            ["inkog", "-version"], 
            capture_output=True, 
            text=True, 
            timeout=10
        )
        if result.returncode != 0:
            return False, "inkog CLI is not properly installed. Install with: brew tap inkog-io/inkog && brew install inkog"
    except FileNotFoundError:
        return False, "inkog CLI is not installed. Install with: brew tap inkog-io/inkog && brew install inkog"
    except subprocess.TimeoutExpired:
        return False, "inkog CLI is not responding. Please check installation."
    except Exception as e:
        return False, f"Error checking inkog installation: {e}"
    
    # Check for API key (instance-provided key takes precedence over env var)
    api_key = api_key or os.environ.get("INKOG_API_KEY")
    if not api_key:
        return False, "INKOG_API_KEY environment variable is required. Get your free key at https://app.inkog.io"
    
    return True, None


class InkogTool(BaseTool):
    """Comprehensive security analysis tool for AI agent code using Inkog.
    
    Inkog provides static analysis specifically designed for AI agents, detecting:
    - Token bombing attacks (loops where LLM controls termination)
    - Prompt injection vulnerabilities
    - Recursive tool calling without cycle detection
    - Missing human oversight for destructive operations
    - Cross-tenant data leakage
    - MCP tool poisoning
    
    Supports 21+ frameworks including LangChain, CrewAI, AutoGen, OpenAI Agents,
    and provides compliance mapping to EU AI Act, NIST AI RMF, and OWASP LLM Top 10.
    
    Requires:
    - inkog CLI: brew tap inkog-io/inkog && brew install inkog
    - INKOG_API_KEY environment variable (free at app.inkog.io)
    """
    
    name = "inkog_security"
    description = "Analyze AI agent code for security vulnerabilities using Inkog static analysis."
    
    def __init__(self, api_key: Optional[str] = None, server_url: Optional[str] = None):
        """Initialize InkogTool.
        
        Args:
            api_key: Optional API key. If not provided, uses INKOG_API_KEY env var.
            server_url: Optional server URL. If not provided, uses INKOG_SERVER_URL env var.
        """
        super().__init__()
        self._api_key = api_key
        self._server_url = server_url
    
    def _get_api_key(self) -> Optional[str]:
        """Get API key from instance or environment."""
        return self._api_key or os.environ.get("INKOG_API_KEY")
    
    def _get_server_url(self) -> Optional[str]:
        """Get server URL from instance or environment."""
        return self._server_url or os.environ.get("INKOG_SERVER_URL")
    
    def run(
        self,
        action: str = "scan",
        path: str = ".",
        output_format: str = "json",
        policy: str = "balanced",
        severity: str = "low", 
        deep: bool = False,
        **kwargs
    ) -> Union[str, Dict[str, Any]]:
        """Execute inkog security analysis.
        
        Args:
            action: Action to perform ("scan", "skill-scan", "mcp-scan")
            path: Path to scan (directory or file)
            output_format: Output format ("json", "text", "html", "sarif")
            policy: Security policy ("low-noise", "balanced", "comprehensive")
            severity: Minimum severity ("critical", "high", "medium", "low")
            deep: Enable deep scan with AI orchestrator analysis
            **kwargs: Additional arguments
            
        Returns:
            Scan results as dict (JSON) or formatted string (text/html)
        """
        action = action.lower().replace("-", "_")
        
        if action == "scan":
            return self.scan_directory(
                path=path,
                output_format=output_format,
                policy=policy,
                severity=severity,
                deep=deep
            )
        elif action == "skill_scan":
            return self.skill_scan(
                path=path,
                output_format=output_format,
                deep=deep,
                repo=kwargs.get("repo")
            )
        elif action == "mcp_scan":
            return self.mcp_scan(
                server_name=kwargs.get("server_name", path),
                output_format=output_format,
                deep=deep,
                repo=kwargs.get("repo")
            )
        else:
            return {"error": f"Unknown action: {action}"}
    
    def scan_directory(
        self,
        path: str = ".",
        output_format: str = "json",
        policy: str = "balanced",
        severity: str = "low",
        deep: bool = False,
        verbose: bool = False
    ) -> Union[Dict[str, Any], str]:
        """Scan a directory or file for AI agent security vulnerabilities.
        
        Args:
            path: Path to scan (directory or file)
            output_format: Output format ("json", "text", "html", "sarif")  
            policy: Security policy ("low-noise", "balanced", "comprehensive")
            severity: Minimum severity level ("critical", "high", "medium", "low")
            deep: Enable deep scan with AI orchestrator analysis
            verbose: Enable verbose output
            
        Returns:
            Scan results as dict (JSON format) or string (other formats)
        """
        is_available, error = _check_inkog_available(self._get_api_key())
        if not is_available:
            logger.error(error)
            return {"error": error}
        
        try:
            # Build command
            cmd = ["inkog"]
            
            if deep:
                cmd.append("-deep")
            
            cmd.extend([
                "-output", output_format,
                "-policy", policy,
                "-severity", severity,
            ])
            
            if verbose:
                cmd.append("-verbose")
            
            # Add server URL if specified
            server_url = self._get_server_url()
            if server_url:
                cmd.extend(["-server", server_url])
            
            # Add path
            cmd.append(path)
            
            # Set environment
            env = os.environ.copy()
            api_key = self._get_api_key()
            if api_key:
                env["INKOG_API_KEY"] = api_key
            
            # Execute scan
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                env=env,
                timeout=300  # 5 minutes timeout
            )
            
            if result.returncode != 0:
                error_msg = f"Inkog scan failed: {result.stderr or result.stdout}"
                logger.error(error_msg)
                return {"error": error_msg}
            
            # Parse output based on format
            if output_format == "json":
                try:
                    return json.loads(result.stdout)
                except json.JSONDecodeError as e:
                    return {"error": f"Failed to parse JSON output: {e}", "raw_output": result.stdout}
            else:
                return result.stdout
                
        except subprocess.TimeoutExpired:
            error_msg = "Inkog scan timed out after 5 minutes"
            logger.error(error_msg)
            return {"error": error_msg}
        except Exception as e:
            error_msg = f"Inkog scan error: {str(e)}"
            logger.error(error_msg)
            return {"error": error_msg}
    
    def skill_scan(
        self,
        path: str = ".",
        output_format: str = "json",
        deep: bool = False,
        repo: Optional[str] = None
    ) -> Union[Dict[str, Any], str]:
        """Scan SKILL.md packages and agent tools for security vulnerabilities.
        
        Args:
            path: Path to scan or server name
            output_format: Output format ("json", "text", "html", "sarif")
            deep: Enable deep scan with AI orchestrator analysis  
            repo: Repository URL to scan
            
        Returns:
            Scan results as dict (JSON format) or string (other formats)
        """
        is_available, error = _check_inkog_available(self._get_api_key())
        if not is_available:
            logger.error(error)
            return {"error": error}
        
        try:
            # Build command
            cmd = ["inkog", "skill-scan"]
            
            if deep:
                cmd.append("-deep")
            
            cmd.extend(["-output", output_format])
            
            if repo:
                cmd.extend(["-repo", repo])
            else:
                cmd.append(path)
            
            # Set environment
            env = os.environ.copy()
            api_key = self._get_api_key()
            if api_key:
                env["INKOG_API_KEY"] = api_key
            
            # Execute scan
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                env=env,
                timeout=300
            )
            
            if result.returncode != 0:
                error_msg = f"Inkog skill scan failed: {result.stderr or result.stdout}"
                logger.error(error_msg)
                return {"error": error_msg}
            
            # Parse output based on format
            if output_format == "json":
                try:
                    return json.loads(result.stdout)
                except json.JSONDecodeError as e:
                    return {"error": f"Failed to parse JSON output: {e}", "raw_output": result.stdout}
            else:
                return result.stdout
                
        except subprocess.TimeoutExpired:
            error_msg = "Inkog skill scan timed out after 5 minutes"
            logger.error(error_msg)
            return {"error": error_msg}
        except Exception as e:
            error_msg = f"Inkog skill scan error: {str(e)}"
            logger.error(error_msg)
            return {"error": error_msg}
    
    def mcp_scan(
        self,
        server_name: str,
        output_format: str = "json",
        deep: bool = False,
        repo: Optional[str] = None
    ) -> Union[Dict[str, Any], str]:
        """Scan MCP servers for security vulnerabilities.
        
        Args:
            server_name: MCP server name to scan
            output_format: Output format ("json", "text", "html", "sarif")
            deep: Enable deep scan with AI orchestrator analysis
            repo: Repository URL for the MCP server source code
            
        Returns:
            Scan results as dict (JSON format) or string (other formats)
        """
        is_available, error = _check_inkog_available(self._get_api_key())
        if not is_available:
            logger.error(error)
            return {"error": error}
        
        try:
            # Build command
            cmd = ["inkog", "mcp-scan"]
            
            if deep:
                cmd.append("-deep")
            
            cmd.extend(["-output", output_format])
            
            if repo:
                cmd.extend(["-repo", repo])
            
            cmd.append(server_name)
            
            # Set environment
            env = os.environ.copy()
            api_key = self._get_api_key()
            if api_key:
                env["INKOG_API_KEY"] = api_key
            
            # Execute scan
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                env=env,
                timeout=300
            )
            
            if result.returncode != 0:
                error_msg = f"Inkog MCP scan failed: {result.stderr or result.stdout}"
                logger.error(error_msg)
                return {"error": error_msg}
            
            # Parse output based on format
            if output_format == "json":
                try:
                    return json.loads(result.stdout)
                except json.JSONDecodeError as e:
                    return {"error": f"Failed to parse JSON output: {e}", "raw_output": result.stdout}
            else:
                return result.stdout
                
        except subprocess.TimeoutExpired:
            error_msg = "Inkog MCP scan timed out after 5 minutes"
            logger.error(error_msg)
            return {"error": error_msg}
        except Exception as e:
            error_msg = f"Inkog MCP scan error: {str(e)}"
            logger.error(error_msg)
            return {"error": error_msg}
    
    def analyze_findings(self, scan_results: Union[Dict[str, Any], str]) -> str:
        """Analyze scan results and provide a summary.
        
        Args:
            scan_results: Results from a JSON format scan. Non-dict inputs
                (e.g. text/HTML output) are returned as-is.
            
        Returns:
            Human-readable analysis summary
        """
        try:
            if not isinstance(scan_results, dict):
                return str(scan_results)
            
            if "error" in scan_results:
                return f"Scan failed: {scan_results['error']}"
            
            summary = scan_results.get("summary", {})
            total_findings = summary.get("total_findings", 0)
            
            if total_findings == 0:
                return "✅ No security vulnerabilities found in the agent code."
            
            # Build severity breakdown
            critical = summary.get("critical", 0)
            high = summary.get("high", 0)
            medium = summary.get("medium", 0)
            low = summary.get("low", 0)
            
            analysis = "🔍 Security Analysis Results:\n"
            analysis += f"Total Findings: {total_findings}\n\n"
            
            if critical > 0:
                analysis += f"🔴 CRITICAL: {critical} findings - Immediate attention required\n"
            if high > 0:
                analysis += f"🟠 HIGH: {high} findings - Should be addressed soon\n"
            if medium > 0:
                analysis += f"🟡 MEDIUM: {medium} findings - Review recommended\n"
            if low > 0:
                analysis += f"⚪ LOW: {low} findings - Minor issues\n"
            
            # Add key finding types if available
            findings = scan_results.get("server_findings", [])
            if findings:
                patterns = set()
                for finding in findings[:5]:  # Show top 5 patterns
                    pattern = finding.get("pattern", "Unknown")
                    patterns.add(pattern)
                
                if patterns:
                    analysis += "\nKey Vulnerability Types Detected:\n"
                    for pattern in sorted(patterns):
                        analysis += f"• {pattern}\n"
            
            # Risk recommendations
            if critical > 0 or high > 0:
                analysis += "\n⚠️ Recommendation: Address critical and high severity findings before deployment."
            
            return analysis
            
        except Exception as e:
            return f"Error analyzing scan results: {e}"


# Standalone functions for direct import and use
def scan_agent_code(
    path: str = ".",
    output_format: str = "json", 
    policy: str = "balanced",
    severity: str = "low",
    deep: bool = False
) -> Union[Dict[str, Any], str]:
    """Scan AI agent code for security vulnerabilities using Inkog.
    
    Args:
        path: Path to scan (directory or file)
        output_format: Output format ("json", "text", "html", "sarif")
        policy: Security policy ("low-noise", "balanced", "comprehensive")
        severity: Minimum severity level ("critical", "high", "medium", "low")
        deep: Enable deep scan with AI orchestrator analysis
        
    Returns:
        Scan results as dict (JSON format) or string (other formats)
    """
    tool = InkogTool()
    return tool.scan_directory(
        path=path,
        output_format=output_format,
        policy=policy,
        severity=severity,
        deep=deep
    )


def scan_skill_package(
    path: str = ".",
    deep: bool = False,
    repo: Optional[str] = None
) -> Dict[str, Any]:
    """Scan SKILL.md packages for security vulnerabilities.
    
    Args:
        path: Path to scan
        deep: Enable deep scan with AI orchestrator analysis
        repo: Repository URL to scan
        
    Returns:
        Scan results as dict
    """
    tool = InkogTool()
    return tool.skill_scan(path=path, deep=deep, repo=repo)


def scan_mcp_server(
    server_name: str,
    deep: bool = False,
    repo: Optional[str] = None
) -> Dict[str, Any]:
    """Scan MCP server for security vulnerabilities.
    
    Args:
        server_name: MCP server name to scan
        deep: Enable deep scan with AI orchestrator analysis
        repo: Repository URL for the MCP server
        
    Returns:
        Scan results as dict
    """
    tool = InkogTool()
    return tool.mcp_scan(server_name=server_name, deep=deep, repo=repo)


# Example usage and testing
if __name__ == "__main__":
    print("\n" + "="*60)
    print("Inkog Security Analysis Tool Demonstration")
    print("="*60 + "\n")
    
    # Check if inkog is available
    is_available, error = _check_inkog_available()
    if not is_available:
        print(f"❌ Error: {error}")
        print("\nTo use Inkog tools:")
        print("1. Install CLI: brew tap inkog-io/inkog && brew install inkog")
        print("2. Get API key: https://app.inkog.io")
        print("3. Set environment: export INKOG_API_KEY=your_key_here")
    else:
        print("✅ Inkog is available and configured!")
        
        # Example usage with current directory
        try:
            print("\nScanning current directory for security vulnerabilities...")
            result = scan_agent_code(".", output_format="json", policy="balanced")
            
            if isinstance(result, dict) and "error" not in result:
                tool = InkogTool()
                analysis = tool.analyze_findings(result)
                print(analysis)
            else:
                print("Scan completed:", result)
                
        except Exception as e:
            print(f"Demo error: {e}")