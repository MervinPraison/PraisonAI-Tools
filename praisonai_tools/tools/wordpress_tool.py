"""WordPress Tool for PraisonAI Agents.

WordPress content management with duplicate detection.

Usage:
    from praisonai_tools import WordPressTool
    
    wp = WordPressTool()
    
    # Check for duplicate content
    result = wp.check_duplicate(title="My Post", content="...")
    
    # Create a post
    result = wp.create_post(title="My Post", content="...", status="draft")

Dependencies:
    pip install praisonai-tools[wordpress]
    # Requires: praisonaiwp
"""

import logging
import os
from typing import Any, Dict, List, Optional

from praisonai_tools.tools.base import BaseTool

logger = logging.getLogger(__name__)


class WordPressTool(BaseTool):
    """Tool for WordPress content management with semantic duplicate detection."""
    
    name = "wordpress"
    description = "Manage WordPress posts with duplicate detection"
    
    def __init__(
        self,
        threshold: float = 0.7,
        verbose: bool = False,
    ):
        """
        Initialize WordPress tool.
        
        Args:
            threshold: Similarity threshold for duplicate detection (0.0-1.0)
            verbose: Enable verbose logging
        """
        self.threshold = threshold
        self.verbose = verbose
        self._wp_client = None
        self._ssh_manager = None
        self._detector = None
        super().__init__()
    
    def _lazy_import(self):
        """Lazy import praisonaiwp to avoid import-time overhead."""
        try:
            from praisonaiwp.core.config import Config
            from praisonaiwp.core.ssh_manager import SSHManager
            from praisonaiwp.core.wp_client import WPClient
            from praisonaiwp.ai.duplicate_detector import DuplicateDetector
            return Config, SSHManager, WPClient, DuplicateDetector
        except ImportError:
            raise ImportError(
                "praisonaiwp not installed. Install with: pip install praisonaiwp[ai]"
            )
    
    def _get_wp_client(self):
        """Lazy initialization of WordPress client via SSH."""
        if self._wp_client is not None:
            return self._wp_client
        
        Config, SSHManager, WPClient, _ = self._lazy_import()
        
        config = Config()
        server_config = config.get_server()
        
        if self.verbose:
            logger.info(f"Connecting to WordPress at {server_config['hostname']}")
        
        self._ssh_manager = SSHManager(
            server_config['hostname'],
            server_config['username'],
            server_config['key_file'],
            server_config.get('port', 22)
        )
        self._ssh_manager.__enter__()
        
        self._wp_client = WPClient(
            self._ssh_manager,
            server_config['wp_path'],
            server_config.get('php_bin', 'php'),
            server_config.get('wp_cli', '/usr/local/bin/wp'),
            verify_installation=False
        )
        
        return self._wp_client
    
    def _get_detector(self):
        """Get singleton DuplicateDetector instance."""
        if self._detector is not None:
            return self._detector
        
        _, _, _, DuplicateDetector = self._lazy_import()
        
        wp = self._get_wp_client()
        self._detector = DuplicateDetector(
            wp_client=wp,
            threshold=self.threshold,
            duplicate_threshold=self.threshold,
            verbose=1 if self.verbose else 0
        )
        
        # Ensure index is in sync
        self._ensure_index_sync(wp, self._detector)
        
        return self._detector
    
    def _ensure_index_sync(self, wp_client, detector) -> int:
        """Ensure embeddings index is in sync with WordPress posts."""
        all_posts = wp_client.list_posts(
            post_type='post', 
            post_status='publish', 
            per_page=2000
        )
        wp_count = len(all_posts)
        embeddings_count = detector.cache.count() if detector.cache else 0
        
        if embeddings_count < wp_count:
            indexed = detector.index_posts()
            return indexed
        
        return embeddings_count
    
    def run(
        self,
        action: str = "check_duplicate",
        title: Optional[str] = None,
        content: Optional[str] = None,
        status: str = "draft",
        category: str = "News",
        author: str = "praison",
        items: Optional[List[str]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Run WordPress tool action."""
        action = action.lower().replace("-", "_")
        
        if action == "check_duplicate":
            return self.check_duplicate(title=title or "", content=content or "")
        elif action == "check_duplicates_batch":
            return self.check_duplicates_batch(items=items or [])
        elif action == "create_post":
            return self.create_post(
                title=title or "",
                content=content or "",
                status=status,
                category=category,
                author=author
            )
        else:
            return {"error": f"Unknown action: {action}"}
    
    def check_duplicate(self, title: str, content: str = "") -> Dict[str, Any]:
        """
        Check for duplicate content in WordPress using semantic similarity.
        
        Args:
            title: Post title to check
            content: Post content to check
            
        Returns:
            Dict with has_duplicates, status, matches, recommendation
        """
        try:
            detector = self._get_detector()
            result = detector.check_duplicate(content=content, title=title)
            
            status = "DUPLICATE" if result.has_duplicates else "UNIQUE"
            matches = [
                {
                    "post_id": m.post_id,
                    "title": m.title,
                    "similarity": round(m.similarity_score, 3),
                    "status": m.status
                }
                for m in result.matches
            ]
            
            recommendation = ""
            if result.has_duplicates:
                top = result.matches[0]
                recommendation = f"Similar to existing post '{top.title}' (ID: {top.post_id}). Consider updating instead."
            else:
                recommendation = "Content appears unique. Safe to publish."
            
            return {
                "has_duplicates": result.has_duplicates,
                "status": status,
                "matches": matches,
                "total_checked": result.total_posts_checked,
                "recommendation": recommendation
            }
            
        except ImportError as e:
            return {"error": str(e), "status": "ERROR", "has_duplicates": False}
        except Exception as e:
            logger.error(f"Duplicate check failed: {e}")
            return {"error": str(e), "status": "ERROR", "has_duplicates": False}
    
    def check_duplicates_batch(self, items: List[str]) -> Dict[str, Any]:
        """
        Check multiple items for duplicates.
        
        Args:
            items: List of titles/content to check
            
        Returns:
            Dict with has_duplicates, status, matches
        """
        try:
            detector = self._get_detector()
            result = detector.check_duplicates_batch(items=items, any_match=True)
            
            status = "DUPLICATE" if result.has_duplicates else "UNIQUE"
            matches = [
                {
                    "post_id": m.post_id,
                    "title": m.title,
                    "similarity": round(m.similarity_score, 3),
                    "status": m.status
                }
                for m in result.matches
            ]
            
            if result.has_duplicates:
                top = result.matches[0]
                recommendation = f"Similar to existing post '{top.title}' (ID: {top.post_id})."
            else:
                recommendation = "All content appears unique. Safe to publish."
            
            return {
                "has_duplicates": result.has_duplicates,
                "status": status,
                "matches": matches,
                "total_checked": result.total_posts_checked,
                "items_checked": len(items),
                "recommendation": recommendation
            }
            
        except ImportError as e:
            return {"error": str(e), "status": "ERROR", "has_duplicates": False}
        except Exception as e:
            logger.error(f"Batch duplicate check failed: {e}")
            return {"error": str(e), "status": "ERROR", "has_duplicates": False}
    
    def create_post(
        self,
        title: str,
        content: str,
        status: str = "draft",
        category: str = "News",
        author: str = "praison",
        min_word_count: int = 100,
        check_duplicates: bool = True,
    ) -> Dict[str, Any]:
        """
        Create WordPress post with content validation.
        
        Args:
            title: Post title
            content: Post content (markdown or HTML)
            status: Post status (draft, publish)
            category: Category name
            author: Author username
            min_word_count: Minimum word count (default 100)
            check_duplicates: Whether to check for duplicates first
            
        Returns:
            Dict with post_id, status, success
        """
        import re
        import subprocess
        
        # Content word count check
        word_count = len(content.split()) if content else 0
        if word_count < min_word_count:
            return {
                "post_id": None,
                "status": "rejected",
                "message": f"REJECTED: Content too short ({word_count} words, minimum {min_word_count})",
                "success": False,
                "blocked": True
            }
        
        # Session deduplication
        if not hasattr(self, '_created_titles'):
            self._created_titles = set()
        
        normalized_title = title.strip().lower()
        if normalized_title in self._created_titles:
            return {
                "post_id": None,
                "status": "skipped",
                "message": "SKIPPED: Already created in this session",
                "success": True,
                "duplicate": True
            }
        
        # Optional duplicate check
        if check_duplicates:
            try:
                dup_result = self.check_duplicate(title=title, content=content[:500] if content else "")
                if dup_result.get("has_duplicates"):
                    top_match = dup_result.get("matches", [{}])[0]
                    return {
                        "post_id": None,
                        "status": "duplicate",
                        "message": f"BLOCKED: Similar to '{top_match.get('title')}'",
                        "success": False,
                        "duplicate": True,
                        "similar_post": top_match
                    }
            except Exception as e:
                logger.warning(f"Duplicate check failed, proceeding: {e}")
        
        # Add to session
        self._created_titles.add(normalized_title)
        
        try:
            # Convert markdown to HTML
            try:
                import markdown
                html_content = markdown.markdown(
                    content,
                    extensions=['tables', 'fenced_code', 'nl2br']
                )
            except ImportError:
                html_content = content
                html_content = re.sub(r'^#### (.+)$', r'<h4>\1</h4>', html_content, flags=re.MULTILINE)
                html_content = re.sub(r'^### (.+)$', r'<h3>\1</h3>', html_content, flags=re.MULTILINE)
                html_content = re.sub(r'^## (.+)$', r'<h2>\1</h2>', html_content, flags=re.MULTILINE)
                html_content = re.sub(r'^# (.+)$', r'<h1>\1</h1>', html_content, flags=re.MULTILINE)
                html_content = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', html_content)
            
            # Pass through Gutenberg blocks unchanged
            if '<!-- wp:' in content:
                html_content = content
            
            cmd = [
                "praisonaiwp", "create", title,
                "--content", html_content,
                "--status", status,
                "--category", category,
                "--author", author
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            output = result.stdout + result.stderr
            
            match = re.search(r'post[:\s]+(?:ID[:\s]*)?(\d+)', output, re.IGNORECASE)
            
            if match:
                post_id = int(match.group(1))
                return {
                    "post_id": post_id,
                    "status": status,
                    "category": category,
                    "author": author,
                    "message": f"Created {status} post with ID: {post_id}",
                    "success": True
                }
            elif result.returncode == 0:
                return {
                    "post_id": None,
                    "status": status,
                    "message": "Post created successfully",
                    "output": output[:500],
                    "success": True
                }
            else:
                return {"error": output[:500], "success": False}
                
        except subprocess.TimeoutExpired:
            return {"error": "Command timed out after 120s", "success": False}
        except Exception as e:
            logger.error(f"Failed to create post: {e}")
            return {"error": str(e), "success": False}
    
    def cleanup(self):
        """Close SSH connection when done."""
        if self._ssh_manager:
            try:
                self._ssh_manager.__exit__(None, None, None)
            except:
                pass
        self._ssh_manager = None
        self._wp_client = None
        self._detector = None


# Convenience functions
def check_wp_duplicate(title: str, content: str = "") -> Dict[str, Any]:
    """Check for duplicate WordPress content."""
    return WordPressTool().check_duplicate(title=title, content=content)


def create_wp_post(
    title: str,
    content: str,
    status: str = "draft",
    category: str = "News",
    author: str = "praison"
) -> Dict[str, Any]:
    """Create a WordPress post."""
    return WordPressTool().create_post(
        title=title,
        content=content,
        status=status,
        category=category,
        author=author
    )
