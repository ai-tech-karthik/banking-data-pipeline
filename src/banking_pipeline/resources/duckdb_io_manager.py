"""
DuckDB IO Manager for persisting Dagster asset outputs to DuckDB.

This IO manager writes pandas DataFrames from Dagster assets to DuckDB tables,
allowing DBT models to read from the persisted data.
"""

import duckdb
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


class DuckDBIOManager(ConfigurableIOManager):
    """
    IO Manager that persists Dagster asset outputs to DuckDB tables.
    
    This manager handles writing pandas DataFrames to DuckDB and reading them back.
    It creates tables in the 'raw' schema for ingestion assets, making them
    accessible to DBT models via source definitions.
    
    Attributes:
        database_path: Path to the DuckDB database file
    """
    
    database_path: str = Field(
        description="Path to the DuckDB database file"
    )
    
    def setup_for_execution(self, context: InitResourceContext) -> None:
        """Initialize the IO manager and ensure database directory exists."""
        db_path = Path(self.database_path)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        
        if context:
            context.log.info(f"DuckDB IO Manager initialized with database: {self.database_path}")
    
    def _get_connection(self, read_only: bool = False) -> duckdb.DuckDBPyConnection:
        """
        Get a DuckDB connection.
        
        Args:
            read_only: If True, open connection in read-only mode to avoid lock conflicts
        """
        return duckdb.connect(database=self.database_path, read_only=read_only)
    
    def _get_table_name(self, context: Union[OutputContext, InputContext]) -> str:
        """
        Determine the table name from the asset key.
        
        For ingestion assets, tables are created in the 'raw' schema.
        For DBT assets, tables are in schemas like 'main_staging', 'main_intermediate', 'main_marts'.
        """
        # Get the asset key (e.g., ['customers_raw'] or ['marts', 'account_summary'])
        asset_key = context.asset_key.path
        
        # Check if this is a DBT asset (has multiple path components)
        if len(asset_key) > 1:
            # DBT asset - use the full path with 'main_' prefix
            # e.g., ['marts', 'account_summary'] -> 'main_marts.account_summary'
            schema = f"main_{asset_key[0]}"
            table_name = asset_key[-1]
            return f"{schema}.{table_name}"
        else:
            # Ingestion asset - use 'raw' schema
            table_name = asset_key[-1]
            return f"raw.{table_name}"
    
    def handle_output(self, context: OutputContext, obj: pd.DataFrame) -> None:
        """
        Write a pandas DataFrame to DuckDB.
        
        Args:
            context: Dagster output context containing asset metadata
            obj: pandas DataFrame to persist
        """
        table_name = self._get_table_name(context)
        
        context.log.info(f"Writing {len(obj)} rows to DuckDB table: {table_name}")
        
        conn = self._get_connection()
        try:
            # Ensure the 'raw' schema exists
            conn.execute("CREATE SCHEMA IF NOT EXISTS raw")
            
            # Register the DataFrame as a temporary view
            conn.register('temp_df', obj)
            
            # Create or replace the table from the DataFrame
            conn.execute(f"""
                CREATE OR REPLACE TABLE {table_name} AS 
                SELECT * FROM temp_df
            """)
            
            # Verify the write
            row_count = conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
            context.log.info(f"Successfully wrote {row_count} rows to {table_name}")
        finally:
            conn.close()
    
    def load_input(self, context: InputContext) -> pd.DataFrame:
        """
        Read a pandas DataFrame from DuckDB.
        
        Args:
            context: Dagster input context containing asset metadata
            
        Returns:
            pandas DataFrame loaded from DuckDB
        """
        table_name = self._get_table_name(context)
        
        context.log.info(f"Reading from DuckDB table: {table_name}")
        
        # Use read-only connection to avoid lock conflicts
        conn = self._get_connection(read_only=True)
        try:
            df = conn.execute(f"SELECT * FROM {table_name}").df()
            context.log.info(f"Successfully read {len(df)} rows from {table_name}")
            return df
        finally:
            conn.close()
