"""
DuckDB resource for local development.

Provides connection management and error handling for DuckDB database operations.
"""

import duckdb
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Generator

from dagster import ConfigurableResource, InitResourceContext
from pydantic import Field


class DuckDBResource(ConfigurableResource):
    """
    Dagster resource for managing DuckDB connections.
    
    Provides connection pooling and error handling for local development
    using DuckDB as the OLAP database backend.
    
    Attributes:
        database_path: Path to the DuckDB database file
        read_only: Whether to open the database in read-only mode
    """
    
    database_path: str = Field(
        description="Path to the DuckDB database file"
    )
    read_only: bool = Field(
        default=False,
        description="Whether to open the database in read-only mode"
    )
    
    def setup_for_execution(self, context: InitResourceContext) -> None:
        """
        Initialize the resource for execution.
        
        Creates the database directory if it doesn't exist.
        """
        db_path = Path(self.database_path)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        
        if context:
            context.log.info(f"DuckDB resource initialized with database: {self.database_path}")
    
    @contextmanager
    def get_connection(self, max_retries: int = 3, retry_delay: float = 1.0) -> Generator[duckdb.DuckDBPyConnection, None, None]:
        """
        Get a DuckDB connection with automatic cleanup and retry logic.
        
        Args:
            max_retries: Maximum number of connection retry attempts
            retry_delay: Initial delay between retries in seconds (exponential backoff)
        
        Yields:
            DuckDBPyConnection: Active database connection
            
        Raises:
            duckdb.Error: If connection fails after all retry attempts
            
        Example:
            with duckdb_resource.get_connection() as conn:
                result = conn.execute("SELECT * FROM customers").fetchall()
        """
        conn = None
        last_error = None
        
        for attempt in range(max_retries):
            try:
                # Create connection to DuckDB
                conn = duckdb.connect(
                    database=self.database_path,
                    read_only=self.read_only
                )
                
                # Configure connection settings for optimal performance
                conn.execute("SET memory_limit='4GB'")
                conn.execute("SET threads=4")
                
                yield conn
                return
                
            except duckdb.Error as e:
                last_error = e
                error_msg = str(e).lower()
                
                # Check if this is a transient error (lock, busy, etc.)
                is_transient = any(pattern in error_msg for pattern in [
                    'lock', 'busy', 'timeout', 'temporary'
                ])
                
                if is_transient and attempt < max_retries - 1:
                    # Retry with exponential backoff
                    wait_time = retry_delay * (2 ** attempt)
                    time.sleep(wait_time)
                    continue
                else:
                    # Non-transient error or max retries reached
                    error_msg = f"DuckDB error: {str(e)}"
                    raise duckdb.Error(error_msg) from e
                    
            except Exception as e:
                last_error = e
                error_msg = f"Unexpected error with DuckDB connection: {str(e)}"
                raise RuntimeError(error_msg) from e
            finally:
                if conn:
                    try:
                        conn.close()
                    except Exception:
                        # Ignore errors during cleanup
                        pass
        
        # If we get here, all retries failed
        if last_error:
            raise last_error
    
    def execute_query(self, query: str) -> list:
        """
        Execute a SQL query and return results.
        
        Args:
            query: SQL query string to execute
            
        Returns:
            List of tuples containing query results
            
        Raises:
            duckdb.Error: If query execution fails
        """
        with self.get_connection() as conn:
            result = conn.execute(query).fetchall()
            return result
    
    def execute_query_df(self, query: str):
        """
        Execute a SQL query and return results as a pandas DataFrame.
        
        Args:
            query: SQL query string to execute
            
        Returns:
            pandas.DataFrame containing query results
            
        Raises:
            duckdb.Error: If query execution fails
        """
        with self.get_connection() as conn:
            result = conn.execute(query).df()
            return result
    
    def load_csv_to_table(self, csv_path: str, table_name: str) -> None:
        """
        Load a CSV file into a DuckDB table.
        
        Args:
            csv_path: Path to the CSV file
            table_name: Name of the table to create
            
        Raises:
            duckdb.Error: If loading fails
            FileNotFoundError: If CSV file doesn't exist
        """
        csv_file = Path(csv_path)
        if not csv_file.exists():
            raise FileNotFoundError(f"CSV file not found: {csv_path}")
        
        with self.get_connection() as conn:
            # Create or replace table from CSV
            conn.execute(f"""
                CREATE OR REPLACE TABLE {table_name} AS 
                SELECT * FROM read_csv_auto('{csv_path}')
            """)
    
    def table_exists(self, table_name: str) -> bool:
        """
        Check if a table exists in the database.
        
        Args:
            table_name: Name of the table to check
            
        Returns:
            True if table exists, False otherwise
        """
        with self.get_connection() as conn:
            result = conn.execute(f"""
                SELECT COUNT(*) 
                FROM information_schema.tables 
                WHERE table_name = '{table_name}'
            """).fetchone()
            return result[0] > 0 if result else False
