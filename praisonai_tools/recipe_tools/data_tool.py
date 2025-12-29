"""
Data Tool - CSV/JSON/Parquet operations via pandas.

Provides:
- Profiling data files
- Cleaning data (duplicates, nulls, types)
- Converting between formats
- Inferring schemas
"""

import importlib.util
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import sys
import os as _os
_dir = _os.path.dirname(_os.path.abspath(__file__))
if _dir not in sys.path:
    sys.path.insert(0, _dir)

try:
    from .base import RecipeToolBase
except ImportError:
    from base import RecipeToolBase

logger = logging.getLogger(__name__)

# Try to import pandas
try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False
    pd = None

# Check for pyarrow availability
PYARROW_AVAILABLE = importlib.util.find_spec("pyarrow") is not None


@dataclass
class ColumnProfile:
    """Profile of a single column."""
    name: str
    dtype: str
    count: int
    null_count: int
    null_percent: float
    unique_count: int
    sample_values: List[Any] = field(default_factory=list)
    min_value: Optional[Any] = None
    max_value: Optional[Any] = None
    mean: Optional[float] = None
    std: Optional[float] = None


@dataclass
class DataProfileResult:
    """Result of profiling a data file."""
    path: str
    format: str
    row_count: int
    column_count: int
    file_size: int
    columns: List[ColumnProfile] = field(default_factory=list)
    duplicate_rows: int = 0
    memory_usage: int = 0
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "path": self.path,
            "format": self.format,
            "row_count": self.row_count,
            "column_count": self.column_count,
            "file_size": self.file_size,
            "duplicate_rows": self.duplicate_rows,
            "memory_usage": self.memory_usage,
            "columns": [
                {
                    "name": c.name,
                    "dtype": c.dtype,
                    "count": c.count,
                    "null_count": c.null_count,
                    "null_percent": c.null_percent,
                    "unique_count": c.unique_count,
                }
                for c in self.columns
            ],
        }


class DataTool(RecipeToolBase):
    """
    Data operations tool using pandas.
    
    Provides data profiling, cleaning, format conversion, and schema inference.
    """
    
    name = "data_tool"
    description = "CSV/JSON/Parquet operations via pandas"
    
    def check_dependencies(self) -> Dict[str, bool]:
        """Check for pandas and pyarrow."""
        return {
            "pandas": PANDAS_AVAILABLE,
            "pyarrow": PYARROW_AVAILABLE,
        }
    
    def _require_pandas(self):
        """Ensure pandas is available."""
        if not PANDAS_AVAILABLE:
            raise ImportError("pandas is required. Install with: pip install pandas")
    
    def _detect_format(self, path: Path) -> str:
        """Detect file format from extension."""
        ext = path.suffix.lower()
        formats = {
            ".csv": "csv",
            ".tsv": "tsv",
            ".json": "json",
            ".jsonl": "jsonl",
            ".parquet": "parquet",
            ".xlsx": "excel",
            ".xls": "excel",
        }
        return formats.get(ext, "csv")
    
    def _read_file(
        self,
        path: Path,
        format: Optional[str] = None,
        sample: Optional[int] = None,
    ) -> "pd.DataFrame":
        """Read data file into DataFrame."""
        self._require_pandas()
        
        if format is None:
            format = self._detect_format(path)
        
        kwargs = {}
        if sample:
            kwargs["nrows"] = sample
        
        if format == "csv":
            return pd.read_csv(path, **kwargs)
        elif format == "tsv":
            return pd.read_csv(path, sep="\t", **kwargs)
        elif format == "json":
            return pd.read_json(path, **kwargs)
        elif format == "jsonl":
            return pd.read_json(path, lines=True, **kwargs)
        elif format == "parquet":
            if not PYARROW_AVAILABLE:
                raise ImportError("pyarrow required for parquet. Install with: pip install pyarrow")
            df = pd.read_parquet(path)
            if sample:
                df = df.head(sample)
            return df
        elif format == "excel":
            return pd.read_excel(path, **kwargs)
        else:
            raise ValueError(f"Unsupported format: {format}")
    
    def _write_file(
        self,
        df: "pd.DataFrame",
        path: Path,
        format: Optional[str] = None,
    ) -> None:
        """Write DataFrame to file."""
        if format is None:
            format = self._detect_format(path)
        
        if format == "csv":
            df.to_csv(path, index=False)
        elif format == "tsv":
            df.to_csv(path, sep="\t", index=False)
        elif format == "json":
            df.to_json(path, orient="records", indent=2)
        elif format == "jsonl":
            df.to_json(path, orient="records", lines=True)
        elif format == "parquet":
            if not PYARROW_AVAILABLE:
                raise ImportError("pyarrow required for parquet")
            df.to_parquet(path, index=False)
        elif format == "excel":
            df.to_excel(path, index=False)
        else:
            raise ValueError(f"Unsupported format: {format}")
    
    def profile(
        self,
        path: Union[str, Path],
        sample: Optional[int] = None,
    ) -> DataProfileResult:
        """
        Profile a data file.
        
        Args:
            path: Path to data file
            sample: Number of rows to sample (for large files)
            
        Returns:
            DataProfileResult with file statistics
        """
        self._require_pandas()
        path = Path(path)
        
        if not path.exists():
            raise FileNotFoundError(f"Data file not found: {path}")
        
        format = self._detect_format(path)
        df = self._read_file(path, format, sample)
        
        # Profile columns
        columns = []
        for col in df.columns:
            series = df[col]
            
            profile = ColumnProfile(
                name=col,
                dtype=str(series.dtype),
                count=len(series),
                null_count=int(series.isna().sum()),
                null_percent=float(series.isna().mean() * 100),
                unique_count=int(series.nunique()),
                sample_values=series.dropna().head(5).tolist(),
            )
            
            # Numeric stats
            if pd.api.types.is_numeric_dtype(series):
                profile.min_value = float(series.min()) if not series.isna().all() else None
                profile.max_value = float(series.max()) if not series.isna().all() else None
                profile.mean = float(series.mean()) if not series.isna().all() else None
                profile.std = float(series.std()) if not series.isna().all() else None
            
            columns.append(profile)
        
        return DataProfileResult(
            path=str(path),
            format=format,
            row_count=len(df),
            column_count=len(df.columns),
            file_size=path.stat().st_size,
            columns=columns,
            duplicate_rows=int(df.duplicated().sum()),
            memory_usage=int(df.memory_usage(deep=True).sum()),
        )
    
    def clean(
        self,
        input_path: Union[str, Path],
        output_path: Optional[Union[str, Path]] = None,
        drop_duplicates: bool = True,
        drop_empty_rows: bool = True,
        fill_nulls: Optional[str] = None,
        strip_whitespace: bool = True,
    ) -> Path:
        """
        Clean a data file.
        
        Args:
            input_path: Input data file
            output_path: Output file (auto-generated if not provided)
            drop_duplicates: Remove duplicate rows
            drop_empty_rows: Remove rows that are all null
            fill_nulls: Strategy for null values (mean, median, mode, value)
            strip_whitespace: Strip whitespace from string columns
            
        Returns:
            Path to cleaned file
        """
        self._require_pandas()
        input_path = Path(input_path)
        
        if not input_path.exists():
            raise FileNotFoundError(f"Data file not found: {input_path}")
        
        if output_path is None:
            output_path = self._generate_output_path(input_path, suffix="_cleaned")
        else:
            output_path = Path(output_path)
            self._ensure_output_dir(output_path.parent)
        
        df = self._read_file(input_path)
        original_rows = len(df)
        
        # Drop duplicates
        if drop_duplicates:
            df = df.drop_duplicates()
        
        # Drop empty rows
        if drop_empty_rows:
            df = df.dropna(how="all")
        
        # Fill nulls
        if fill_nulls:
            if fill_nulls == "mean":
                df = df.fillna(df.mean(numeric_only=True))
            elif fill_nulls == "median":
                df = df.fillna(df.median(numeric_only=True))
            elif fill_nulls == "mode":
                for col in df.columns:
                    mode = df[col].mode()
                    if len(mode) > 0:
                        df[col] = df[col].fillna(mode[0])
            else:
                df = df.fillna(fill_nulls)
        
        # Strip whitespace
        if strip_whitespace:
            for col in df.select_dtypes(include=["object"]).columns:
                df[col] = df[col].str.strip()
        
        self._write_file(df, output_path)
        
        logger.info(f"Cleaned {original_rows} -> {len(df)} rows")
        return output_path
    
    def convert(
        self,
        input_path: Union[str, Path],
        output_path: Union[str, Path],
        input_format: Optional[str] = None,
        output_format: Optional[str] = None,
    ) -> Path:
        """
        Convert data between formats.
        
        Args:
            input_path: Input data file
            output_path: Output file
            input_format: Input format (auto-detected if not provided)
            output_format: Output format (auto-detected if not provided)
            
        Returns:
            Path to converted file
        """
        self._require_pandas()
        input_path = Path(input_path)
        output_path = Path(output_path)
        
        if not input_path.exists():
            raise FileNotFoundError(f"Data file not found: {input_path}")
        
        self._ensure_output_dir(output_path.parent)
        
        df = self._read_file(input_path, input_format)
        self._write_file(df, output_path, output_format)
        
        return output_path
    
    def infer_schema(
        self,
        path: Union[str, Path],
        sample: int = 1000,
        output_format: str = "json_schema",
    ) -> Dict:
        """
        Infer schema from data file.
        
        Args:
            path: Path to data file
            sample: Number of rows to sample
            output_format: Schema format (json_schema, simple)
            
        Returns:
            Schema dictionary
        """
        self._require_pandas()
        path = Path(path)
        
        if not path.exists():
            raise FileNotFoundError(f"Data file not found: {path}")
        
        df = self._read_file(path, sample=sample)
        
        if output_format == "json_schema":
            return self._to_json_schema(df)
        else:
            return self._to_simple_schema(df)
    
    def _to_json_schema(self, df: "pd.DataFrame") -> Dict:
        """Convert DataFrame to JSON Schema."""
        type_map = {
            "int64": "integer",
            "int32": "integer",
            "float64": "number",
            "float32": "number",
            "bool": "boolean",
            "object": "string",
            "datetime64[ns]": "string",
        }
        
        properties = {}
        required = []
        
        for col in df.columns:
            dtype = str(df[col].dtype)
            json_type = type_map.get(dtype, "string")
            
            prop = {"type": json_type}
            
            # Add format hints
            if "datetime" in dtype:
                prop["format"] = "date-time"
            
            # Check if required (no nulls)
            if df[col].notna().all():
                required.append(col)
            
            properties[col] = prop
        
        return {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "type": "object",
            "properties": properties,
            "required": required,
        }
    
    def _to_simple_schema(self, df: "pd.DataFrame") -> Dict:
        """Convert DataFrame to simple schema."""
        return {
            "columns": [
                {
                    "name": col,
                    "type": str(df[col].dtype),
                    "nullable": bool(df[col].isna().any()),
                }
                for col in df.columns
            ]
        }
    
    def generate_profile_report(
        self,
        path: Union[str, Path],
        output_path: Optional[Union[str, Path]] = None,
        sample: Optional[int] = None,
    ) -> Path:
        """
        Generate an HTML profile report.
        
        Args:
            path: Path to data file
            output_path: Output HTML file
            sample: Number of rows to sample
            
        Returns:
            Path to HTML report
        """
        path = Path(path)
        profile = self.profile(path, sample)
        
        if output_path is None:
            output_path = self._generate_output_path(path, suffix="_profile", extension="html")
        else:
            output_path = Path(output_path)
            self._ensure_output_dir(output_path.parent)
        
        # Generate simple HTML report
        html = self._generate_html_report(profile)
        output_path.write_text(html, encoding="utf-8")
        
        return output_path
    
    def _generate_html_report(self, profile: DataProfileResult) -> str:
        """Generate HTML report from profile."""
        html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Data Profile: {Path(profile.path).name}</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 40px; }}
        h1 {{ color: #333; }}
        table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 12px; text-align: left; }}
        th {{ background-color: #4CAF50; color: white; }}
        tr:nth-child(even) {{ background-color: #f2f2f2; }}
        .stat {{ display: inline-block; margin: 10px 20px 10px 0; padding: 10px 20px; background: #f5f5f5; border-radius: 5px; }}
        .stat-value {{ font-size: 24px; font-weight: bold; color: #333; }}
        .stat-label {{ font-size: 12px; color: #666; }}
    </style>
</head>
<body>
    <h1>Data Profile: {Path(profile.path).name}</h1>
    
    <div class="stats">
        <div class="stat">
            <div class="stat-value">{profile.row_count:,}</div>
            <div class="stat-label">Rows</div>
        </div>
        <div class="stat">
            <div class="stat-value">{profile.column_count}</div>
            <div class="stat-label">Columns</div>
        </div>
        <div class="stat">
            <div class="stat-value">{profile.duplicate_rows:,}</div>
            <div class="stat-label">Duplicate Rows</div>
        </div>
        <div class="stat">
            <div class="stat-value">{profile.file_size / 1024:.1f} KB</div>
            <div class="stat-label">File Size</div>
        </div>
    </div>
    
    <h2>Columns</h2>
    <table>
        <tr>
            <th>Name</th>
            <th>Type</th>
            <th>Count</th>
            <th>Nulls</th>
            <th>Null %</th>
            <th>Unique</th>
        </tr>
"""
        for col in profile.columns:
            html += f"""        <tr>
            <td>{col.name}</td>
            <td>{col.dtype}</td>
            <td>{col.count:,}</td>
            <td>{col.null_count:,}</td>
            <td>{col.null_percent:.1f}%</td>
            <td>{col.unique_count:,}</td>
        </tr>
"""
        
        html += """    </table>
</body>
</html>"""
        
        return html


# Convenience functions
def data_profile(
    path: Union[str, Path],
    sample: Optional[int] = None,
    verbose: bool = False,
) -> DataProfileResult:
    """Profile a data file."""
    return DataTool(verbose=verbose).profile(path, sample)


def data_clean(
    input_path: Union[str, Path],
    output_path: Optional[Union[str, Path]] = None,
    drop_duplicates: bool = True,
    verbose: bool = False,
) -> Path:
    """Clean a data file."""
    return DataTool(verbose=verbose).clean(input_path, output_path, drop_duplicates)


def data_convert(
    input_path: Union[str, Path],
    output_path: Union[str, Path],
    verbose: bool = False,
) -> Path:
    """Convert data between formats."""
    return DataTool(verbose=verbose).convert(input_path, output_path)


def data_infer_schema(
    path: Union[str, Path],
    output_format: str = "json_schema",
    verbose: bool = False,
) -> Dict:
    """Infer schema from data file."""
    return DataTool(verbose=verbose).infer_schema(path, output_format=output_format)
