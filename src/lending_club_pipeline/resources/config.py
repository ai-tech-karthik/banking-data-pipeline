"""
Configuration management for the LendingClub data pipeline.

This module provides environment-driven configuration that allows the same code
to run in development (DuckDB) and production (Databricks) without changes.
"""

import os
from dataclasses import dataclass
from typing import Literal


@dataclass
class DataPlatformConfig:
    """
    Configuration for the data platform.
    
    Loads all configuration from environment variables to support
    different deployment environments (dev, staging, prod).
    """
    
    # Environment settings
    environment: Literal["dev", "staging", "prod"]
    database_type: Literal["duckdb", "databricks"]
    
    # DBT configuration
    dbt_target: str
    
    # Local paths
    output_path: str
    duckdb_path: str
    
    # Databricks configuration (optional, only for prod)
    databricks_host: str | None = None
    databricks_token: str | None = None
    databricks_catalog: str | None = None
    databricks_schema: str | None = None
    databricks_http_path: str | None = None
    
    @classmethod
    def from_env(cls) -> "DataPlatformConfig":
        """
        Load configuration from environment variables.
        
        Returns:
            DataPlatformConfig: Validated configuration object
            
        Raises:
            ValueError: If required environment variables are missing or invalid
        """
        # Load required environment variables
        environment = os.getenv("ENVIRONMENT", "dev")
        database_type = os.getenv("DATABASE_TYPE", "duckdb")
        dbt_target = os.getenv("DBT_TARGET", "dev")
        output_path = os.getenv("OUTPUT_PATH", "data/outputs")
        duckdb_path = os.getenv("DUCKDB_PATH", "data/duckdb/lending_club.duckdb")
        
        # Validate environment
        if environment not in ["dev", "staging", "prod"]:
            raise ValueError(
                f"Invalid ENVIRONMENT: {environment}. "
                "Must be one of: dev, staging, prod"
            )
        
        # Validate database_type
        if database_type not in ["duckdb", "databricks"]:
            raise ValueError(
                f"Invalid DATABASE_TYPE: {database_type}. "
                "Must be one of: duckdb, databricks"
            )
        
        # Load optional Databricks configuration
        databricks_host = os.getenv("DATABRICKS_HOST")
        databricks_token = os.getenv("DATABRICKS_TOKEN")
        databricks_catalog = os.getenv("DATABRICKS_CATALOG")
        databricks_schema = os.getenv("DATABRICKS_SCHEMA")
        databricks_http_path = os.getenv("DATABRICKS_HTTP_PATH")
        
        # Validate Databricks configuration if using Databricks
        if database_type == "databricks":
            missing_fields = []
            if not databricks_host:
                missing_fields.append("DATABRICKS_HOST")
            if not databricks_token:
                missing_fields.append("DATABRICKS_TOKEN")
            if not databricks_catalog:
                missing_fields.append("DATABRICKS_CATALOG")
            if not databricks_schema:
                missing_fields.append("DATABRICKS_SCHEMA")
            if not databricks_http_path:
                missing_fields.append("DATABRICKS_HTTP_PATH")
            
            if missing_fields:
                raise ValueError(
                    f"DATABASE_TYPE is 'databricks' but missing required fields: "
                    f"{', '.join(missing_fields)}"
                )
        
        return cls(
            environment=environment,  # type: ignore
            database_type=database_type,  # type: ignore
            dbt_target=dbt_target,
            output_path=output_path,
            duckdb_path=duckdb_path,
            databricks_host=databricks_host,
            databricks_token=databricks_token,
            databricks_catalog=databricks_catalog,
            databricks_schema=databricks_schema,
            databricks_http_path=databricks_http_path,
        )
    
    def is_local(self) -> bool:
        """Check if running in local development mode."""
        return self.database_type == "duckdb"
    
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return self.environment == "prod"
    
    def get_database_connection_string(self) -> str:
        """
        Get the appropriate database connection string based on configuration.
        
        Returns:
            str: Connection string for DuckDB or Databricks
        """
        if self.database_type == "duckdb":
            return f"duckdb:///{self.duckdb_path}"
        else:
            # Databricks connection string format
            return (
                f"databricks://token:{self.databricks_token}@{self.databricks_host}?"
                f"http_path={self.databricks_http_path}&"
                f"catalog={self.databricks_catalog}&"
                f"schema={self.databricks_schema}"
            )
