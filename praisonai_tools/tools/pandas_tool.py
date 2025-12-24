"""Pandas Tool for PraisonAI Agents.

DataFrame operations using Pandas.

Usage:
    from praisonai_tools import PandasTool
    
    pd_tool = PandasTool()
    data = pd_tool.read_csv("data.csv")
"""

import logging
from typing import Any, Dict, List, Optional, Union

from praisonai_tools.tools.base import BaseTool

logger = logging.getLogger(__name__)


class PandasTool(BaseTool):
    """Tool for Pandas DataFrame operations."""
    
    name = "pandas"
    description = "DataFrame operations using Pandas."
    
    def run(
        self,
        action: str = "read_csv",
        file_path: Optional[str] = None,
        **kwargs
    ) -> Union[str, Dict[str, Any], List[Dict[str, Any]]]:
        action = action.lower().replace("-", "_")
        
        if action == "read_csv":
            return self.read_csv(file_path=file_path, **kwargs)
        elif action == "read_excel":
            return self.read_excel(file_path=file_path, **kwargs)
        elif action == "read_json":
            return self.read_json(file_path=file_path)
        elif action == "describe":
            return self.describe(file_path=file_path)
        elif action == "query":
            return self.query(file_path=file_path, expr=kwargs.get("expr"))
        else:
            return {"error": f"Unknown action: {action}"}
    
    def read_csv(self, file_path: str, nrows: int = 100) -> List[Dict[str, Any]]:
        """Read CSV file."""
        if not file_path:
            return [{"error": "file_path is required"}]
        
        try:
            import pandas as pd
            df = pd.read_csv(file_path, nrows=nrows)
            return df.to_dict(orient="records")
        except ImportError:
            return [{"error": "pandas not installed"}]
        except Exception as e:
            logger.error(f"Pandas read_csv error: {e}")
            return [{"error": str(e)}]
    
    def read_excel(self, file_path: str, sheet_name: str = None, nrows: int = 100) -> List[Dict[str, Any]]:
        """Read Excel file."""
        if not file_path:
            return [{"error": "file_path is required"}]
        
        try:
            import pandas as pd
            df = pd.read_excel(file_path, sheet_name=sheet_name, nrows=nrows)
            return df.to_dict(orient="records")
        except ImportError:
            return [{"error": "pandas and openpyxl not installed"}]
        except Exception as e:
            logger.error(f"Pandas read_excel error: {e}")
            return [{"error": str(e)}]
    
    def read_json(self, file_path: str) -> List[Dict[str, Any]]:
        """Read JSON file."""
        if not file_path:
            return [{"error": "file_path is required"}]
        
        try:
            import pandas as pd
            df = pd.read_json(file_path)
            return df.to_dict(orient="records")
        except ImportError:
            return [{"error": "pandas not installed"}]
        except Exception as e:
            logger.error(f"Pandas read_json error: {e}")
            return [{"error": str(e)}]
    
    def describe(self, file_path: str) -> Dict[str, Any]:
        """Get DataFrame statistics."""
        if not file_path:
            return {"error": "file_path is required"}
        
        try:
            import pandas as pd
            df = pd.read_csv(file_path)
            return {
                "shape": df.shape,
                "columns": list(df.columns),
                "dtypes": df.dtypes.astype(str).to_dict(),
                "describe": df.describe().to_dict(),
            }
        except ImportError:
            return {"error": "pandas not installed"}
        except Exception as e:
            logger.error(f"Pandas describe error: {e}")
            return {"error": str(e)}
    
    def query(self, file_path: str, expr: str) -> List[Dict[str, Any]]:
        """Query DataFrame."""
        if not file_path or not expr:
            return [{"error": "file_path and expr are required"}]
        
        try:
            import pandas as pd
            df = pd.read_csv(file_path)
            result = df.query(expr)
            return result.to_dict(orient="records")
        except ImportError:
            return [{"error": "pandas not installed"}]
        except Exception as e:
            logger.error(f"Pandas query error: {e}")
            return [{"error": str(e)}]


def pandas_read_csv(file_path: str, nrows: int = 100) -> List[Dict[str, Any]]:
    """Read CSV with Pandas."""
    return PandasTool().read_csv(file_path=file_path, nrows=nrows)
