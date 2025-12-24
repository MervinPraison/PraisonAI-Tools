"""BigQuery Tool for PraisonAI Agents.

Google BigQuery operations.

Usage:
    from praisonai_tools import BigQueryTool
    
    bq = BigQueryTool()
    results = bq.query("SELECT * FROM dataset.table LIMIT 10")

Environment Variables:
    GOOGLE_APPLICATION_CREDENTIALS: Path to service account JSON
"""

import os
import logging
from typing import Any, Dict, List, Optional, Union

from praisonai_tools.tools.base import BaseTool

logger = logging.getLogger(__name__)


class BigQueryTool(BaseTool):
    """Tool for BigQuery operations."""
    
    name = "bigquery"
    description = "Google BigQuery SQL operations."
    
    def __init__(self, project_id: Optional[str] = None):
        self.project_id = project_id or os.getenv("GOOGLE_CLOUD_PROJECT")
        self._client = None
        super().__init__()
    
    @property
    def client(self):
        if self._client is None:
            try:
                from google.cloud import bigquery
            except ImportError:
                raise ImportError("google-cloud-bigquery not installed")
            self._client = bigquery.Client(project=self.project_id)
        return self._client
    
    def run(
        self,
        action: str = "query",
        sql: Optional[str] = None,
        **kwargs
    ) -> Union[str, Dict[str, Any], List[Dict[str, Any]]]:
        action = action.lower().replace("-", "_")
        
        if action == "query":
            return self.query(sql=sql)
        elif action == "list_datasets":
            return self.list_datasets()
        elif action == "list_tables":
            return self.list_tables(dataset=kwargs.get("dataset"))
        else:
            return {"error": f"Unknown action: {action}"}
    
    def query(self, sql: str) -> List[Dict[str, Any]]:
        """Execute SQL query."""
        if not sql:
            return [{"error": "sql is required"}]
        
        try:
            query_job = self.client.query(sql)
            results = query_job.result()
            return [dict(row) for row in results]
        except Exception as e:
            logger.error(f"BigQuery query error: {e}")
            return [{"error": str(e)}]
    
    def list_datasets(self) -> List[Dict[str, Any]]:
        """List datasets."""
        try:
            datasets = self.client.list_datasets()
            return [{"dataset_id": d.dataset_id} for d in datasets]
        except Exception as e:
            logger.error(f"BigQuery list_datasets error: {e}")
            return [{"error": str(e)}]
    
    def list_tables(self, dataset: str) -> List[Dict[str, Any]]:
        """List tables in dataset."""
        if not dataset:
            return [{"error": "dataset is required"}]
        
        try:
            tables = self.client.list_tables(dataset)
            return [{"table_id": t.table_id, "table_type": t.table_type} for t in tables]
        except Exception as e:
            logger.error(f"BigQuery list_tables error: {e}")
            return [{"error": str(e)}]


def bigquery_query(sql: str) -> List[Dict[str, Any]]:
    """Query BigQuery."""
    return BigQueryTool().query(sql=sql)
