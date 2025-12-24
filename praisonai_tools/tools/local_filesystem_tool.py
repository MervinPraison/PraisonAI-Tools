"""Local FileSystem Tool for PraisonAI Agents.

Local file system operations with directory traversal.

Usage:
    from praisonai_tools import LocalFileSystemTool
    
    fs = LocalFileSystemTool()
    files = fs.list_directory("/path/to/dir")
"""

import os
import logging
from typing import Any, Dict, List, Optional, Union

from praisonai_tools.tools.base import BaseTool

logger = logging.getLogger(__name__)


class LocalFileSystemTool(BaseTool):
    """Tool for local file system operations."""
    
    name = "local_filesystem"
    description = "Local file system operations with directory traversal."
    
    def __init__(self, base_path: str = None):
        self.base_path = base_path or os.getcwd()
        super().__init__()
    
    def run(
        self,
        action: str = "list",
        path: Optional[str] = None,
        **kwargs
    ) -> Union[str, Dict[str, Any], List[Dict[str, Any]]]:
        action = action.lower().replace("-", "_")
        
        if action == "list":
            return self.list_directory(path=path)
        elif action == "read":
            return self.read_file(path=path)
        elif action == "write":
            return self.write_file(path=path, content=kwargs.get("content"))
        elif action == "exists":
            return self.exists(path=path)
        elif action == "mkdir":
            return self.mkdir(path=path)
        elif action == "delete":
            return self.delete(path=path)
        elif action == "tree":
            return self.tree(path=path, **kwargs)
        else:
            return {"error": f"Unknown action: {action}"}
    
    def _resolve_path(self, path: str) -> str:
        if os.path.isabs(path):
            return path
        return os.path.join(self.base_path, path)
    
    def list_directory(self, path: str = ".") -> List[Dict[str, Any]]:
        """List directory contents."""
        full_path = self._resolve_path(path or ".")
        
        try:
            items = []
            for name in os.listdir(full_path):
                item_path = os.path.join(full_path, name)
                stat = os.stat(item_path)
                items.append({
                    "name": name,
                    "type": "directory" if os.path.isdir(item_path) else "file",
                    "size": stat.st_size,
                    "modified": stat.st_mtime,
                })
            return items
        except Exception as e:
            logger.error(f"LocalFileSystem list error: {e}")
            return [{"error": str(e)}]
    
    def read_file(self, path: str) -> Dict[str, Any]:
        """Read file content."""
        if not path:
            return {"error": "path is required"}
        
        full_path = self._resolve_path(path)
        
        try:
            with open(full_path, "r", encoding="utf-8") as f:
                content = f.read()
            return {"path": path, "content": content}
        except Exception as e:
            logger.error(f"LocalFileSystem read error: {e}")
            return {"error": str(e)}
    
    def write_file(self, path: str, content: str) -> Dict[str, Any]:
        """Write file content."""
        if not path or content is None:
            return {"error": "path and content are required"}
        
        full_path = self._resolve_path(path)
        
        try:
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(content)
            return {"success": True, "path": path}
        except Exception as e:
            logger.error(f"LocalFileSystem write error: {e}")
            return {"error": str(e)}
    
    def exists(self, path: str) -> Dict[str, Any]:
        """Check if path exists."""
        if not path:
            return {"error": "path is required"}
        
        full_path = self._resolve_path(path)
        return {"exists": os.path.exists(full_path), "is_file": os.path.isfile(full_path), "is_dir": os.path.isdir(full_path)}
    
    def mkdir(self, path: str) -> Dict[str, Any]:
        """Create directory."""
        if not path:
            return {"error": "path is required"}
        
        full_path = self._resolve_path(path)
        
        try:
            os.makedirs(full_path, exist_ok=True)
            return {"success": True, "path": path}
        except Exception as e:
            logger.error(f"LocalFileSystem mkdir error: {e}")
            return {"error": str(e)}
    
    def delete(self, path: str) -> Dict[str, Any]:
        """Delete file or empty directory."""
        if not path:
            return {"error": "path is required"}
        
        full_path = self._resolve_path(path)
        
        try:
            if os.path.isfile(full_path):
                os.remove(full_path)
            elif os.path.isdir(full_path):
                os.rmdir(full_path)
            return {"success": True}
        except Exception as e:
            logger.error(f"LocalFileSystem delete error: {e}")
            return {"error": str(e)}
    
    def tree(self, path: str = ".", max_depth: int = 3) -> List[Dict[str, Any]]:
        """Get directory tree."""
        full_path = self._resolve_path(path or ".")
        
        def _walk(p, depth):
            if depth > max_depth:
                return []
            items = []
            try:
                for name in os.listdir(p):
                    item_path = os.path.join(p, name)
                    is_dir = os.path.isdir(item_path)
                    item = {"name": name, "type": "directory" if is_dir else "file"}
                    if is_dir:
                        item["children"] = _walk(item_path, depth + 1)
                    items.append(item)
            except PermissionError:
                pass
            return items
        
        return _walk(full_path, 1)


def list_local_directory(path: str = ".") -> List[Dict[str, Any]]:
    """List local directory."""
    return LocalFileSystemTool().list_directory(path=path)
