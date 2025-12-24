"""Google Cloud Storage Tool for PraisonAI Agents.

GCS bucket and object operations.

Usage:
    from praisonai_tools import GCSTool
    
    gcs = GCSTool()
    files = gcs.list_objects(bucket="my-bucket")

Environment Variables:
    GOOGLE_APPLICATION_CREDENTIALS: Path to service account JSON
"""

import os
import logging
from typing import Any, Dict, List, Optional, Union

from praisonai_tools.tools.base import BaseTool

logger = logging.getLogger(__name__)


class GCSTool(BaseTool):
    """Tool for Google Cloud Storage operations."""
    
    name = "gcs"
    description = "Google Cloud Storage bucket and object operations."
    
    def __init__(self, project_id: Optional[str] = None):
        self.project_id = project_id or os.getenv("GOOGLE_CLOUD_PROJECT")
        self._client = None
        super().__init__()
    
    @property
    def client(self):
        if self._client is None:
            try:
                from google.cloud import storage
            except ImportError:
                raise ImportError("google-cloud-storage not installed")
            self._client = storage.Client(project=self.project_id)
        return self._client
    
    def run(
        self,
        action: str = "list_objects",
        bucket: Optional[str] = None,
        **kwargs
    ) -> Union[str, Dict[str, Any], List[Dict[str, Any]]]:
        action = action.lower().replace("-", "_")
        
        if action == "list_buckets":
            return self.list_buckets()
        elif action == "list_objects":
            return self.list_objects(bucket=bucket, **kwargs)
        elif action == "upload":
            return self.upload(bucket=bucket, **kwargs)
        elif action == "download":
            return self.download(bucket=bucket, **kwargs)
        elif action == "delete":
            return self.delete(bucket=bucket, blob_name=kwargs.get("blob_name"))
        else:
            return {"error": f"Unknown action: {action}"}
    
    def list_buckets(self) -> List[Dict[str, Any]]:
        """List buckets."""
        try:
            buckets = self.client.list_buckets()
            return [{"name": b.name, "created": str(b.time_created)} for b in buckets]
        except Exception as e:
            logger.error(f"GCS list_buckets error: {e}")
            return [{"error": str(e)}]
    
    def list_objects(self, bucket: str, prefix: str = "", max_results: int = 100) -> List[Dict[str, Any]]:
        """List objects in bucket."""
        if not bucket:
            return [{"error": "bucket is required"}]
        
        try:
            bucket_obj = self.client.bucket(bucket)
            blobs = bucket_obj.list_blobs(prefix=prefix, max_results=max_results)
            return [{"name": b.name, "size": b.size, "updated": str(b.updated)} for b in blobs]
        except Exception as e:
            logger.error(f"GCS list_objects error: {e}")
            return [{"error": str(e)}]
    
    def upload(self, bucket: str, blob_name: str, content: str) -> Dict[str, Any]:
        """Upload content to bucket."""
        if not bucket or not blob_name or not content:
            return {"error": "bucket, blob_name, and content are required"}
        
        try:
            bucket_obj = self.client.bucket(bucket)
            blob = bucket_obj.blob(blob_name)
            blob.upload_from_string(content)
            return {"success": True, "url": f"gs://{bucket}/{blob_name}"}
        except Exception as e:
            logger.error(f"GCS upload error: {e}")
            return {"error": str(e)}
    
    def download(self, bucket: str, blob_name: str) -> Dict[str, Any]:
        """Download object content."""
        if not bucket or not blob_name:
            return {"error": "bucket and blob_name are required"}
        
        try:
            bucket_obj = self.client.bucket(bucket)
            blob = bucket_obj.blob(blob_name)
            content = blob.download_as_text()
            return {"content": content}
        except Exception as e:
            logger.error(f"GCS download error: {e}")
            return {"error": str(e)}
    
    def delete(self, bucket: str, blob_name: str) -> Dict[str, Any]:
        """Delete object."""
        if not bucket or not blob_name:
            return {"error": "bucket and blob_name are required"}
        
        try:
            bucket_obj = self.client.bucket(bucket)
            blob = bucket_obj.blob(blob_name)
            blob.delete()
            return {"success": True}
        except Exception as e:
            logger.error(f"GCS delete error: {e}")
            return {"error": str(e)}


def gcs_list_objects(bucket: str, prefix: str = "") -> List[Dict[str, Any]]:
    """List GCS objects."""
    return GCSTool().list_objects(bucket=bucket, prefix=prefix)
