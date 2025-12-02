"""
Databricks IO Manager for persisting Dagster asset outputs to Databricks.

This IO manager writes pandas DataFrames from Dagster assets to Databricks Delta tables,
allowing DBT models to read from the persisted data in production.
"""

from typing import Union
import pandas as pd
from dagster import (
    ConfigurableIOManager,
    InputContext,
    OutputContext,
    InitResourceContext,
)
from pydantic import Field


class DatabricksIOManager(ConfigurableIOManager):
    """
    IO Manager that persists Dagster asset outputs to Databricks Delta tables.
    
    This manager handles writing pandas DataFrames to Databricks and reading them back.
    It creates tables in the 'raw' schema for ingestion assets, making them
    accessible to DBT models via source definitions.
    
    Attributes:
        host: Databricks workspace URL
        token: Personal access token for authentication
        http_path: SQL warehouse HTTP path
        catalog: Unity Catalog name
        schema: Schema name within the catalog
    """
    
    host: str = Field(description="Databricks workspace URL")
    token: str = Field(description="Databricks personal access token")
    http_path: str = Field(description="SQL warehouse HTTP path")
    catalog: str = Field(description="Unity Catalog name")
    schema: str = Field(description="Schema name within the catalog")
    
    def setup_for_execution(self, context: InitResourceContext) -> None:
        """Initialize the IO manager and validate databricks-sql-connector is available."""
        try:
            import databricks.sql
        except ImportError:
            raise ImportError(
                "databricks-sql-connector is required for DatabricksIOManager. "
                "Install it with: pip install databricks-sql-connector"
            )
        
        if context:
            context.log.info(
                f"Databricks IO Manager initialized for {self.host} "
                f"(catalog: {self.catalog}, schema: {self.schema})"
            )
    
    def _get_connection(self):
        """Get a Databricks SQL connection."""
        from databricks import sql
        
        return sql.connect(
            server_hostname=self.host,
            http_path=self.http_path,
            access_token=self.token,
            catalog=self.catalog,
            schema=self.schema,
        )
    
    def _get_table_name(self, context: Union[OutputContext, InputContext]) -> str:
        """
        Determine the table name from the asset key.
        
        For ingestion assets, tables are created in the 'raw' schema.
        """
        asset_key = context.asset_key.path
        table_name = asset_key[-1]
        return f"raw.{table_name}"
    
    def handle_output(self, context: OutputContext, obj: pd.DataFrame) -> None:
        """
        Write a pandas DataFrame to Databricks Delta table.
        
        Args:
            context: Dagster output context containing asset metadata
            obj: pandas DataFrame to persist
        """
        table_name = self._get_table_name(context)
        
        context.log.info(f"Writing {len(obj)} rows to Databricks table: {table_name}")
        
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            
            # Ensure the 'raw' schema exists
            cursor.execute(f"CREATE SCHEMA IF NOT EXISTS {self.catalog}.raw")
            
            # Drop table if exists (for simplicity in this demo)
            cursor.execute(f"DROP TABLE IF EXISTS {self.catalog}.{table_name}")
            
            # Create table from DataFrame
            # Convert DataFrame to SQL-compatible format
            columns_def = []
            for col in obj.columns:
                dtype = obj[col].dtype
                if dtype == 'object':
                    sql_type = 'STRING'
                elif dtype == 'int64':
                    sql_type = 'BIGINT'
                elif dtype == 'float64':
                    sql_type = 'DOUBLE'
                else:
                    sql_type = 'STRING'
                columns_def.append(f"`{col}` {sql_type}")
            
            create_table_sql = f"""
                CREATE TABLE {self.catalog}.{table_name} (
                    {', '.join(columns_def)}
                )
                USING DELTA
            """
            cursor.execute(create_table_sql)
            
            # Insert data row by row (for demo purposes)
            # In production, use bulk loading via cloud storage
            for _, row in obj.iterrows():
                values = []
                for val in row:
                    if pd.isna(val):
                        values.append('NULL')
                    elif isinstance(val, str):
                        # Escape single quotes
                        escaped_val = val.replace("'", "''")
                        values.append(f"'{escaped_val}'")
                    else:
                        values.append(str(val))
                
                insert_sql = f"""
                    INSERT INTO {self.catalog}.{table_name}
                    VALUES ({', '.join(values)})
                """
                cursor.execute(insert_sql)
            
            # Verify the write
            cursor.execute(f"SELECT COUNT(*) FROM {self.catalog}.{table_name}")
            row_count = cursor.fetchone()[0]
            context.log.info(f"Successfully wrote {row_count} rows to {table_name}")
            
            cursor.close()
        finally:
            conn.close()
    
    def load_input(self, context: InputContext) -> pd.DataFrame:
        """
        Read a pandas DataFrame from Databricks Delta table.
        
        Args:
            context: Dagster input context containing asset metadata
            
        Returns:
            pandas DataFrame loaded from Databricks
        """
        table_name = self._get_table_name(context)
        
        context.log.info(f"Reading from Databricks table: {table_name}")
        
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(f"SELECT * FROM {self.catalog}.{table_name}")
            
            # Fetch results and column names
            columns = [desc[0] for desc in cursor.description]
            rows = cursor.fetchall()
            
            # Convert to pandas DataFrame
            df = pd.DataFrame(rows, columns=columns)
            context.log.info(f"Successfully read {len(df)} rows from {table_name}")
            
            cursor.close()
            return df
        finally:
            conn.close()
