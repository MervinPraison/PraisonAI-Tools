"""Visualization Tool for PraisonAI Agents.

Create charts and visualizations.

Usage:
    from praisonai_tools import VisualizationTool
    
    viz = VisualizationTool()
    viz.bar_chart(data={"A": 10, "B": 20}, output_path="chart.png")
"""

import logging
from typing import Any, Dict, List, Optional, Union

from praisonai_tools.tools.base import BaseTool

logger = logging.getLogger(__name__)


class VisualizationTool(BaseTool):
    """Tool for creating visualizations."""
    
    name = "visualization"
    description = "Create charts and visualizations."
    
    def run(
        self,
        action: str = "bar_chart",
        data: Optional[Dict] = None,
        output_path: str = "chart.png",
        **kwargs
    ) -> Union[str, Dict[str, Any]]:
        action = action.lower().replace("-", "_")
        
        if action == "bar_chart":
            return self.bar_chart(data=data, output_path=output_path, **kwargs)
        elif action == "line_chart":
            return self.line_chart(data=data, output_path=output_path, **kwargs)
        elif action == "pie_chart":
            return self.pie_chart(data=data, output_path=output_path, **kwargs)
        elif action == "scatter":
            return self.scatter(x=kwargs.get("x"), y=kwargs.get("y"), output_path=output_path)
        else:
            return {"error": f"Unknown action: {action}"}
    
    def bar_chart(self, data: Dict, output_path: str = "bar_chart.png", title: str = "Bar Chart") -> Dict[str, Any]:
        """Create bar chart."""
        if not data:
            return {"error": "data is required"}
        
        try:
            import matplotlib.pyplot as plt
        except ImportError:
            return {"error": "matplotlib not installed"}
        
        try:
            plt.figure(figsize=(10, 6))
            plt.bar(list(data.keys()), list(data.values()))
            plt.title(title)
            plt.tight_layout()
            plt.savefig(output_path)
            plt.close()
            return {"success": True, "output_path": output_path}
        except Exception as e:
            logger.error(f"Visualization bar_chart error: {e}")
            return {"error": str(e)}
    
    def line_chart(self, data: Dict, output_path: str = "line_chart.png", title: str = "Line Chart") -> Dict[str, Any]:
        """Create line chart."""
        if not data:
            return {"error": "data is required"}
        
        try:
            import matplotlib.pyplot as plt
        except ImportError:
            return {"error": "matplotlib not installed"}
        
        try:
            plt.figure(figsize=(10, 6))
            plt.plot(list(data.keys()), list(data.values()), marker="o")
            plt.title(title)
            plt.tight_layout()
            plt.savefig(output_path)
            plt.close()
            return {"success": True, "output_path": output_path}
        except Exception as e:
            logger.error(f"Visualization line_chart error: {e}")
            return {"error": str(e)}
    
    def pie_chart(self, data: Dict, output_path: str = "pie_chart.png", title: str = "Pie Chart") -> Dict[str, Any]:
        """Create pie chart."""
        if not data:
            return {"error": "data is required"}
        
        try:
            import matplotlib.pyplot as plt
        except ImportError:
            return {"error": "matplotlib not installed"}
        
        try:
            plt.figure(figsize=(10, 8))
            plt.pie(list(data.values()), labels=list(data.keys()), autopct="%1.1f%%")
            plt.title(title)
            plt.tight_layout()
            plt.savefig(output_path)
            plt.close()
            return {"success": True, "output_path": output_path}
        except Exception as e:
            logger.error(f"Visualization pie_chart error: {e}")
            return {"error": str(e)}
    
    def scatter(self, x: List, y: List, output_path: str = "scatter.png", title: str = "Scatter Plot") -> Dict[str, Any]:
        """Create scatter plot."""
        if not x or not y:
            return {"error": "x and y data are required"}
        
        try:
            import matplotlib.pyplot as plt
        except ImportError:
            return {"error": "matplotlib not installed"}
        
        try:
            plt.figure(figsize=(10, 6))
            plt.scatter(x, y)
            plt.title(title)
            plt.tight_layout()
            plt.savefig(output_path)
            plt.close()
            return {"success": True, "output_path": output_path}
        except Exception as e:
            logger.error(f"Visualization scatter error: {e}")
            return {"error": str(e)}


def create_bar_chart(data: Dict, output_path: str = "chart.png") -> Dict[str, Any]:
    """Create bar chart."""
    return VisualizationTool().bar_chart(data=data, output_path=output_path)
