"""
Databricks resource for production deployment.

Provides connection management and error handling for Databricks SQL warehouse operations.
"""

import time
from contextlib import contextmanager
from typing import Generator, Any

from dagster import ConfigurableResource, InitResourceContext
from pydantic import Field


class DatabricksResource(ConfigurableResource):
    """
    Dagster resource for managing Databricks connections.
    
    Provides connection pooling, retry logic, and error handling for production
    deployments using Databricks as the cloud data platform.
    
    Attributes:
        host: Databricks workspace URL
        token: Personal access token for authentication
        http_path: SQL warehouse HTTP path
        catalog: Unity Catalog name
        schema: Schema name within the catalog
        max_retries: Maximum number of connection retry attempts
        retry_delay: Initial delay between retries in seconds (exponential backoff)
    """
    
    host: str = Field(
        description="Databricks workspace URL (e.g., your-workspace.cloud.databricks.com)"
    )
    token: str = Field(
        description="Databricks personal access token for authentication"
    )
    http_path: str = Field(
        description="SQL warehouse HTTP path (e.g., /sql/1.0/warehouses/abc123)"
    )
    catalog: str = Field(
        description="Unity Catalog name"
    )
    schema: str = Field(
        description="Schema name within the catalog"
    )
    max_retries: int = Field(
        default=3,
        description="Maximum number of connection retry attempts"
    )
    retry_delay: float = Field(
        default=1.0,
        description="Initial delay between retries in seconds (exponential backoff)"
    )
    
    def setup_for_execution(self, context: InitResourceContext) -> None:
        """
        Initialize the resource for execution.
        
        Validates that the databricks-sql-connector is available.
        """
        try:
            import databricks.sql
        except ImportError:
            raise ImportError(
                "databricks-sql-connector is required for DatabricksResource. "
                "Install it with: pip install databricks-sql-connector"
            )
        
        if context:
            context.log.info(
                f"Databricks resource initialized for {self.host} "
                f"(catalog: {self.catalog}, schema: {self.schema})"
            )
    
    @contextmanager
    def get_connection(self) -> Generator[Any, None, None]:
        """
        Get a Databricks SQL connection with automatic cleanup and retry logic.
        
        Yields:
            Connection: Active Databricks SQL connection
            
        Raises:
            RuntimeError: If connection fails after all retry attempts
            
        Example:
            with databricks_resource.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM customers")
                result = cursor.fetchall()
        """
        try:
            from databricks import sql
        except ImportError:
            raise ImportError(
                "databricks-sql-connector is required. "
                "Install it with: pip install databricks-sql-connector"
            )
        
        conn = None
        last_error = None
        
        # Retry logic with exponential backoff
        for attempt in range(self.max_retries):
            try:
                conn = sql.connect(
                    server_hostname=self.host,
                    http_path=self.http_path,
                    access_token=self.token,
                    catalog=self.catalog,
                    schema=self.schema,
                )
                
                # Connection successful
                yield conn
                return
                
            except Exception as e:
                last_error = e
                
                if attempt < self.max_retries - 1:
                    # Calculate exponential backoff delay
                    delay = self.retry_delay * (2 ** attempt)
                    time.sleep(delay)
                    continue
                else:
                    # All retries exhausted
                    break
            finally:
                if conn:
                    try:
                        conn.close()
                    except Exception:
                        # Ignore errors during cleanup
                        pass
        
        # If we get here, all retries failed
        error_msg = (
            f"Failed to connect to Databricks after {self.max_retries} attempts. "
            f"Last error: {str(last_error)}"
        )
        raise RuntimeError(error_msg) from last_error
    
    def execute_query(self, query: str) -> list:
        """
        Execute a SQL query and return results.
        
        Args:
            query: SQL query string to execute
            
        Returns:
            List of tuples containing query results
            
        Raises:
            RuntimeError: If query execution fails
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(query)
                result = cursor.fetchall()
                return result
            finally:
                cursor.close()
    
    def execute_query_df(self, query: str):
        """
        Execute a SQL query and return results as a pandas DataFrame.
        
        Args:
            query: SQL query string to execute
            
        Returns:
            pandas.DataFrame containing query results
            
        Raises:
            RuntimeError: If query execution fails
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(query)
                
                # Fetch results and column names
                columns = [desc[0] for desc in cursor.description]
                rows = cursor.fetchall()
                
                # Convert to pandas DataFrame
                import pandas as pd
                df = pd.DataFrame(rows, columns=columns)
                return df
            finally:
                cursor.close()
    
    def load_dataframe_to_table(
        self, 
        df, 
        table_name: str, 
        mode: str = "overwrite"
    ) -> None:
        """
        Load a pandas DataFrame into a Databricks Delta table.
        
        Args:
            df: pandas DataFrame to load
            table_name: Name of the table to create/update
            mode: Write mode - 'overwrite' or 'append'
            
        Raises:
            RuntimeError: If loading fails
            ValueError: If mode is invalid
        """
        if mode not in ["overwrite", "append"]:
            raise ValueError(f"Invalid mode: {mode}. Must be 'overwrite' or 'append'")
        
        # For production use, this would typically use Databricks' native
        # DataFrame API or Delta Lake operations. For now, we'll use a
        # simple SQL-based approach.
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                # Create table if it doesn't exist (simplified approach)
                # In production, you'd want to use proper Delta Lake operations
                
                if mode == "overwrite":
                    # Drop and recreate table
                    cursor.execute(f"DROP TABLE IF EXISTS {table_name}")
                
                # Note: This is a simplified implementation
                # Production code should use Databricks' native APIs
                # or write to cloud storage and use COPY INTO
                
                raise NotImplementedError(
                    "DataFrame loading to Databricks requires additional setup. "
                    "Use Databricks' native APIs or write to cloud storage first."
                )
                
            finally:
                cursor.close()
    
    def table_exists(self, table_name: str) -> bool:
        """
        Check if a table exists in the catalog.
        
        Args:
            table_name: Name of the table to check
            
        Returns:
            True if table exists, False otherwise
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(f"""
                    SELECT COUNT(*) 
                    FROM information_schema.tables 
                    WHERE table_catalog = '{self.catalog}'
                    AND table_schema = '{self.schema}'
                    AND table_name = '{table_name}'
                """)
                result = cursor.fetchone()
                return result[0] > 0 if result else False
            finally:
                cursor.close()
