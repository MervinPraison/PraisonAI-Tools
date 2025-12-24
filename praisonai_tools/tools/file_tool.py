"""File Tool for PraisonAI Agents.

Read, write, and manage files.

Usage:
    from praisonai_tools import FileTool
    
    file = FileTool()
    content = file.read("/path/to/file.txt")
    file.write("/path/to/file.txt", "Hello World")
"""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from praisonai_tools.tools.base import BaseTool

logger = logging.getLogger(__name__)


class FileTool(BaseTool):
    """Tool for file operations."""
    
    name = "file"
    description = "Read, write, and manage files."
    
    def __init__(self, base_dir: Optional[str] = None):
        self.base_dir = Path(base_dir) if base_dir else None
        super().__init__()
    
    def _resolve_path(self, path: str) -> Path:
        """Resolve path relative to base_dir if set."""
        p = Path(path)
        if self.base_dir and not p.is_absolute():
            return self.base_dir / p
        return p
    
    def run(
        self,
        action: str = "read",
        path: Optional[str] = None,
        content: Optional[str] = None,
        **kwargs
    ) -> Union[str, Dict[str, Any], List[Dict[str, Any]]]:
        action = action.lower().replace("-", "_")
        
        if action == "read":
            return self.read(path=path)
        elif action == "write":
            return self.write(path=path, content=content)
        elif action == "append":
            return self.append(path=path, content=content)
        elif action == "delete":
            return self.delete(path=path)
        elif action == "exists":
            return self.exists(path=path)
        elif action == "list_dir":
            return self.list_dir(path=path)
        elif action == "mkdir":
            return self.mkdir(path=path)
        elif action == "copy":
            return self.copy(src=path, dst=kwargs.get("dst"))
        elif action == "move":
            return self.move(src=path, dst=kwargs.get("dst"))
        else:
            return {"error": f"Unknown action: {action}"}
    
    def read(self, path: str) -> Dict[str, Any]:
        """Read file content."""
        if not path:
            return {"error": "path is required"}
        
        try:
            p = self._resolve_path(path)
            if not p.exists():
                return {"error": f"File not found: {path}"}
            
            content = p.read_text()
            return {"path": str(p), "content": content, "size": len(content)}
        except Exception as e:
            logger.error(f"File read error: {e}")
            return {"error": str(e)}
    
    def write(self, path: str, content: str) -> Dict[str, Any]:
        """Write content to file."""
        if not path:
            return {"error": "path is required"}
        if content is None:
            return {"error": "content is required"}
        
        try:
            p = self._resolve_path(path)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content)
            return {"success": True, "path": str(p), "size": len(content)}
        except Exception as e:
            logger.error(f"File write error: {e}")
            return {"error": str(e)}
    
    def append(self, path: str, content: str) -> Dict[str, Any]:
        """Append content to file."""
        if not path:
            return {"error": "path is required"}
        if content is None:
            return {"error": "content is required"}
        
        try:
            p = self._resolve_path(path)
            p.parent.mkdir(parents=True, exist_ok=True)
            with open(p, "a") as f:
                f.write(content)
            return {"success": True, "path": str(p)}
        except Exception as e:
            logger.error(f"File append error: {e}")
            return {"error": str(e)}
    
    def delete(self, path: str) -> Dict[str, Any]:
        """Delete file."""
        if not path:
            return {"error": "path is required"}
        
        try:
            p = self._resolve_path(path)
            if not p.exists():
                return {"error": f"File not found: {path}"}
            
            if p.is_dir():
                import shutil
                shutil.rmtree(p)
            else:
                p.unlink()
            return {"success": True, "path": str(p)}
        except Exception as e:
            logger.error(f"File delete error: {e}")
            return {"error": str(e)}
    
    def exists(self, path: str) -> Dict[str, Any]:
        """Check if file exists."""
        if not path:
            return {"error": "path is required"}
        
        p = self._resolve_path(path)
        return {
            "path": str(p),
            "exists": p.exists(),
            "is_file": p.is_file() if p.exists() else False,
            "is_dir": p.is_dir() if p.exists() else False,
        }
    
    def list_dir(self, path: str = ".") -> List[Dict[str, Any]]:
        """List directory contents."""
        try:
            p = self._resolve_path(path or ".")
            if not p.exists():
                return [{"error": f"Directory not found: {path}"}]
            if not p.is_dir():
                return [{"error": f"Not a directory: {path}"}]
            
            items = []
            for item in p.iterdir():
                items.append({
                    "name": item.name,
                    "type": "dir" if item.is_dir() else "file",
                    "size": item.stat().st_size if item.is_file() else None,
                })
            return items
        except Exception as e:
            logger.error(f"File list_dir error: {e}")
            return [{"error": str(e)}]
    
    def mkdir(self, path: str) -> Dict[str, Any]:
        """Create directory."""
        if not path:
            return {"error": "path is required"}
        
        try:
            p = self._resolve_path(path)
            p.mkdir(parents=True, exist_ok=True)
            return {"success": True, "path": str(p)}
        except Exception as e:
            logger.error(f"File mkdir error: {e}")
            return {"error": str(e)}
    
    def copy(self, src: str, dst: str) -> Dict[str, Any]:
        """Copy file."""
        if not src or not dst:
            return {"error": "src and dst are required"}
        
        try:
            import shutil
            src_p = self._resolve_path(src)
            dst_p = self._resolve_path(dst)
            
            if src_p.is_dir():
                shutil.copytree(src_p, dst_p)
            else:
                shutil.copy2(src_p, dst_p)
            return {"success": True, "src": str(src_p), "dst": str(dst_p)}
        except Exception as e:
            logger.error(f"File copy error: {e}")
            return {"error": str(e)}
    
    def move(self, src: str, dst: str) -> Dict[str, Any]:
        """Move file."""
        if not src or not dst:
            return {"error": "src and dst are required"}
        
        try:
            import shutil
            src_p = self._resolve_path(src)
            dst_p = self._resolve_path(dst)
            shutil.move(src_p, dst_p)
            return {"success": True, "src": str(src_p), "dst": str(dst_p)}
        except Exception as e:
            logger.error(f"File move error: {e}")
            return {"error": str(e)}


def read_file(path: str) -> Dict[str, Any]:
    """Read file content."""
    return FileTool().read(path=path)


def write_file(path: str, content: str) -> Dict[str, Any]:
    """Write file content."""
    return FileTool().write(path=path, content=content)
