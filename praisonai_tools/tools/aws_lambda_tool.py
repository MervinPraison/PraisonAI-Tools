"""AWS Lambda Tool for PraisonAI Agents.

Invoke AWS Lambda functions.

Usage:
    from praisonai_tools import AWSLambdaTool
    
    lambda_tool = AWSLambdaTool()
    result = lambda_tool.invoke("my-function", {"key": "value"})

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


class AWSLambdaTool(BaseTool):
    """Tool for AWS Lambda."""
    
    name = "aws_lambda"
    description = "Invoke AWS Lambda functions."
    
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
                raise ImportError("boto3 not installed")
            self._client = boto3.client("lambda", region_name=self.region)
        return self._client
    
    def run(
        self,
        action: str = "invoke",
        function_name: Optional[str] = None,
        **kwargs
    ) -> Union[str, Dict[str, Any], List[Dict[str, Any]]]:
        action = action.lower().replace("-", "_")
        
        if action == "invoke":
            return self.invoke(function_name=function_name, payload=kwargs.get("payload"))
        elif action == "list_functions":
            return self.list_functions()
        else:
            return {"error": f"Unknown action: {action}"}
    
    def invoke(self, function_name: str, payload: Dict = None) -> Dict[str, Any]:
        """Invoke Lambda function."""
        if not function_name:
            return {"error": "function_name is required"}
        
        try:
            import json
            resp = self.client.invoke(
                FunctionName=function_name,
                InvocationType="RequestResponse",
                Payload=json.dumps(payload or {}),
            )
            result = json.loads(resp["Payload"].read())
            return {"status_code": resp["StatusCode"], "result": result}
        except Exception as e:
            logger.error(f"Lambda invoke error: {e}")
            return {"error": str(e)}
    
    def list_functions(self) -> List[Dict[str, Any]]:
        """List Lambda functions."""
        try:
            resp = self.client.list_functions()
            return [
                {"name": f["FunctionName"], "runtime": f.get("Runtime"), "memory": f.get("MemorySize")}
                for f in resp.get("Functions", [])
            ]
        except Exception as e:
            logger.error(f"Lambda list_functions error: {e}")
            return [{"error": str(e)}]


def invoke_lambda(function_name: str, payload: Dict = None) -> Dict[str, Any]:
    """Invoke Lambda function."""
    return AWSLambdaTool().invoke(function_name=function_name, payload=payload)
