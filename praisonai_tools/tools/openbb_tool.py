"""OpenBB Tool for PraisonAI Agents.

Financial data using OpenBB.

Usage:
    from praisonai_tools import OpenBBTool
    
    openbb = OpenBBTool()
    data = openbb.get_stock("AAPL")
"""

import logging
from typing import Any, Dict, List, Optional, Union

from praisonai_tools.tools.base import BaseTool

logger = logging.getLogger(__name__)


class OpenBBTool(BaseTool):
    """Tool for OpenBB financial data."""
    
    name = "openbb"
    description = "Get financial data using OpenBB."
    
    def run(
        self,
        action: str = "stock",
        symbol: Optional[str] = None,
        **kwargs
    ) -> Union[str, Dict[str, Any], List[Dict[str, Any]]]:
        action = action.lower().replace("-", "_")
        
        if action == "stock":
            return self.get_stock(symbol=symbol)
        elif action == "news":
            return self.get_news(symbol=symbol)
        elif action == "crypto":
            return self.get_crypto(symbol=symbol)
        else:
            return {"error": f"Unknown action: {action}"}
    
    def get_stock(self, symbol: str) -> Dict[str, Any]:
        """Get stock data."""
        if not symbol:
            return {"error": "symbol is required"}
        
        try:
            from openbb import obb
        except ImportError:
            return {"error": "openbb not installed. Install with: pip install openbb"}
        
        try:
            data = obb.equity.price.quote(symbol)
            return data.to_dict() if hasattr(data, "to_dict") else {"data": str(data)}
        except Exception as e:
            logger.error(f"OpenBB get_stock error: {e}")
            return {"error": str(e)}
    
    def get_news(self, symbol: str = None) -> List[Dict[str, Any]]:
        """Get financial news."""
        try:
            from openbb import obb
        except ImportError:
            return [{"error": "openbb not installed"}]
        
        try:
            if symbol:
                data = obb.news.company(symbol)
            else:
                data = obb.news.world()
            return data.to_list() if hasattr(data, "to_list") else [{"data": str(data)}]
        except Exception as e:
            logger.error(f"OpenBB get_news error: {e}")
            return [{"error": str(e)}]
    
    def get_crypto(self, symbol: str) -> Dict[str, Any]:
        """Get crypto data."""
        if not symbol:
            return {"error": "symbol is required"}
        
        try:
            from openbb import obb
        except ImportError:
            return {"error": "openbb not installed"}
        
        try:
            data = obb.crypto.price.historical(symbol)
            return data.to_dict() if hasattr(data, "to_dict") else {"data": str(data)}
        except Exception as e:
            logger.error(f"OpenBB get_crypto error: {e}")
            return {"error": str(e)}


def openbb_stock(symbol: str) -> Dict[str, Any]:
    """Get stock data."""
    return OpenBBTool().get_stock(symbol=symbol)
