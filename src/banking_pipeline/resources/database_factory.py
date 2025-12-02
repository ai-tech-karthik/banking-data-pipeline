"""
Database resource factory.

Provides a factory function that returns the appropriate database resource
based on the DATABASE_TYPE configuration.
"""

from typing import Union

from dagster import ConfigurableResource

from .config import DataPlatformConfig
from .duckdb_resource import DuckDBResource
from .databricks_resource import DatabricksResource


def get_database_resource(
    config: DataPlatformConfig,
) -> Union[DuckDBResource, DatabricksResource]:
    """
    Factory function that returns the appropriate database resource.
    
    Based on the DATABASE_TYPE configuration, returns either a DuckDBResource
    (for local development) or a DatabricksResource (for production).
    
    Args:
        config: DataPlatformConfig instance with environment settings
        
    Returns:
        DuckDBResource or DatabricksResource based on database_type
        
    Raises:
        ValueError: If database_type is not supported
        
    Example:
        config = DataPlatformConfig.from_env()
        db_resource = get_database_resource(config)
        
        with db_resource.get_connection() as conn:
            # Use connection...
    """
    if config.database_type == "duckdb":
        return DuckDBResource(
            database_path=config.duckdb_path,
            read_only=False,
        )
    
    elif config.database_type == "databricks":
        # Validate that Databricks configuration is present
        if not all([
            config.databricks_host,
            config.databricks_token,
            config.databricks_http_path,
            config.databricks_catalog,
            config.databricks_schema,
        ]):
            raise ValueError(
                "Databricks configuration is incomplete. "
                "Ensure all DATABRICKS_* environment variables are set."
            )
        
        return DatabricksResource(
            host=config.databricks_host,  # type: ignore
            token=config.databricks_token,  # type: ignore
            http_path=config.databricks_http_path,  # type: ignore
            catalog=config.databricks_catalog,  # type: ignore
            schema=config.databricks_schema,  # type: ignore
            max_retries=3,
            retry_delay=1.0,
        )
    
    else:
        raise ValueError(
            f"Unsupported database_type: {config.database_type}. "
            "Must be 'duckdb' or 'databricks'."
        )


def create_database_resource_from_env() -> Union[DuckDBResource, DatabricksResource]:
    """
    Convenience function to create database resource from environment variables.
    
    Loads configuration from environment and returns the appropriate resource.
    
    Returns:
        DuckDBResource or DatabricksResource based on DATABASE_TYPE env var
        
    Raises:
        ValueError: If configuration is invalid or database_type is not supported
        
    Example:
        # In Dagster definitions
        db_resource = create_database_resource_from_env()
    """
    config = DataPlatformConfig.from_env()
    return get_database_resource(config)
