"""Yahoo Finance Tool for PraisonAI Agents.

Get stock data and financial information.

Usage:
    from praisonai_tools import YFinanceTool
    
    yf = YFinanceTool()
    data = yf.get_stock("AAPL")
"""

import logging
from typing import Any, Dict, List, Optional, Union

from praisonai_tools.tools.base import BaseTool

logger = logging.getLogger(__name__)


class YFinanceTool(BaseTool):
    """Tool for Yahoo Finance data."""
    
    name = "yfinance"
    description = "Get stock prices, financial data, and market information."
    
    def __init__(self):
        super().__init__()
    
    def run(
        self,
        action: str = "get_stock",
        symbol: Optional[str] = None,
        period: str = "1mo",
        **kwargs
    ) -> Union[str, Dict[str, Any], List[Dict[str, Any]]]:
        action = action.lower().replace("-", "_")
        
        if action == "get_stock":
            return self.get_stock(symbol=symbol)
        elif action == "get_history":
            return self.get_history(symbol=symbol, period=period)
        elif action == "get_info":
            return self.get_info(symbol=symbol)
        elif action == "get_news":
            return self.get_news(symbol=symbol)
        else:
            return {"error": f"Unknown action: {action}"}
    
    def get_stock(self, symbol: str) -> Dict[str, Any]:
        """Get current stock price."""
        if not symbol:
            return {"error": "symbol is required"}
        
        try:
            import yfinance as yf
        except ImportError:
            return {"error": "yfinance not installed. Install with: pip install yfinance"}
        
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            
            return {
                "symbol": symbol.upper(),
                "name": info.get("longName") or info.get("shortName"),
                "price": info.get("currentPrice") or info.get("regularMarketPrice"),
                "previous_close": info.get("previousClose"),
                "open": info.get("open"),
                "day_high": info.get("dayHigh"),
                "day_low": info.get("dayLow"),
                "volume": info.get("volume"),
                "market_cap": info.get("marketCap"),
                "currency": info.get("currency"),
            }
        except Exception as e:
            logger.error(f"YFinance get_stock error: {e}")
            return {"error": str(e)}
    
    def get_history(self, symbol: str, period: str = "1mo") -> List[Dict[str, Any]]:
        """Get historical prices."""
        if not symbol:
            return [{"error": "symbol is required"}]
        
        try:
            import yfinance as yf
        except ImportError:
            return [{"error": "yfinance not installed"}]
        
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period=period)
            
            results = []
            for date, row in hist.iterrows():
                results.append({
                    "date": str(date.date()),
                    "open": round(row["Open"], 2),
                    "high": round(row["High"], 2),
                    "low": round(row["Low"], 2),
                    "close": round(row["Close"], 2),
                    "volume": int(row["Volume"]),
                })
            return results
        except Exception as e:
            logger.error(f"YFinance get_history error: {e}")
            return [{"error": str(e)}]
    
    def get_info(self, symbol: str) -> Dict[str, Any]:
        """Get detailed company info."""
        if not symbol:
            return {"error": "symbol is required"}
        
        try:
            import yfinance as yf
        except ImportError:
            return {"error": "yfinance not installed"}
        
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            
            return {
                "symbol": symbol.upper(),
                "name": info.get("longName"),
                "sector": info.get("sector"),
                "industry": info.get("industry"),
                "country": info.get("country"),
                "website": info.get("website"),
                "employees": info.get("fullTimeEmployees"),
                "summary": info.get("longBusinessSummary", "")[:500],
                "pe_ratio": info.get("trailingPE"),
                "eps": info.get("trailingEps"),
                "dividend_yield": info.get("dividendYield"),
                "52_week_high": info.get("fiftyTwoWeekHigh"),
                "52_week_low": info.get("fiftyTwoWeekLow"),
            }
        except Exception as e:
            logger.error(f"YFinance get_info error: {e}")
            return {"error": str(e)}
    
    def get_news(self, symbol: str) -> List[Dict[str, Any]]:
        """Get stock news."""
        if not symbol:
            return [{"error": "symbol is required"}]
        
        try:
            import yfinance as yf
        except ImportError:
            return [{"error": "yfinance not installed"}]
        
        try:
            ticker = yf.Ticker(symbol)
            news = ticker.news
            
            return [
                {
                    "title": n.get("title"),
                    "publisher": n.get("publisher"),
                    "link": n.get("link"),
                    "published": n.get("providerPublishTime"),
                }
                for n in news[:10]
            ]
        except Exception as e:
            logger.error(f"YFinance get_news error: {e}")
            return [{"error": str(e)}]


def get_stock_price(symbol: str) -> Dict[str, Any]:
    """Get stock price."""
    return YFinanceTool().get_stock(symbol=symbol)
