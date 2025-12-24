"""CSV Tool for PraisonAI Agents.

CSV file operations.

Usage:
    from praisonai_tools import CSVTool
    
    csv = CSVTool()
    data = csv.read("data.csv")
"""

import logging
from typing import Any, Dict, List, Optional, Union

from praisonai_tools.tools.base import BaseTool

logger = logging.getLogger(__name__)


class CSVTool(BaseTool):
    """Tool for CSV file operations."""
    
    name = "csv"
    description = "Read and write CSV files."
    
    def run(
        self,
        action: str = "read",
        file_path: Optional[str] = None,
        **kwargs
    ) -> Union[str, Dict[str, Any], List[Dict[str, Any]]]:
        action = action.lower().replace("-", "_")
        
        if action == "read":
            return self.read(file_path=file_path, **kwargs)
        elif action == "write":
            return self.write(file_path=file_path, data=kwargs.get("data"))
        elif action == "query":
            return self.query(file_path=file_path, sql=kwargs.get("sql"))
        else:
            return {"error": f"Unknown action: {action}"}
    
    def read(self, file_path: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Read CSV file."""
        if not file_path:
            return [{"error": "file_path is required"}]
        
        try:
            import csv
            with open(file_path, "r", newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                rows = []
                for i, row in enumerate(reader):
                    if i >= limit:
                        break
                    rows.append(dict(row))
                return rows
        except Exception as e:
            logger.error(f"CSV read error: {e}")
            return [{"error": str(e)}]
    
    def write(self, file_path: str, data: List[Dict]) -> Dict[str, Any]:
        """Write CSV file."""
        if not file_path or not data:
            return {"error": "file_path and data are required"}
        
        try:
            import csv
            fieldnames = list(data[0].keys())
            with open(file_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(data)
            return {"success": True, "rows_written": len(data)}
        except Exception as e:
            logger.error(f"CSV write error: {e}")
            return {"error": str(e)}
    
    def query(self, file_path: str, sql: str) -> List[Dict[str, Any]]:
        """Query CSV with SQL using DuckDB."""
        if not file_path or not sql:
            return [{"error": "file_path and sql are required"}]
        
        try:
            import duckdb
            result = duckdb.query(sql.replace("$FILE", f"'{file_path}'")).fetchdf()
            return result.to_dict(orient="records")
        except ImportError:
            return [{"error": "duckdb not installed for SQL queries"}]
        except Exception as e:
            logger.error(f"CSV query error: {e}")
            return [{"error": str(e)}]


def read_csv(file_path: str, limit: int = 100) -> List[Dict[str, Any]]:
    """Read CSV file."""
    return CSVTool().read(file_path=file_path, limit=limit)
