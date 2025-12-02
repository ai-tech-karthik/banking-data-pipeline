"""
Parquet IO Manager for persisting Dagster asset outputs to Parquet files.

This IO manager writes pandas DataFrames from Dagster assets to Parquet files
with Snappy compression, enabling efficient storage and fast reads for analytics.
"""

from pathlib import Path
from typing import Union

import pandas as pd
from dagster import (
    ConfigurableIOManager,
    InputContext,
    OutputContext,
    InitResourceContext,
)
from pydantic import Field


class ParquetIOManager(ConfigurableIOManager):
    """
    IO Manager that persists Dagster asset outputs to Parquet files.
    
    This manager handles writing pandas DataFrames to Parquet format with
    Snappy compression and reading them back. Files are organized by asset key
    in the configured output path.
    
    Attributes:
        output_path: Base directory path for Parquet file storage
    """
    
    output_path: str = Field(
        description="Base directory path for Parquet file storage"
    )
    
    def setup_for_execution(self, context: InitResourceContext) -> None:
        """Initialize the IO manager and ensure output directory exists."""
        output_dir = Path(self.output_path)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        if context:
            context.log.info(f"Parquet IO Manager initialized with output path: {self.output_path}")
    
    def _get_file_path(self, context: Union[OutputContext, InputContext]) -> Path:
        """
        Determine the Parquet file path from the asset key.
        
        Args:
            context: Dagster context containing asset metadata
            
        Returns:
            Path object for the Parquet file
        """
        # Get the asset key (e.g., ['account_summary_parquet'])
        asset_key = context.asset_key.path
        file_name = asset_key[-1]  # Use the last part of the key
        
        # Construct the full file path
        file_path = Path(self.output_path) / f"{file_name}.parquet"
        
        return file_path
    
    def handle_output(self, context: OutputContext, obj: pd.DataFrame) -> None:
        """
        Write a pandas DataFrame to a Parquet file with Snappy compression.
        
        Args:
            context: Dagster output context containing asset metadata
            obj: pandas DataFrame to persist
        """
        file_path = self._get_file_path(context)
        
        context.log.info(f"Writing {len(obj)} rows to Parquet file: {file_path}")
        
        # Ensure the output directory exists
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write DataFrame to Parquet with Snappy compression
        obj.to_parquet(
            file_path,
            engine='pyarrow',
            compression='snappy',
            index=False
        )
        
        # Log file size for monitoring
        file_size_mb = file_path.stat().st_size / (1024 * 1024)
        context.log.info(
            f"Successfully wrote {len(obj)} rows to {file_path} "
            f"({file_size_mb:.2f} MB)"
        )
    
    def load_input(self, context: InputContext) -> pd.DataFrame:
        """
        Read a pandas DataFrame from a Parquet file.
        
        Args:
            context: Dagster input context containing asset metadata
            
        Returns:
            pandas DataFrame loaded from Parquet file
            
        Raises:
            FileNotFoundError: If the Parquet file does not exist
        """
        file_path = self._get_file_path(context)
        
        if not file_path.exists():
            raise FileNotFoundError(
                f"Parquet file not found: {file_path}. "
                "Ensure the upstream asset has been materialized."
            )
        
        context.log.info(f"Reading from Parquet file: {file_path}")
        
        # Read DataFrame from Parquet
        df = pd.read_parquet(file_path, engine='pyarrow')
        
        context.log.info(f"Successfully read {len(df)} rows from {file_path}")
        
        return df
