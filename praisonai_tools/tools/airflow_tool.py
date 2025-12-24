"""Airflow Tool for PraisonAI Agents.

Manage Apache Airflow DAGs and tasks.

Usage:
    from praisonai_tools import AirflowTool
    
    airflow = AirflowTool()
    dags = airflow.list_dags()

Environment Variables:
    AIRFLOW_HOST: Airflow API host
    AIRFLOW_USERNAME: Username
    AIRFLOW_PASSWORD: Password
"""

import os
import logging
from typing import Any, Dict, List, Optional, Union

from praisonai_tools.tools.base import BaseTool

logger = logging.getLogger(__name__)


class AirflowTool(BaseTool):
    """Tool for Apache Airflow."""
    
    name = "airflow"
    description = "Manage Apache Airflow DAGs and tasks."
    
    def __init__(
        self,
        host: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
    ):
        self.host = host or os.getenv("AIRFLOW_HOST", "http://localhost:8080")
        self.username = username or os.getenv("AIRFLOW_USERNAME", "admin")
        self.password = password or os.getenv("AIRFLOW_PASSWORD", "admin")
        super().__init__()
    
    def _request(self, method: str, endpoint: str, data: Dict = None) -> Dict:
        try:
            import requests
        except ImportError:
            return {"error": "requests not installed"}
        
        url = f"{self.host}/api/v1/{endpoint}"
        auth = (self.username, self.password)
        
        try:
            if method == "GET":
                resp = requests.get(url, auth=auth, timeout=10)
            elif method == "POST":
                resp = requests.post(url, auth=auth, json=data, timeout=10)
            elif method == "PATCH":
                resp = requests.patch(url, auth=auth, json=data, timeout=10)
            else:
                return {"error": f"Unknown method: {method}"}
            return resp.json()
        except Exception as e:
            return {"error": str(e)}
    
    def run(
        self,
        action: str = "list_dags",
        dag_id: Optional[str] = None,
        **kwargs
    ) -> Union[str, Dict[str, Any], List[Dict[str, Any]]]:
        action = action.lower().replace("-", "_")
        
        if action == "list_dags":
            return self.list_dags()
        elif action == "get_dag":
            return self.get_dag(dag_id=dag_id)
        elif action == "trigger_dag":
            return self.trigger_dag(dag_id=dag_id, **kwargs)
        elif action == "pause_dag":
            return self.pause_dag(dag_id=dag_id)
        elif action == "unpause_dag":
            return self.unpause_dag(dag_id=dag_id)
        else:
            return {"error": f"Unknown action: {action}"}
    
    def list_dags(self) -> List[Dict[str, Any]]:
        """List DAGs."""
        result = self._request("GET", "dags")
        if "error" in result:
            return [result]
        return result.get("dags", [])
    
    def get_dag(self, dag_id: str) -> Dict[str, Any]:
        """Get DAG details."""
        if not dag_id:
            return {"error": "dag_id is required"}
        return self._request("GET", f"dags/{dag_id}")
    
    def trigger_dag(self, dag_id: str, conf: Dict = None) -> Dict[str, Any]:
        """Trigger DAG run."""
        if not dag_id:
            return {"error": "dag_id is required"}
        data = {"conf": conf or {}}
        return self._request("POST", f"dags/{dag_id}/dagRuns", data)
    
    def pause_dag(self, dag_id: str) -> Dict[str, Any]:
        """Pause DAG."""
        if not dag_id:
            return {"error": "dag_id is required"}
        return self._request("PATCH", f"dags/{dag_id}", {"is_paused": True})
    
    def unpause_dag(self, dag_id: str) -> Dict[str, Any]:
        """Unpause DAG."""
        if not dag_id:
            return {"error": "dag_id is required"}
        return self._request("PATCH", f"dags/{dag_id}", {"is_paused": False})


def list_airflow_dags() -> List[Dict[str, Any]]:
    """List Airflow DAGs."""
    return AirflowTool().list_dags()
