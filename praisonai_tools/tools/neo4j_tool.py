"""Neo4j Tool for PraisonAI Agents.

Execute Cypher queries on Neo4j graph database.

Usage:
    from praisonai_tools import Neo4jTool
    
    neo4j = Neo4jTool()
    results = neo4j.query("MATCH (n) RETURN n LIMIT 10")

Environment Variables:
    NEO4J_URI: Neo4j connection URI
    NEO4J_USER: Username
    NEO4J_PASSWORD: Password
"""

import os
import logging
from typing import Any, Dict, List, Optional, Union

from praisonai_tools.tools.base import BaseTool

logger = logging.getLogger(__name__)


class Neo4jTool(BaseTool):
    """Tool for Neo4j graph database."""
    
    name = "neo4j"
    description = "Execute Cypher queries on Neo4j graph database."
    
    def __init__(
        self,
        uri: Optional[str] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
    ):
        self.uri = uri or os.getenv("NEO4J_URI", "bolt://localhost:7687")
        self.user = user or os.getenv("NEO4J_USER", "neo4j")
        self.password = password or os.getenv("NEO4J_PASSWORD")
        self._driver = None
        super().__init__()
    
    @property
    def driver(self):
        if self._driver is None:
            try:
                from neo4j import GraphDatabase
            except ImportError:
                raise ImportError("neo4j not installed. Install with: pip install neo4j")
            
            if not self.password:
                raise ValueError("NEO4J_PASSWORD required")
            
            self._driver = GraphDatabase.driver(self.uri, auth=(self.user, self.password))
        return self._driver
    
    def run(
        self,
        action: str = "query",
        cypher: Optional[str] = None,
        **kwargs
    ) -> Union[str, Dict[str, Any], List[Dict[str, Any]]]:
        action = action.lower().replace("-", "_")
        
        if action == "query":
            return self.query(cypher=cypher)
        elif action == "execute":
            return self.execute(cypher=cypher)
        else:
            return {"error": f"Unknown action: {action}"}
    
    def query(self, cypher: str) -> List[Dict[str, Any]]:
        """Execute Cypher query."""
        if not cypher:
            return [{"error": "cypher is required"}]
        
        try:
            with self.driver.session() as session:
                result = session.run(cypher)
                records = []
                for record in result:
                    records.append(dict(record))
                return records
        except Exception as e:
            logger.error(f"Neo4j query error: {e}")
            return [{"error": str(e)}]
    
    def execute(self, cypher: str) -> Dict[str, Any]:
        """Execute Cypher statement."""
        if not cypher:
            return {"error": "cypher is required"}
        
        try:
            with self.driver.session() as session:
                result = session.run(cypher)
                summary = result.consume()
                return {
                    "success": True,
                    "nodes_created": summary.counters.nodes_created,
                    "relationships_created": summary.counters.relationships_created,
                }
        except Exception as e:
            logger.error(f"Neo4j execute error: {e}")
            return {"error": str(e)}
    
    def close(self):
        if self._driver:
            self._driver.close()
            self._driver = None


def neo4j_query(cypher: str) -> List[Dict[str, Any]]:
    """Query Neo4j."""
    return Neo4jTool().query(cypher=cypher)
