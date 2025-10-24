"""
Data loading, schema validation, unit conversion, and caching.
"""

import os
from pathlib import Path
from typing import Dict, List, Optional, Any
import yaml
import pandas as pd
import numpy as np
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class SchemaValidator:
    """Validates data against typed schema."""
    
    def __init__(self, schema_config: Dict[str, Any]):
        self.schema = schema_config.get("schema", {})
        
    def validate(self, df: pd.DataFrame) -> pd.DataFrame:
        """Validate and type-cast dataframe according to schema."""
        errors = []
        
        # Check required columns
        for col_name, col_spec in self.schema.items():
            if col_spec.get("required", False) and col_name not in df.columns:
                errors.append(f"Missing required column: {col_name}")
        
        if errors:
            raise ValueError(f"Schema validation failed: {', '.join(errors)}")
        
        # Type conversion
        for col_name, col_spec in self.schema.items():
            if col_name not in df.columns:
                continue
                
            col_type = col_spec.get("type")
            
            if col_type == "datetime":
                fmt = col_spec.get("format", None)
                try:
                    df[col_name] = pd.to_datetime(df[col_name], format=fmt)
                except Exception as e:
                    logger.warning(f"Failed to parse datetime for {col_name}: {e}")
                    
            elif col_type == "float":
                df[col_name] = pd.to_numeric(df[col_name], errors="coerce")
                
            elif col_type == "int":
                df[col_name] = pd.to_numeric(df[col_name], errors="coerce").astype("Int64")
        
        logger.info(f"Schema validation passed for {len(df)} rows")
        return df


class UnitConverter:
    """Convert sensor units to standard SI units."""
    
    CONVERSIONS = {
        "deg/s": lambda x: x * np.pi / 180.0,  # degrees/s to rad/s
        "g": lambda x: x * 9.80665,  # g-force to m/s^2
        "mph": lambda x: x * 0.44704,  # mph to m/s
        "km/h": lambda x: x / 3.6,  # km/h to m/s
    }
    
    @staticmethod
    def convert(df: pd.DataFrame, schema: Dict[str, Any]) -> pd.DataFrame:
        """Apply unit conversions based on schema."""
        for col_name, col_spec in schema.items():
            if col_name not in df.columns:
                continue
                
            unit = col_spec.get("unit")
            source_unit = col_spec.get("source_unit")
            
            if source_unit and source_unit != unit:
                if source_unit in UnitConverter.CONVERSIONS:
                    df[col_name] = UnitConverter.CONVERSIONS[source_unit](df[col_name])
                    logger.info(f"Converted {col_name} from {source_unit} to {unit}")
        
        return df


class DataLoader:
    """Load and cache sensor data."""
    
    def __init__(self, config_path: str):
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        # Expand environment variables
        data_root = self.config.get("data_root", "./data")
        if "${" in data_root:
            # Parse ${VAR:default}
            parts = data_root.strip("${}").split(":")
            var_name = parts[0]
            default = parts[1] if len(parts) > 1 else "./data"
            data_root = os.environ.get(var_name, default)
        
        self.data_root = Path(data_root)
        self.file_format = self.config.get("file_format", "csv")
        self.validator = SchemaValidator(self.config)
        self.cache_dir = self.data_root / ".cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
    def load_file(self, filepath: Path, use_cache: bool = True) -> pd.DataFrame:
        """Load a single data file with caching."""
        cache_path = self.cache_dir / f"{filepath.stem}.parquet"
        
        # Check cache
        if use_cache and cache_path.exists():
            cache_mtime = cache_path.stat().st_mtime
            file_mtime = filepath.stat().st_mtime
            
            if cache_mtime > file_mtime:
                logger.info(f"Loading from cache: {cache_path}")
                return pd.read_parquet(cache_path)
        
        # Load file
        logger.info(f"Loading file: {filepath}")
        if self.file_format == "csv":
            df = pd.read_csv(filepath)
        elif self.file_format == "parquet":
            df = pd.read_parquet(filepath)
        else:
            raise ValueError(f"Unsupported format: {self.file_format}")
        
        # Validate and convert
        df = self.validator.validate(df)
        df = UnitConverter.convert(df, self.config.get("schema", {}))
        
        # Cache
        if use_cache:
            df.to_parquet(cache_path, index=False)
            logger.info(f"Cached to: {cache_path}")
        
        return df
    
    def load_all(self, pattern: str = "*", use_cache: bool = True) -> List[pd.DataFrame]:
        """Load all matching files."""
        if self.file_format == "csv":
            files = list(self.data_root.glob(f"{pattern}.csv"))
        else:
            files = list(self.data_root.glob(f"{pattern}.parquet"))
        
        if not files:
            raise FileNotFoundError(f"No files found matching {pattern} in {self.data_root}")
        
        logger.info(f"Found {len(files)} files to load")
        
        dfs = []
        for filepath in sorted(files):
            try:
                df = self.load_file(filepath, use_cache=use_cache)
                dfs.append(df)
            except Exception as e:
                logger.error(f"Failed to load {filepath}: {e}")
        
        return dfs
    
    def get_sampling_rate(self, sensor: str) -> float:
        """Get configured sampling rate for a sensor."""
        rates = self.config.get("sampling_rates", {})
        return rates.get(sensor, 100.0)
    
    def get_quality_thresholds(self) -> Dict[str, float]:
        """Get data quality thresholds."""
        return self.config.get("quality", {})


def load_config(config_path: str) -> Dict[str, Any]:
    """Load YAML config with environment variable expansion."""
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    # Expand environment variables recursively
    def expand_env(obj):
        if isinstance(obj, str) and "${" in obj:
            parts = obj.strip("${}").split(":")
            var_name = parts[0]
            default = parts[1] if len(parts) > 1 else ""
            return os.environ.get(var_name, default)
        elif isinstance(obj, dict):
            return {k: expand_env(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [expand_env(x) for x in obj]
        return obj
    
    return expand_env(config)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # Example usage
    loader = DataLoader("./configs/dataset.yml")
    dfs = loader.load_all()
    print(f"Loaded {len(dfs)} dataframes")
    if dfs:
        print(f"First dataframe shape: {dfs[0].shape}")
        print(f"Columns: {dfs[0].columns.tolist()}")
