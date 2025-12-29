"""
Chart Tool - Generate charts and visualizations from data.

Supports various chart types including bar, line, pie, scatter, etc.
Uses matplotlib for rendering with optional AI-assisted chart selection.
"""

import os
import logging
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Union
from pathlib import Path

try:
    from .base import RecipeToolBase, RecipeToolResult
except ImportError:
    from base import RecipeToolBase, RecipeToolResult

logger = logging.getLogger(__name__)


@dataclass
class ChartResult(RecipeToolResult):
    """Result from chart generation."""
    output_path: str = ""
    chart_type: str = ""
    title: str = ""
    data_points: int = 0


class ChartTool(RecipeToolBase):
    """Chart generation tool using matplotlib."""
    
    CHART_TYPES = ["bar", "line", "pie", "scatter", "histogram", "area", "heatmap"]
    
    def __init__(
        self,
        style: str = "seaborn-v0_8-whitegrid",
        figsize: tuple = (10, 6),
        dpi: int = 150,
    ):
        self.style = style
        self.figsize = figsize
        self.dpi = dpi
    
    def check_dependencies(self) -> Dict[str, bool]:
        """Check if required dependencies are available."""
        deps = {}
        try:
            import matplotlib
            deps["matplotlib"] = True
        except ImportError:
            deps["matplotlib"] = False
        
        try:
            import pandas
            deps["pandas"] = True
        except ImportError:
            deps["pandas"] = False
        
        return deps
    
    def _setup_style(self):
        """Setup matplotlib style."""
        import matplotlib.pyplot as plt
        try:
            plt.style.use(self.style)
        except OSError:
            plt.style.use("ggplot")
    
    def bar(
        self,
        data: Dict[str, Union[int, float]],
        output_path: str,
        title: str = "Bar Chart",
        xlabel: str = "",
        ylabel: str = "",
        color: str = "#3498db",
        horizontal: bool = False,
    ) -> ChartResult:
        """
        Create a bar chart.
        
        Args:
            data: Dictionary of labels to values
            output_path: Path to save chart
            title: Chart title
            xlabel: X-axis label
            ylabel: Y-axis label
            color: Bar color
            horizontal: If True, create horizontal bar chart
        """
        import matplotlib.pyplot as plt
        
        self._setup_style()
        fig, ax = plt.subplots(figsize=self.figsize)
        
        labels = list(data.keys())
        values = list(data.values())
        
        if horizontal:
            ax.barh(labels, values, color=color)
        else:
            ax.bar(labels, values, color=color)
        
        ax.set_title(title)
        ax.set_xlabel(xlabel)
        ax.set_ylabel(ylabel)
        
        plt.tight_layout()
        plt.savefig(output_path, dpi=self.dpi, bbox_inches='tight')
        plt.close()
        
        return ChartResult(
            success=True,
            output_path=output_path,
            chart_type="bar",
            title=title,
            data_points=len(data),
        )
    
    def line(
        self,
        data: Union[Dict[str, List], List[Dict]],
        output_path: str,
        title: str = "Line Chart",
        xlabel: str = "",
        ylabel: str = "",
        legend: bool = True,
    ) -> ChartResult:
        """
        Create a line chart.
        
        Args:
            data: Dict with 'x' and 'y' keys, or list of series dicts
            output_path: Path to save chart
            title: Chart title
            xlabel: X-axis label
            ylabel: Y-axis label
            legend: Show legend
        """
        import matplotlib.pyplot as plt
        
        self._setup_style()
        fig, ax = plt.subplots(figsize=self.figsize)
        
        if isinstance(data, dict) and 'x' in data and 'y' in data:
            ax.plot(data['x'], data['y'], marker='o')
            data_points = len(data['x'])
        elif isinstance(data, list):
            data_points = 0
            for series in data:
                label = series.get('label', '')
                ax.plot(series['x'], series['y'], marker='o', label=label)
                data_points += len(series['x'])
            if legend:
                ax.legend()
        else:
            return ChartResult(success=False, error="Invalid data format for line chart")
        
        ax.set_title(title)
        ax.set_xlabel(xlabel)
        ax.set_ylabel(ylabel)
        
        plt.tight_layout()
        plt.savefig(output_path, dpi=self.dpi, bbox_inches='tight')
        plt.close()
        
        return ChartResult(
            success=True,
            output_path=output_path,
            chart_type="line",
            title=title,
            data_points=data_points,
        )
    
    def pie(
        self,
        data: Dict[str, Union[int, float]],
        output_path: str,
        title: str = "Pie Chart",
        autopct: str = '%1.1f%%',
        explode: Optional[List[float]] = None,
    ) -> ChartResult:
        """
        Create a pie chart.
        
        Args:
            data: Dictionary of labels to values
            output_path: Path to save chart
            title: Chart title
            autopct: Format string for percentages
            explode: List of explode values for each slice
        """
        import matplotlib.pyplot as plt
        
        self._setup_style()
        fig, ax = plt.subplots(figsize=self.figsize)
        
        labels = list(data.keys())
        values = list(data.values())
        
        ax.pie(values, labels=labels, autopct=autopct, explode=explode)
        ax.set_title(title)
        
        plt.tight_layout()
        plt.savefig(output_path, dpi=self.dpi, bbox_inches='tight')
        plt.close()
        
        return ChartResult(
            success=True,
            output_path=output_path,
            chart_type="pie",
            title=title,
            data_points=len(data),
        )
    
    def scatter(
        self,
        x: List[Union[int, float]],
        y: List[Union[int, float]],
        output_path: str,
        title: str = "Scatter Plot",
        xlabel: str = "",
        ylabel: str = "",
        color: str = "#3498db",
        size: int = 50,
    ) -> ChartResult:
        """
        Create a scatter plot.
        
        Args:
            x: X values
            y: Y values
            output_path: Path to save chart
            title: Chart title
            xlabel: X-axis label
            ylabel: Y-axis label
            color: Point color
            size: Point size
        """
        import matplotlib.pyplot as plt
        
        self._setup_style()
        fig, ax = plt.subplots(figsize=self.figsize)
        
        ax.scatter(x, y, c=color, s=size, alpha=0.7)
        ax.set_title(title)
        ax.set_xlabel(xlabel)
        ax.set_ylabel(ylabel)
        
        plt.tight_layout()
        plt.savefig(output_path, dpi=self.dpi, bbox_inches='tight')
        plt.close()
        
        return ChartResult(
            success=True,
            output_path=output_path,
            chart_type="scatter",
            title=title,
            data_points=len(x),
        )
    
    def histogram(
        self,
        data: List[Union[int, float]],
        output_path: str,
        title: str = "Histogram",
        xlabel: str = "",
        ylabel: str = "Frequency",
        bins: int = 20,
        color: str = "#3498db",
    ) -> ChartResult:
        """
        Create a histogram.
        
        Args:
            data: List of values
            output_path: Path to save chart
            title: Chart title
            xlabel: X-axis label
            ylabel: Y-axis label
            bins: Number of bins
            color: Bar color
        """
        import matplotlib.pyplot as plt
        
        self._setup_style()
        fig, ax = plt.subplots(figsize=self.figsize)
        
        ax.hist(data, bins=bins, color=color, edgecolor='white', alpha=0.7)
        ax.set_title(title)
        ax.set_xlabel(xlabel)
        ax.set_ylabel(ylabel)
        
        plt.tight_layout()
        plt.savefig(output_path, dpi=self.dpi, bbox_inches='tight')
        plt.close()
        
        return ChartResult(
            success=True,
            output_path=output_path,
            chart_type="histogram",
            title=title,
            data_points=len(data),
        )
    
    def from_dataframe(
        self,
        df,
        output_path: str,
        chart_type: str = "bar",
        x_col: Optional[str] = None,
        y_col: Optional[str] = None,
        title: str = "",
        **kwargs,
    ) -> ChartResult:
        """
        Create chart from pandas DataFrame.
        
        Args:
            df: Pandas DataFrame
            output_path: Path to save chart
            chart_type: Type of chart
            x_col: Column for x-axis
            y_col: Column for y-axis
            title: Chart title
            **kwargs: Additional chart options
        """
        import matplotlib.pyplot as plt
        
        self._setup_style()
        fig, ax = plt.subplots(figsize=self.figsize)
        
        if chart_type == "bar":
            if x_col and y_col:
                df.plot(kind='bar', x=x_col, y=y_col, ax=ax, **kwargs)
            else:
                df.plot(kind='bar', ax=ax, **kwargs)
        elif chart_type == "line":
            if x_col and y_col:
                df.plot(kind='line', x=x_col, y=y_col, ax=ax, **kwargs)
            else:
                df.plot(kind='line', ax=ax, **kwargs)
        elif chart_type == "pie":
            if y_col:
                df[y_col].plot(kind='pie', ax=ax, autopct='%1.1f%%', **kwargs)
            else:
                df.iloc[:, 0].plot(kind='pie', ax=ax, autopct='%1.1f%%', **kwargs)
        elif chart_type == "scatter":
            if x_col and y_col:
                df.plot(kind='scatter', x=x_col, y=y_col, ax=ax, **kwargs)
        elif chart_type == "histogram":
            if y_col:
                df[y_col].plot(kind='hist', ax=ax, **kwargs)
            else:
                df.iloc[:, 0].plot(kind='hist', ax=ax, **kwargs)
        
        if title:
            ax.set_title(title)
        
        plt.tight_layout()
        plt.savefig(output_path, dpi=self.dpi, bbox_inches='tight')
        plt.close()
        
        return ChartResult(
            success=True,
            output_path=output_path,
            chart_type=chart_type,
            title=title,
            data_points=len(df),
        )
    
    def from_csv(
        self,
        csv_path: str,
        output_path: str,
        chart_type: str = "bar",
        x_col: Optional[str] = None,
        y_col: Optional[str] = None,
        title: str = "",
        **kwargs,
    ) -> ChartResult:
        """
        Create chart from CSV file.
        
        Args:
            csv_path: Path to CSV file
            output_path: Path to save chart
            chart_type: Type of chart
            x_col: Column for x-axis
            y_col: Column for y-axis
            title: Chart title
        """
        import pandas as pd
        
        if not os.path.exists(csv_path):
            return ChartResult(success=False, error=f"CSV not found: {csv_path}")
        
        df = pd.read_csv(csv_path)
        return self.from_dataframe(df, output_path, chart_type, x_col, y_col, title, **kwargs)


# Convenience functions
def chart_bar(data: Dict, output_path: str, title: str = "Bar Chart") -> str:
    """Create bar chart and return path."""
    tool = ChartTool()
    result = tool.bar(data, output_path, title)
    return result.output_path if result.success else ""


def chart_line(data: Dict, output_path: str, title: str = "Line Chart") -> str:
    """Create line chart and return path."""
    tool = ChartTool()
    result = tool.line(data, output_path, title)
    return result.output_path if result.success else ""


def chart_pie(data: Dict, output_path: str, title: str = "Pie Chart") -> str:
    """Create pie chart and return path."""
    tool = ChartTool()
    result = tool.pie(data, output_path, title)
    return result.output_path if result.success else ""


__all__ = [
    "ChartTool",
    "ChartResult",
    "chart_bar",
    "chart_line",
    "chart_pie",
]
