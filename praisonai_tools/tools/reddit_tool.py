"""Reddit Tool for PraisonAI Agents.

Search Reddit, get posts, and interact with subreddits.

Usage:
    from praisonai_tools import RedditTool
    
    reddit = RedditTool()  # Uses REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET env vars
    
    # Search posts
    posts = reddit.search("python programming", subreddit="learnpython")
    
    # Get hot posts
    hot = reddit.get_hot(subreddit="technology", limit=10)

Environment Variables:
    REDDIT_CLIENT_ID: Reddit API client ID
    REDDIT_CLIENT_SECRET: Reddit API client secret
    REDDIT_USER_AGENT: User agent string (optional)
    REDDIT_USERNAME: Reddit username (required for write actions)
    REDDIT_PASSWORD: Reddit password (required for write actions)
    REDDIT_ALLOW_WRITE: Set to "1" to enable write actions (post/comment)

Write actions (submit_post, post_comment) are disabled by default to reduce
spam/abuse surface. They are only permitted when ``REDDIT_ALLOW_WRITE=1`` (or
``allow_write=True``) and Reddit account credentials are configured. You are
responsible for complying with Reddit's API terms when enabling writes.

Reddit rate-limits misconfigured clients aggressively. Use a descriptive
User-Agent referencing your app id, e.g. ``script:my-app:v1.0 (by /u/you)``.
"""

import os
import logging
from typing import Any, Dict, List, Optional, Union

from praisonai_tools.tools.base import BaseTool

logger = logging.getLogger(__name__)


class RedditTool(BaseTool):
    """Tool for interacting with Reddit."""
    
    name = "reddit"
    description = "Search Reddit, get posts from subreddits, and read comments."
    
    def __init__(
        self,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        user_agent: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        allow_write: Optional[bool] = None,
    ):
        """Initialize RedditTool.
        
        Args:
            client_id: Reddit API client ID
            client_secret: Reddit API client secret
            user_agent: User agent string
            username: Reddit username (required for write actions)
            password: Reddit password (required for write actions)
            allow_write: Enable write actions. Defaults to the
                ``REDDIT_ALLOW_WRITE`` env var ("1"/"true" enables).
        """
        self.client_id = client_id or os.getenv("REDDIT_CLIENT_ID")
        self.client_secret = client_secret or os.getenv("REDDIT_CLIENT_SECRET")
        self.user_agent = user_agent or os.getenv("REDDIT_USER_AGENT") or self._default_user_agent()
        self.username = username or os.getenv("REDDIT_USERNAME")
        self.password = password or os.getenv("REDDIT_PASSWORD")
        if allow_write is None:
            allow_write = os.getenv("REDDIT_ALLOW_WRITE", "").lower() in ("1", "true", "yes")
        self.allow_write = allow_write
        self._reddit = None
        super().__init__()
    
    def _default_user_agent(self) -> str:
        """Build a compliant User-Agent referencing the app id.
        
        Reddit recommends ``<platform>:<app id>:<version> (by /u/<user>)``.
        """
        app_id = self.client_id or "unknown"
        return f"script:praisonai-{app_id}:1.0 (by PraisonAI)"
    
    @property
    def reddit(self):
        """Lazy-load Reddit client."""
        if self._reddit is None:
            try:
                import praw
            except ImportError:
                raise ImportError("praw not installed. Install with: pip install praw")
            
            if not self.client_id or not self.client_secret:
                raise ValueError("REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET required")
            
            kwargs = {
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "user_agent": self.user_agent,
            }
            if self.username and self.password:
                kwargs["username"] = self.username
                kwargs["password"] = self.password
            
            self._reddit = praw.Reddit(**kwargs)
        return self._reddit
    
    def _check_write_allowed(self) -> Optional[Dict[str, Any]]:
        """Return an error dict if write actions are not permitted, else None."""
        if not self.allow_write:
            return {
                "error": "Write actions disabled. Set REDDIT_ALLOW_WRITE=1 to enable "
                "posting/commenting.",
            }
        if not self.username or not self.password:
            return {
                "error": "REDDIT_USERNAME and REDDIT_PASSWORD required for write actions.",
            }
        return None
    
    def run(
        self,
        action: str = "search",
        query: Optional[str] = None,
        subreddit: Optional[str] = None,
        post_id: Optional[str] = None,
        limit: int = 10,
        **kwargs
    ) -> Union[str, Dict[str, Any], List[Dict[str, Any]]]:
        """Execute Reddit action."""
        action = action.lower().replace("-", "_")
        
        if action == "search":
            return self.search(query=query, subreddit=subreddit, limit=limit)
        elif action == "hot":
            return self.get_hot(subreddit=subreddit, limit=limit)
        elif action == "top":
            return self.get_top(subreddit=subreddit, limit=limit, **kwargs)
        elif action == "new":
            return self.get_new(subreddit=subreddit, limit=limit)
        elif action == "get_post":
            return self.get_post(post_id=post_id)
        elif action == "get_comments":
            return self.get_comments(post_id=post_id, limit=limit)
        elif action == "subreddit_info":
            return self.get_subreddit_info(subreddit=subreddit)
        elif action == "post_comment":
            return self.post_comment(post_id=post_id, body=kwargs.get("body"))
        elif action == "submit_post":
            return self.submit_post(
                subreddit=subreddit,
                title=kwargs.get("title"),
                body=kwargs.get("body"),
                url=kwargs.get("url"),
            )
        else:
            return {"error": f"Unknown action: {action}"}
    
    def search(
        self,
        query: str,
        subreddit: Optional[str] = None,
        sort: str = "relevance",
        time_filter: str = "all",
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Search Reddit posts.
        
        Args:
            query: Search query
            subreddit: Limit to specific subreddit
            sort: "relevance", "hot", "top", "new", "comments"
            time_filter: "all", "day", "week", "month", "year"
            limit: Max results
            
        Returns:
            List of posts
        """
        if not query:
            return [{"error": "query is required"}]
        
        try:
            if subreddit:
                sub = self.reddit.subreddit(subreddit)
                results = sub.search(query, sort=sort, time_filter=time_filter, limit=limit)
            else:
                results = self.reddit.subreddit("all").search(query, sort=sort, time_filter=time_filter, limit=limit)
            
            posts = []
            for post in results:
                posts.append(self._format_post(post))
            
            return posts
        except Exception as e:
            logger.error(f"Reddit search error: {e}")
            return [{"error": str(e)}]
    
    def get_hot(self, subreddit: str = "all", limit: int = 10) -> List[Dict[str, Any]]:
        """Get hot posts from a subreddit.
        
        Args:
            subreddit: Subreddit name
            limit: Max posts
            
        Returns:
            List of posts
        """
        try:
            sub = self.reddit.subreddit(subreddit)
            posts = []
            for post in sub.hot(limit=limit):
                posts.append(self._format_post(post))
            return posts
        except Exception as e:
            logger.error(f"Reddit get_hot error: {e}")
            return [{"error": str(e)}]
    
    def get_top(
        self,
        subreddit: str = "all",
        time_filter: str = "day",
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Get top posts from a subreddit.
        
        Args:
            subreddit: Subreddit name
            time_filter: "hour", "day", "week", "month", "year", "all"
            limit: Max posts
            
        Returns:
            List of posts
        """
        try:
            sub = self.reddit.subreddit(subreddit)
            posts = []
            for post in sub.top(time_filter=time_filter, limit=limit):
                posts.append(self._format_post(post))
            return posts
        except Exception as e:
            logger.error(f"Reddit get_top error: {e}")
            return [{"error": str(e)}]
    
    def get_new(self, subreddit: str = "all", limit: int = 10) -> List[Dict[str, Any]]:
        """Get new posts from a subreddit.
        
        Args:
            subreddit: Subreddit name
            limit: Max posts
            
        Returns:
            List of posts
        """
        try:
            sub = self.reddit.subreddit(subreddit)
            posts = []
            for post in sub.new(limit=limit):
                posts.append(self._format_post(post))
            return posts
        except Exception as e:
            logger.error(f"Reddit get_new error: {e}")
            return [{"error": str(e)}]
    
    def get_post(self, post_id: str) -> Dict[str, Any]:
        """Get a specific post by ID.
        
        Args:
            post_id: Reddit post ID
            
        Returns:
            Post details
        """
        if not post_id:
            return {"error": "post_id is required"}
        
        try:
            post = self.reddit.submission(id=post_id)
            return self._format_post(post, include_body=True)
        except Exception as e:
            logger.error(f"Reddit get_post error: {e}")
            return {"error": str(e)}
    
    def get_comments(self, post_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Get comments from a post.
        
        Args:
            post_id: Reddit post ID
            limit: Max comments
            
        Returns:
            List of comments
        """
        if not post_id:
            return [{"error": "post_id is required"}]
        
        try:
            post = self.reddit.submission(id=post_id)
            post.comments.replace_more(limit=0)
            
            comments = []
            for comment in post.comments[:limit]:
                comments.append({
                    "id": comment.id,
                    "author": str(comment.author) if comment.author else "[deleted]",
                    "body": comment.body[:500],
                    "score": comment.score,
                    "created_utc": comment.created_utc,
                })
            
            return comments
        except Exception as e:
            logger.error(f"Reddit get_comments error: {e}")
            return [{"error": str(e)}]
    
    def get_subreddit_info(self, subreddit: str) -> Dict[str, Any]:
        """Get subreddit information.
        
        Args:
            subreddit: Subreddit name
            
        Returns:
            Subreddit info
        """
        if not subreddit:
            return {"error": "subreddit is required"}
        
        try:
            sub = self.reddit.subreddit(subreddit)
            return {
                "name": sub.display_name,
                "title": sub.title,
                "description": sub.public_description[:500] if sub.public_description else "",
                "subscribers": sub.subscribers,
                "created_utc": sub.created_utc,
                "over18": sub.over18,
                "url": f"https://reddit.com{sub.url}",
            }
        except Exception as e:
            logger.error(f"Reddit get_subreddit_info error: {e}")
            return {"error": str(e)}
    
    def post_comment(self, post_id: str, body: str) -> Dict[str, Any]:
        """Reply with a comment to a post (write action).
        
        Gated behind ``REDDIT_ALLOW_WRITE=1`` and account credentials.
        
        Args:
            post_id: Reddit post ID to comment on
            body: Comment text
            
        Returns:
            Result with the new comment id, or an error dict
        """
        denied = self._check_write_allowed()
        if denied:
            return denied
        if not post_id:
            return {"error": "post_id is required"}
        if not body:
            return {"error": "body is required"}
        
        try:
            submission = self.reddit.submission(id=post_id)
            comment = submission.reply(body)
            return {
                "success": True,
                "id": comment.id,
                "permalink": f"https://reddit.com{comment.permalink}",
            }
        except Exception as e:
            logger.error(f"Reddit post_comment error: {e}")
            return {"error": str(e)}
    
    def submit_post(
        self,
        subreddit: str,
        title: str,
        body: Optional[str] = None,
        url: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Submit a new post to a subreddit (write action).
        
        Gated behind ``REDDIT_ALLOW_WRITE=1`` and account credentials.
        
        Args:
            subreddit: Target subreddit name
            title: Post title
            body: Self-post text (mutually exclusive with url)
            url: Link URL (mutually exclusive with body)
            
        Returns:
            Result with the new post id, or an error dict
        """
        denied = self._check_write_allowed()
        if denied:
            return denied
        if not subreddit:
            return {"error": "subreddit is required"}
        if not title:
            return {"error": "title is required"}
        if url and body:
            return {"error": "provide either body or url, not both"}
        
        try:
            sub = self.reddit.subreddit(subreddit)
            if url:
                submission = sub.submit(title, url=url)
            else:
                submission = sub.submit(title, selftext=body or "")
            return {
                "success": True,
                "id": submission.id,
                "permalink": f"https://reddit.com{submission.permalink}",
            }
        except Exception as e:
            logger.error(f"Reddit submit_post error: {e}")
            return {"error": str(e)}
    
    def _format_post(self, post, include_body: bool = False) -> Dict[str, Any]:
        """Format a Reddit post."""
        result = {
            "id": post.id,
            "title": post.title,
            "author": str(post.author) if post.author else "[deleted]",
            "subreddit": post.subreddit.display_name,
            "score": post.score,
            "upvote_ratio": post.upvote_ratio,
            "num_comments": post.num_comments,
            "url": post.url,
            "permalink": f"https://reddit.com{post.permalink}",
            "created_utc": post.created_utc,
            "is_self": post.is_self,
        }
        
        if include_body and post.is_self:
            result["body"] = post.selftext[:2000] if post.selftext else ""
        
        return result


def search_reddit(query: str, subreddit: Optional[str] = None, limit: int = 10) -> List[Dict[str, Any]]:
    """Search Reddit posts."""
    return RedditTool().search(query=query, subreddit=subreddit, limit=limit)


def get_reddit_hot(subreddit: str = "all", limit: int = 10) -> List[Dict[str, Any]]:
    """Get hot Reddit posts."""
    return RedditTool().get_hot(subreddit=subreddit, limit=limit)
