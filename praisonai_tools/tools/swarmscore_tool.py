"""SwarmScore integration tool for PraisonAI.

SwarmScore is a portable trust rating system for AI agents based on verified execution history.
This tool allows agents to:
- Load their SwarmScore rating and certificate
- Verify SwarmScore freshness
- Access discovery manifest for agent-to-agent lookup

More information: https://swarmsync.ai/docs/protocol-specs/swarmscore
"""

import json
import logging
from typing import Dict, Any
from urllib.parse import urlparse, quote

try:
    import requests
except ImportError:
    requests = None

from .base import BaseTool, ToolResult

logger = logging.getLogger(__name__)


class SwarmScoreTool(BaseTool):
    """Tool for integrating with SwarmScore trust ratings."""
    
    name = "swarmscore"
    description = "Load and verify SwarmScore trust ratings for AI agents"
    
    def __init__(self, api_base_url: str = "https://api.swarmsync.ai/v1/swarmscore/"):
        """Initialize SwarmScore tool.
        
        Args:
            api_base_url: Base URL for SwarmScore API
        """
        if requests is None:
            raise ImportError("requests is required for SwarmScoreTool. Install with: pip install requests")
        
        super().__init__()
        self.api_base_url = api_base_url.rstrip('/')
        
    def load_swarmscore(self, slug: str) -> ToolResult:
        """Load SwarmScore data by agent slug.
        
        Args:
            slug: Agent slug identifier
            
        Returns:
            ToolResult containing SwarmScore data including passport, certificate, and verification payload
        """
        try:
            url = f"{self.api_base_url}/load-by-slug/{quote(slug, safe='')}"
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            return ToolResult(
                output=data,
                success=True,
                metadata={"message": f"Successfully loaded SwarmScore for agent '{slug}'"}
            )
            
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON response for SwarmScore {slug}: {e}")
            return ToolResult(
                output=None,
                success=False,
                error="Invalid response format from SwarmScore API"
            )
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to load SwarmScore for {slug}: {e}")
            return ToolResult(
                output=None,
                success=False,
                error=f"Failed to load SwarmScore: {str(e)}"
            )
    
    def verify_swarmscore(self, verify_payload: Dict[str, Any]) -> ToolResult:
        """Verify SwarmScore freshness using verification payload.
        
        Args:
            verify_payload: Verification payload from load_swarmscore response
            
        Returns:
            ToolResult containing verification status
        """
        try:
            url = f"{self.api_base_url}/verify"
            response = requests.post(
                url,
                json=verify_payload,
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            response.raise_for_status()
            
            data = response.json()
            
            return ToolResult(
                output=data,
                success=True,
                metadata={"message": "SwarmScore verification completed"}
            )
            
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON response for SwarmScore verification: {e}")
            return ToolResult(
                output=None,
                success=False,
                error="Invalid response format from verification API"
            )
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to verify SwarmScore: {e}")
            return ToolResult(
                output=None,
                success=False,
                error=f"Failed to verify SwarmScore: {str(e)}"
            )
    
    def get_discovery_manifest(self) -> ToolResult:
        """Get machine-readable agent discovery manifest.
        
        Returns:
            ToolResult containing discovery manifest data
        """
        try:
            parsed = urlparse(self.api_base_url)
            base = f"{parsed.scheme}://{parsed.netloc}"
            url = f"{base}/.well-known/agent-card.json"
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            return ToolResult(
                output=data,
                success=True,
                metadata={"message": "Retrieved SwarmScore discovery manifest"}
            )
            
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in discovery manifest: {e}")
            return ToolResult(
                output=None,
                success=False,
                error="Invalid discovery manifest format"
            )
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to get discovery manifest: {e}")
            return ToolResult(
                output=None,
                success=False,
                error=f"Failed to get discovery manifest: {str(e)}"
            )

    def run(self, action: str = "load", **kwargs) -> ToolResult:
        """Execute SwarmScore action.
        
        Args:
            action: Action to perform ('load', 'verify', or 'discover')
            **kwargs: Action-specific parameters
            
        Returns:
            ToolResult with action results
        """
        if action == "load":
            slug = kwargs.get("slug")
            if not slug:
                return ToolResult(
                    output=None,
                    success=False,
                    error="Missing required parameter 'slug' for load action"
                )
            return self.load_swarmscore(slug)
        
        elif action == "verify":
            verify_payload = kwargs.get("verify_payload")
            if not verify_payload:
                return ToolResult(
                    output=None,
                    success=False,
                    error="Missing required parameter 'verify_payload' for verify action"
                )
            return self.verify_swarmscore(verify_payload)
        
        elif action == "discover":
            return self.get_discovery_manifest()
        
        else:
            return ToolResult(
                output=None,
                success=False,
                error=f"Unknown action '{action}'. Supported actions: load, verify, discover"
            )


# Standalone functions for easy agent integration
def load_swarmscore_by_slug(slug: str) -> Dict[str, Any]:
    """Load SwarmScore data by agent slug.
    
    Args:
        slug: Agent slug identifier
        
    Returns:
        Dictionary containing SwarmScore data
        
    Raises:
        Exception: If loading fails
    """
    tool = SwarmScoreTool()
    result = tool.load_swarmscore(slug)
    
    if not result.success:
        raise Exception(result.error)
    
    return result.output


def verify_swarmscore_freshness(verify_payload: Dict[str, Any]) -> Dict[str, Any]:
    """Verify SwarmScore freshness.
    
    Args:
        verify_payload: Verification payload from load response
        
    Returns:
        Dictionary containing verification results
        
    Raises:
        Exception: If verification fails
    """
    tool = SwarmScoreTool()
    result = tool.verify_swarmscore(verify_payload)
    
    if not result.success:
        raise Exception(result.error)
    
    return result.output


def get_agent_discovery_manifest() -> Dict[str, Any]:
    """Get machine-readable agent discovery manifest.
    
    Returns:
        Dictionary containing discovery manifest
        
    Raises:
        Exception: If retrieval fails
    """
    tool = SwarmScoreTool()
    result = tool.get_discovery_manifest()
    
    if not result.success:
        raise Exception(result.error)
    
    return result.output