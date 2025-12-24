"""DynamoDB Tool for PraisonAI Agents.

AWS DynamoDB operations.

Usage:
    from praisonai_tools import DynamoDBTool
    
    dynamo = DynamoDBTool()
    items = dynamo.scan(table="users")

Environment Variables:
    AWS_ACCESS_KEY_ID: AWS access key
    AWS_SECRET_ACCESS_KEY: AWS secret key
    AWS_REGION: AWS region
"""

import os
import logging
from typing import Any, Dict, List, Optional, Union

from praisonai_tools.tools.base import BaseTool

logger = logging.getLogger(__name__)


class DynamoDBTool(BaseTool):
    """Tool for DynamoDB operations."""
    
    name = "dynamodb"
    description = "AWS DynamoDB database operations."
    
    def __init__(self, region: Optional[str] = None):
        self.region = region or os.getenv("AWS_REGION", "us-east-1")
        self._client = None
        super().__init__()
    
    @property
    def client(self):
        if self._client is None:
            try:
                import boto3
            except ImportError:
                raise ImportError("boto3 not installed. Install with: pip install boto3")
            self._client = boto3.client("dynamodb", region_name=self.region)
        return self._client
    
    def run(
        self,
        action: str = "scan",
        table: Optional[str] = None,
        **kwargs
    ) -> Union[str, Dict[str, Any], List[Dict[str, Any]]]:
        action = action.lower().replace("-", "_")
        
        if action == "scan":
            return self.scan(table=table, **kwargs)
        elif action == "get_item":
            return self.get_item(table=table, key=kwargs.get("key"))
        elif action == "put_item":
            return self.put_item(table=table, item=kwargs.get("item"))
        elif action == "delete_item":
            return self.delete_item(table=table, key=kwargs.get("key"))
        elif action == "query":
            return self.query(table=table, **kwargs)
        elif action == "list_tables":
            return self.list_tables()
        else:
            return {"error": f"Unknown action: {action}"}
    
    def scan(self, table: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Scan table."""
        if not table:
            return [{"error": "table is required"}]
        
        try:
            resp = self.client.scan(TableName=table, Limit=limit)
            return resp.get("Items", [])
        except Exception as e:
            logger.error(f"DynamoDB scan error: {e}")
            return [{"error": str(e)}]
    
    def get_item(self, table: str, key: Dict) -> Dict[str, Any]:
        """Get item by key."""
        if not table or not key:
            return {"error": "table and key are required"}
        
        try:
            resp = self.client.get_item(TableName=table, Key=key)
            return resp.get("Item", {})
        except Exception as e:
            logger.error(f"DynamoDB get_item error: {e}")
            return {"error": str(e)}
    
    def put_item(self, table: str, item: Dict) -> Dict[str, Any]:
        """Put item."""
        if not table or not item:
            return {"error": "table and item are required"}
        
        try:
            self.client.put_item(TableName=table, Item=item)
            return {"success": True}
        except Exception as e:
            logger.error(f"DynamoDB put_item error: {e}")
            return {"error": str(e)}
    
    def delete_item(self, table: str, key: Dict) -> Dict[str, Any]:
        """Delete item."""
        if not table or not key:
            return {"error": "table and key are required"}
        
        try:
            self.client.delete_item(TableName=table, Key=key)
            return {"success": True}
        except Exception as e:
            logger.error(f"DynamoDB delete_item error: {e}")
            return {"error": str(e)}
    
    def query(self, table: str, key_condition: str, expression_values: Dict) -> List[Dict[str, Any]]:
        """Query table."""
        if not table or not key_condition:
            return [{"error": "table and key_condition are required"}]
        
        try:
            resp = self.client.query(
                TableName=table,
                KeyConditionExpression=key_condition,
                ExpressionAttributeValues=expression_values,
            )
            return resp.get("Items", [])
        except Exception as e:
            logger.error(f"DynamoDB query error: {e}")
            return [{"error": str(e)}]
    
    def list_tables(self) -> List[Dict[str, Any]]:
        """List tables."""
        try:
            resp = self.client.list_tables()
            return [{"table_name": t} for t in resp.get("TableNames", [])]
        except Exception as e:
            logger.error(f"DynamoDB list_tables error: {e}")
            return [{"error": str(e)}]


def dynamodb_scan(table: str, limit: int = 100) -> List[Dict[str, Any]]:
    """Scan DynamoDB table."""
    return DynamoDBTool().scan(table=table, limit=limit)
