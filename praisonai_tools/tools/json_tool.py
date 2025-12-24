"""JSON Tool for PraisonAI Agents.

JSON file operations.

Usage:
    from praisonai_tools import JSONTool
    
    json_tool = JSONTool()
    data = json_tool.read("data.json")
"""

import json
import logging
from typing import Any, Dict, List, Optional, Union

from praisonai_tools.tools.base import BaseTool

logger = logging.getLogger(__name__)


class JSONTool(BaseTool):
    """Tool for JSON file operations."""
    
    name = "json"
    description = "Read and write JSON files."
    
    def run(
        self,
        action: str = "read",
        file_path: Optional[str] = None,
        data: Optional[Any] = None,
        **kwargs
    ) -> Union[str, Dict[str, Any], List[Dict[str, Any]]]:
        action = action.lower().replace("-", "_")
        
        if action == "read":
            return self.read(file_path=file_path)
        elif action == "write":
            return self.write(file_path=file_path, data=data)
        elif action == "query":
            return self.query(file_path=file_path, path=kwargs.get("path"))
        else:
            return {"error": f"Unknown action: {action}"}
    
    def read(self, file_path: str) -> Union[Dict, List]:
        """Read JSON file."""
        if not file_path:
            return {"error": "file_path is required"}
        
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"JSON read error: {e}")
            return {"error": str(e)}
    
    def write(self, file_path: str, data: Any) -> Dict[str, Any]:
        """Write JSON file."""
        if not file_path or data is None:
            return {"error": "file_path and data are required"}
        
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            return {"success": True, "file_path": file_path}
        except Exception as e:
            logger.error(f"JSON write error: {e}")
            return {"error": str(e)}
    
    def query(self, file_path: str, path: str) -> Any:
        """Query JSON with JSONPath-like syntax."""
        if not file_path or not path:
            return {"error": "file_path and path are required"}
        
        try:
            data = self.read(file_path)
            if isinstance(data, dict) and "error" in data:
                return data
            
            parts = path.strip(".").split(".")
            result = data
            for part in parts:
                if part.isdigit():
                    result = result[int(part)]
                else:
                    result = result[part]
            return result
        except Exception as e:
            logger.error(f"JSON query error: {e}")
            return {"error": str(e)}


def read_json(file_path: str) -> Union[Dict, List]:
    """Read JSON file."""
    return JSONTool().read(file_path=file_path)
