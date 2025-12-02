"""
Output assets for exporting processed data to various formats.

This module contains assets that export the final account_summary mart
to different output formats (CSV, Parquet) and destinations (local files, Databricks).
"""
import os
import time
from datetime import datetime
from pathlib import Path

import pandas as pd
from dagster import (
    AssetExecutionContext, 
    AssetIn, 
    asset, 
    Output, 
    MetadataValue,
)
from dagster_dbt import get_asset_key_for_model

from .dbt_assets import dbt_transformations
from ..resources.databricks_resource import DatabricksResource
from ..resources.data_quality import DataQualityMonitor, TestResult


@asset(
    group_name="outputs",
    tags={
        "layer": "output", 
        "format": "csv",
        "destination": "local",
        "domain": "analytics",
        "sla": "daily",
        "priority": "medium",
    },
    description="Export account summary to CSV format for downstream consumption. This asset exports the final account summary with interest calculations to a CSV file for use by BI tools and reporting systems. Uses standardized column names following snake_case conventions.",
    metadata={
        "owner": "analytics-team",
        "format": "csv",
        "encoding": "utf-8",
        "destination": "data/outputs/",
        "data_classification": "internal",
        "consumers": ["business_intelligence", "reporting"],
        "expected_lag_hours": 26,
        "business_purpose": "Provide account summary data for business reporting and analysis",
        "upstream_dependencies": "account_summary mart (DBT incremental)",
        "output_schema": "account_id, customer_id, original_balance_amount, interest_rate_pct, annual_interest_amount, new_balance_amount, calculated_at",
        "naming_convention": "snake_case with descriptive suffixes (_amount, _pct, _at)",
    },
    owners=["analytics-team@company.com"],
    deps=[get_asset_key_for_model([dbt_transformations], "account_summary")],
)
def account_summary_csv(
    context: AssetExecutionContext,
) -> None:
    """
    Export the account_summary mart to a CSV file.
    
    This asset reads the account_summary table from the database and exports it
    to data/outputs/account_summary.csv with UTF-8 encoding.
    
    Args:
        context: Dagster execution context for logging and metadata
        
    Returns:
        Output containing the file path with metadata about the export
        
    Raises:
        OSError: If there are issues writing the file (e.g., disk space)
    """
    # Check database type to determine where to read from
    database_type = os.getenv("DATABASE_TYPE", "duckdb")
    
    if database_type == "databricks":
        # Read from Databricks
        from databricks import sql
        
        host = os.getenv("DATABRICKS_HOST")
        token = os.getenv("DATABRICKS_TOKEN")
        http_path = os.getenv("DATABRICKS_HTTP_PATH")
        catalog = os.getenv("DATABRICKS_CATALOG", "workspace")
        schema = os.getenv("DATABRICKS_SCHEMA", "default")
        
        context.log.info(f"Reading account_summary from Databricks: {catalog}.{schema}_marts.account_summary")
        
        with sql.connect(
            server_hostname=host,
            http_path=http_path,
            access_token=token,
        ) as conn:
            with conn.cursor() as cursor:
                cursor.execute(f"SELECT * FROM {catalog}.{schema}_marts.account_summary")
                account_summary = cursor.fetchall_arrow().to_pandas()
                context.log.info(f"Loaded {len(account_summary)} rows from account_summary table")
    else:
        # Read from DuckDB
        import duckdb
        
        duckdb_path = os.getenv("DUCKDB_PATH", "data/duckdb/lending_club.duckdb")
        context.log.info(f"Reading account_summary from DuckDB: {duckdb_path}")
        
        conn = duckdb.connect(database=duckdb_path, read_only=True)
        try:
            account_summary = conn.execute("SELECT * FROM main_marts.account_summary").df()
            context.log.info(f"Loaded {len(account_summary)} rows from account_summary table")
        finally:
            conn.close()
    
    # Define output path
    output_dir = Path("data/outputs")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    output_path = output_dir / "account_summary.csv"
    
    context.log.info(
        f"Exporting {len(account_summary)} rows to {output_path} "
        f"(columns: {list(account_summary.columns)})"
    )
    
    try:
        # Export to CSV with UTF-8 encoding
        account_summary.to_csv(
            output_path,
            index=False,
            encoding="utf-8",
        )
        
        # Validate that the file was created successfully
        if not output_path.exists():
            raise OSError(f"Output file was not created: {output_path}")
        
        # Get file size for metadata
        file_size_bytes = output_path.stat().st_size
        file_size_kb = file_size_bytes / 1024
        
        # Validate file is not empty
        if file_size_bytes == 0:
            raise OSError(f"Output file is empty: {output_path}")
        
        # Log success with file details
        context.log.info(
            f"Successfully exported account summary to {output_path}"
        )
        context.log.info(
            f"Output file details - Rows: {len(account_summary)}, "
            f"Columns: {len(account_summary.columns)}, "
            f"Size: {file_size_kb:.2f} KB ({file_size_bytes:,} bytes)"
        )
        
        # Log metadata (no return value needed for side-effect assets)
        context.add_output_metadata({
            "row_count": len(account_summary),
            "column_count": len(account_summary.columns),
            "file_path": str(output_path),
            "file_size_kb": round(file_size_kb, 2),
            "file_size_bytes": file_size_bytes,
            "encoding": "utf-8",
            "execution_timestamp": datetime.now().isoformat(),
            "preview": MetadataValue.md(account_summary.head(10).to_markdown()),
        })
        
    except OSError as e:
        context.log.error(
            f"Failed to write CSV file to {output_path}: {str(e)}. "
            "This may be due to insufficient disk space or permission issues."
        )
        raise OSError(
            f"Insufficient disk space or permission error writing to {output_path}: {str(e)}"
        ) from e


@asset(
    group_name="outputs",
    tags={
        "layer": "output", 
        "format": "parquet",
        "destination": "local",
        "domain": "analytics",
        "sla": "daily",
        "priority": "medium",
    },
    description="Export account summary to Parquet format with Snappy compression. This asset exports the final account summary with interest calculations to a Parquet file optimized for data science and ML workflows. Uses standardized column names following snake_case conventions.",
    metadata={
        "owner": "analytics-team",
        "format": "parquet",
        "compression": "snappy",
        "destination": "data/outputs/",
        "data_classification": "internal",
        "consumers": ["data_science", "ml_pipelines"],
        "expected_lag_hours": 26,
        "business_purpose": "Provide account summary data for data science and ML model training",
        "upstream_dependencies": "account_summary mart (DBT incremental)",
        "output_schema": "account_id, customer_id, original_balance_amount, interest_rate_pct, annual_interest_amount, new_balance_amount, calculated_at",
        "naming_convention": "snake_case with descriptive suffixes (_amount, _pct, _at)",
        "performance_notes": "Snappy compression provides good balance of compression ratio and read speed",
    },
    owners=["analytics-team@company.com"],
    deps=[get_asset_key_for_model([dbt_transformations], "account_summary")],
)
def account_summary_parquet(
    context: AssetExecutionContext,
) -> None:
    """
    Export the account_summary mart to a Parquet file with Snappy compression.
    
    This asset reads the account_summary table from the database and exports it
    to data/outputs/account_summary.parquet with Snappy compression for efficient
    storage and fast read performance.
    
    Args:
        context: Dagster execution context for logging and metadata
        
    Returns:
        Output containing the file path with metadata about the export
        
    Raises:
        OSError: If there are issues writing the file (e.g., disk space)
    """
    # Check database type to determine where to read from
    database_type = os.getenv("DATABASE_TYPE", "duckdb")
    
    if database_type == "databricks":
        # Read from Databricks
        from databricks import sql
        
        host = os.getenv("DATABRICKS_HOST")
        token = os.getenv("DATABRICKS_TOKEN")
        http_path = os.getenv("DATABRICKS_HTTP_PATH")
        catalog = os.getenv("DATABRICKS_CATALOG", "workspace")
        schema = os.getenv("DATABRICKS_SCHEMA", "default")
        
        context.log.info(f"Reading account_summary from Databricks: {catalog}.{schema}_marts.account_summary")
        
        with sql.connect(
            server_hostname=host,
            http_path=http_path,
            access_token=token,
        ) as conn:
            with conn.cursor() as cursor:
                cursor.execute(f"SELECT * FROM {catalog}.{schema}_marts.account_summary")
                account_summary = cursor.fetchall_arrow().to_pandas()
                context.log.info(f"Loaded {len(account_summary)} rows from account_summary table")
    else:
        # Read from DuckDB
        import duckdb
        
        duckdb_path = os.getenv("DUCKDB_PATH", "data/duckdb/lending_club.duckdb")
        context.log.info(f"Reading account_summary from DuckDB: {duckdb_path}")
        
        conn = duckdb.connect(database=duckdb_path, read_only=True)
        try:
            account_summary = conn.execute("SELECT * FROM main_marts.account_summary").df()
            context.log.info(f"Loaded {len(account_summary)} rows from account_summary table")
        finally:
            conn.close()
    
    # Define output path
    output_dir = Path("data/outputs")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    output_path = output_dir / "account_summary.parquet"
    
    context.log.info(
        f"Exporting {len(account_summary)} rows to {output_path} "
        f"(columns: {list(account_summary.columns)})"
    )
    
    try:
        # Export to Parquet with Snappy compression
        account_summary.to_parquet(
            output_path,
            index=False,
            compression="snappy",
            engine="pyarrow",
        )
        
        # Validate that the file was created successfully
        if not output_path.exists():
            raise OSError(f"Output file was not created: {output_path}")
        
        # Get file size for metadata
        file_size_bytes = output_path.stat().st_size
        file_size_kb = file_size_bytes / 1024
        
        # Validate file is not empty
        if file_size_bytes == 0:
            raise OSError(f"Output file is empty: {output_path}")
        
        # Log success with file details
        context.log.info(
            f"Successfully exported account summary to {output_path}"
        )
        context.log.info(
            f"Output file details - Rows: {len(account_summary)}, "
            f"Columns: {len(account_summary.columns)}, "
            f"Size: {file_size_kb:.2f} KB ({file_size_bytes:,} bytes)"
        )
        
        # Log metadata (no return value needed for side-effect assets)
        context.add_output_metadata({
            "row_count": len(account_summary),
            "column_count": len(account_summary.columns),
            "file_path": str(output_path),
            "file_size_kb": round(file_size_kb, 2),
            "file_size_bytes": file_size_bytes,
            "compression": "snappy",
            "engine": "pyarrow",
            "execution_timestamp": datetime.now().isoformat(),
            "preview": MetadataValue.md(account_summary.head(10).to_markdown()),
        })
        
    except OSError as e:
        context.log.error(
            f"Failed to write Parquet file to {output_path}: {str(e)}. "
            "This may be due to insufficient disk space or permission issues."
        )
        raise OSError(
            f"Insufficient disk space or permission error writing to {output_path}: {str(e)}"
        ) from e


@asset(
    group_name="outputs",
    tags={
        "layer": "output", 
        "destination": "databricks", 
        "environment": "production",
        "format": "delta",
        "domain": "analytics",
        "sla": "daily",
        "priority": "high",
    },
    description="Load account summary to Databricks Delta table (production only) with retry logic. This asset loads the final account summary to Databricks for enterprise-wide consumption via SQL, BI tools, and dashboards. Only executes when DATABASE_TYPE=databricks. Uses standardized column names following snake_case conventions.",
    metadata={
        "owner": "data-engineering-team",
        "format": "delta",
        "destination": "databricks",
        "data_classification": "internal",
        "consumers": ["databricks_sql", "powerbi", "tableau"],
        "retry_policy": "exponential_backoff",
        "max_retries": 3,
        "expected_lag_hours": 26,
        "business_purpose": "Provide account summary data for enterprise BI and analytics",
        "upstream_dependencies": "account_summary mart (DBT incremental)",
        "output_schema": "account_id, customer_id, original_balance_amount, interest_rate_pct, annual_interest_amount, new_balance_amount, calculated_at",
        "naming_convention": "snake_case with descriptive suffixes (_amount, _pct, _at)",
        "execution_condition": "Only runs when DATABASE_TYPE=databricks",
        "performance_notes": "Uses batch inserts with retry logic for reliability",
    },
    owners=["data-engineering-team@company.com", "analytics-team@company.com"],
    deps=[get_asset_key_for_model([dbt_transformations], "account_summary")],
    io_manager_key=None,  # Don't use IO manager - this asset writes directly to Databricks
)
def account_summary_to_databricks(
    context: AssetExecutionContext,
    databricks: DatabricksResource,
) -> None:
    """
    Load the account_summary mart to a Databricks Delta table.
    
    This asset only executes in production environments where DATABASE_TYPE=databricks.
    In development environments (DATABASE_TYPE=duckdb), the asset is skipped.
    
    The asset includes retry logic with exponential backoff to handle transient
    connection errors when communicating with Databricks.
    
    Args:
        context: Dagster execution context for logging and metadata
        databricks: DatabricksResource for connecting to Databricks
        
    Returns:
        Output containing the table name with metadata about the load operation
        
    Raises:
        RuntimeError: If loading fails after all retry attempts
    """
    # Check if we should skip this asset based on DATABASE_TYPE
    database_type = os.getenv("DATABASE_TYPE", "duckdb")
    
    if database_type != "databricks":
        context.log.info(
            f"Skipping Databricks output - DATABASE_TYPE is '{database_type}'. "
            "This asset only runs when DATABASE_TYPE=databricks"
        )
        context.add_output_metadata({
            "status": "skipped",
            "reason": f"DATABASE_TYPE={database_type}",
            "execution_timestamp": datetime.now().isoformat(),
        })
        return
    
    # Read from Databricks
    from databricks import sql
    
    host = os.getenv("DATABRICKS_HOST")
    token = os.getenv("DATABRICKS_TOKEN")
    http_path = os.getenv("DATABRICKS_HTTP_PATH")
    catalog = os.getenv("DATABRICKS_CATALOG", "workspace")
    schema = os.getenv("DATABRICKS_SCHEMA", "default")
    
    # DBT creates tables in schema_layer format (e.g., default_marts)
    dbt_schema = f"{schema}_marts"
    
    context.log.info(f"Reading account_summary from Databricks: {catalog}.{dbt_schema}.account_summary")
    
    with sql.connect(
        server_hostname=host,
        http_path=http_path,
        access_token=token,
    ) as conn:
        with conn.cursor() as cursor:
            cursor.execute(f"SELECT * FROM {catalog}.{dbt_schema}.account_summary")
            account_summary = cursor.fetchall_arrow().to_pandas()
            context.log.info(f"Loaded {len(account_summary)} rows from account_summary table")
    
    # Define table name
    # Write to the default schema (not the _marts schema)
    table_name = "account_summary"
    target_schema = databricks.schema  # e.g., "default"
    full_table_name = f"{databricks.catalog}.{target_schema}.{table_name}"
    
    context.log.info(
        f"Loading {len(account_summary)} rows to Databricks table {full_table_name}"
    )
    
    # Retry configuration
    max_retries = 3
    retry_delay = 1.0  # Initial delay in seconds
    last_error = None
    
    # Retry loop with exponential backoff
    for attempt in range(max_retries):
        try:
            context.log.info(
                f"Attempt {attempt + 1}/{max_retries} to load data to Databricks"
            )
            
            # Get connection and load data
            with databricks.get_connection() as conn:
                cursor = conn.cursor()
                
                try:
                    # Create schema if it doesn't exist
                    context.log.info(f"Creating schema if not exists: {databricks.catalog}.{target_schema}")
                    cursor.execute(f"CREATE SCHEMA IF NOT EXISTS {databricks.catalog}.{target_schema}")
                    
                    # Create table if it doesn't exist
                    # First, generate CREATE TABLE statement from DataFrame schema
                    column_defs = []
                    for col_name, dtype in account_summary.dtypes.items():
                        # Map pandas dtypes to SQL types
                        if dtype == 'int64':
                            sql_type = 'BIGINT'
                        elif dtype == 'float64':
                            sql_type = 'DOUBLE'
                        elif dtype == 'object':
                            sql_type = 'STRING'
                        else:
                            sql_type = 'STRING'  # Default fallback
                        
                        column_defs.append(f"{col_name} {sql_type}")
                    
                    create_table_sql = f"""
                        CREATE TABLE IF NOT EXISTS {full_table_name} (
                            {', '.join(column_defs)}
                        )
                        USING DELTA
                    """
                    
                    context.log.info(f"Creating table if not exists: {full_table_name}")
                    cursor.execute(create_table_sql)
                    
                    # Truncate table for overwrite mode
                    context.log.info(f"Truncating table: {full_table_name}")
                    cursor.execute(f"TRUNCATE TABLE {full_table_name}")
                    
                    # Insert data in batches
                    batch_size = 1000
                    total_rows = len(account_summary)
                    
                    for i in range(0, total_rows, batch_size):
                        batch = account_summary.iloc[i:i + batch_size]
                        
                        # Generate INSERT statement
                        values_list = []
                        for _, row in batch.iterrows():
                            values = []
                            for val in row:
                                if pd.isna(val):
                                    values.append('NULL')
                                elif isinstance(val, pd.Timestamp):
                                    # Format timestamp as SQL TIMESTAMP literal
                                    timestamp_str = val.strftime('%Y-%m-%d %H:%M:%S.%f')
                                    values.append(f"TIMESTAMP '{timestamp_str}'")
                                elif isinstance(val, str):
                                    # Escape single quotes and quote strings
                                    escaped_val = val.replace("'", "''")
                                    values.append(f"'{escaped_val}'")
                                elif isinstance(val, (int, float)):
                                    values.append(str(val))
                                else:
                                    # For any other type, convert to string and quote
                                    escaped_val = str(val).replace("'", "''")
                                    values.append(f"'{escaped_val}'")
                            values_list.append(f"({', '.join(values)})")
                        
                        insert_sql = f"""
                            INSERT INTO {full_table_name}
                            VALUES {', '.join(values_list)}
                        """
                        
                        cursor.execute(insert_sql)
                        
                        context.log.info(
                            f"Inserted batch {i // batch_size + 1} "
                            f"({min(i + batch_size, total_rows)}/{total_rows} rows)"
                        )
                    
                    # Verify row count
                    cursor.execute(f"SELECT COUNT(*) FROM {full_table_name}")
                    result = cursor.fetchone()
                    loaded_rows = result[0] if result else 0
                    
                    # Validate that all rows were loaded
                    if loaded_rows != total_rows:
                        context.log.warning(
                            f"Row count mismatch: Expected {total_rows}, "
                            f"but found {loaded_rows} in table"
                        )
                    
                    context.log.info(
                        f"Successfully loaded data to {full_table_name}"
                    )
                    context.log.info(
                        f"Table details - Rows: {loaded_rows}, "
                        f"Columns: {len(account_summary.columns)}, "
                        f"Catalog: {databricks.catalog}, Schema: {target_schema}"
                    )
                    
                    # Success - add metadata and return
                    context.add_output_metadata({
                        "table_name": full_table_name,
                        "row_count": loaded_rows,
                        "column_count": len(account_summary.columns),
                        "catalog": databricks.catalog,
                        "schema": target_schema,
                        "execution_timestamp": datetime.now().isoformat(),
                        "attempts": attempt + 1,
                        "preview": MetadataValue.md(
                            account_summary.head(10).to_markdown()
                        ),
                    })
                    return
                    
                finally:
                    cursor.close()
                    
        except Exception as e:
            last_error = e
            context.log.warning(
                f"Attempt {attempt + 1}/{max_retries} failed: {str(e)}"
            )
            
            if attempt < max_retries - 1:
                # Calculate exponential backoff delay
                delay = retry_delay * (2 ** attempt)
                context.log.info(f"Retrying in {delay} seconds...")
                time.sleep(delay)
            else:
                # All retries exhausted
                context.log.error(
                    f"Failed to load data to Databricks after {max_retries} attempts"
                )
                error_msg = (
                    f"Failed to load data to Databricks table {full_table_name} "
                    f"after {max_retries} attempts. Last error: {str(last_error)}"
                )
                raise RuntimeError(error_msg) from last_error
    
    # This should never be reached, but just in case
    raise RuntimeError("Unexpected error in retry loop")



@asset(
    group_name="outputs",
    tags={
        "layer": "output", 
        "format": "csv",
        "destination": "local",
        "domain": "analytics",
        "sla": "daily",
        "priority": "medium",
    },
    description="Export customer profile to CSV format for downstream consumption. This asset exports customer-level aggregated analytics including total accounts, balances, and interest projections to a CSV file for use by BI tools and reporting systems.",
    metadata={
        "owner": "analytics-team",
        "format": "csv",
        "encoding": "utf-8",
        "destination": "data/outputs/",
        "data_classification": "internal",
        "consumers": ["business_intelligence", "reporting", "customer_analytics"],
        "expected_lag_hours": 26,
        "business_purpose": "Provide customer-level aggregated data for customer analytics and reporting",
        "upstream_dependencies": "customer_profile mart (DBT incremental)",
        "output_schema": "customer_id, customer_name, has_loan_flag, total_accounts_count, total_balance_amount, total_annual_interest_amount, calculated_at",
        "naming_convention": "snake_case with descriptive suffixes (_flag, _count, _amount, _at)",
    },
    owners=["analytics-team@company.com"],
    deps=[get_asset_key_for_model([dbt_transformations], "customer_profile")],
)
def customer_profile_csv(
    context: AssetExecutionContext,
) -> None:
    """
    Export the customer_profile mart to a CSV file.
    
    This asset reads the customer_profile table from the database and exports it
    to data/outputs/customer_profile.csv with UTF-8 encoding.
    
    Args:
        context: Dagster execution context for logging and metadata
        
    Returns:
        None (side-effect asset that writes file)
        
    Raises:
        OSError: If there are issues writing the file (e.g., disk space)
    """
    # Check database type to determine where to read from
    database_type = os.getenv("DATABASE_TYPE", "duckdb")
    
    if database_type == "databricks":
        # Read from Databricks
        from databricks import sql
        
        host = os.getenv("DATABRICKS_HOST")
        token = os.getenv("DATABRICKS_TOKEN")
        http_path = os.getenv("DATABRICKS_HTTP_PATH")
        catalog = os.getenv("DATABRICKS_CATALOG", "workspace")
        schema = os.getenv("DATABRICKS_SCHEMA", "default")
        
        context.log.info(f"Reading customer_profile from Databricks: {catalog}.{schema}_marts.customer_profile")
        
        with sql.connect(
            server_hostname=host,
            http_path=http_path,
            access_token=token,
        ) as conn:
            with conn.cursor() as cursor:
                cursor.execute(f"SELECT * FROM {catalog}.{schema}_marts.customer_profile")
                customer_profile = cursor.fetchall_arrow().to_pandas()
                context.log.info(f"Loaded {len(customer_profile)} rows from customer_profile table")
    else:
        # Read from DuckDB
        import duckdb
        
        duckdb_path = os.getenv("DUCKDB_PATH", "data/duckdb/lending_club.duckdb")
        context.log.info(f"Reading customer_profile from DuckDB: {duckdb_path}")
        
        conn = duckdb.connect(database=duckdb_path, read_only=True)
        try:
            customer_profile = conn.execute("SELECT * FROM main_marts.customer_profile").df()
            context.log.info(f"Loaded {len(customer_profile)} rows from customer_profile table")
        finally:
            conn.close()
    
    # Define output path
    output_dir = Path("data/outputs")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    output_path = output_dir / "customer_profile.csv"
    
    context.log.info(
        f"Exporting {len(customer_profile)} rows to {output_path} "
        f"(columns: {list(customer_profile.columns)})"
    )
    
    try:
        # Export to CSV with UTF-8 encoding
        customer_profile.to_csv(
            output_path,
            index=False,
            encoding="utf-8",
        )
        
        # Validate that the file was created successfully
        if not output_path.exists():
            raise OSError(f"Output file was not created: {output_path}")
        
        # Get file size for metadata
        file_size_bytes = output_path.stat().st_size
        file_size_kb = file_size_bytes / 1024
        
        # Validate file is not empty
        if file_size_bytes == 0:
            raise OSError(f"Output file is empty: {output_path}")
        
        # Log success with file details
        context.log.info(
            f"Successfully exported customer profile to {output_path}"
        )
        context.log.info(
            f"Output file details - Rows: {len(customer_profile)}, "
            f"Columns: {len(customer_profile.columns)}, "
            f"Size: {file_size_kb:.2f} KB ({file_size_bytes:,} bytes)"
        )
        
        # Log metadata (no return value needed for side-effect assets)
        context.add_output_metadata({
            "row_count": len(customer_profile),
            "column_count": len(customer_profile.columns),
            "file_path": str(output_path),
            "file_size_kb": round(file_size_kb, 2),
            "file_size_bytes": file_size_bytes,
            "encoding": "utf-8",
            "execution_timestamp": datetime.now().isoformat(),
            "preview": MetadataValue.md(customer_profile.head(10).to_markdown()),
        })
        
    except OSError as e:
        context.log.error(
            f"Failed to write CSV file to {output_path}: {str(e)}. "
            "This may be due to insufficient disk space or permission issues."
        )
        raise OSError(
            f"Insufficient disk space or permission error writing to {output_path}: {str(e)}"
        ) from e


@asset(
    group_name="outputs",
    tags={
        "layer": "output", 
        "format": "parquet",
        "destination": "local",
        "domain": "analytics",
        "sla": "daily",
        "priority": "medium",
    },
    description="Export customer profile to Parquet format with Snappy compression. This asset exports customer-level aggregated analytics to a Parquet file optimized for data science and ML workflows.",
    metadata={
        "owner": "analytics-team",
        "format": "parquet",
        "compression": "snappy",
        "destination": "data/outputs/",
        "data_classification": "internal",
        "consumers": ["data_science", "ml_pipelines", "customer_analytics"],
        "expected_lag_hours": 26,
        "business_purpose": "Provide customer-level aggregated data for data science and ML model training",
        "upstream_dependencies": "customer_profile mart (DBT incremental)",
        "output_schema": "customer_id, customer_name, has_loan_flag, total_accounts_count, total_balance_amount, total_annual_interest_amount, calculated_at",
        "naming_convention": "snake_case with descriptive suffixes (_flag, _count, _amount, _at)",
        "performance_notes": "Snappy compression provides good balance of compression ratio and read speed",
    },
    owners=["analytics-team@company.com"],
    deps=[get_asset_key_for_model([dbt_transformations], "customer_profile")],
)
def customer_profile_parquet(
    context: AssetExecutionContext,
) -> None:
    """
    Export the customer_profile mart to a Parquet file with Snappy compression.
    
    This asset reads the customer_profile table from the database and exports it
    to data/outputs/customer_profile.parquet with Snappy compression for efficient
    storage and fast read performance.
    
    Args:
        context: Dagster execution context for logging and metadata
        
    Returns:
        None (side-effect asset that writes file)
        
    Raises:
        OSError: If there are issues writing the file (e.g., disk space)
    """
    # Check database type to determine where to read from
    database_type = os.getenv("DATABASE_TYPE", "duckdb")
    
    if database_type == "databricks":
        # Read from Databricks
        from databricks import sql
        
        host = os.getenv("DATABRICKS_HOST")
        token = os.getenv("DATABRICKS_TOKEN")
        http_path = os.getenv("DATABRICKS_HTTP_PATH")
        catalog = os.getenv("DATABRICKS_CATALOG", "workspace")
        schema = os.getenv("DATABRICKS_SCHEMA", "default")
        
        context.log.info(f"Reading customer_profile from Databricks: {catalog}.{schema}_marts.customer_profile")
        
        with sql.connect(
            server_hostname=host,
            http_path=http_path,
            access_token=token,
        ) as conn:
            with conn.cursor() as cursor:
                cursor.execute(f"SELECT * FROM {catalog}.{schema}_marts.customer_profile")
                customer_profile = cursor.fetchall_arrow().to_pandas()
                context.log.info(f"Loaded {len(customer_profile)} rows from customer_profile table")
    else:
        # Read from DuckDB
        import duckdb
        
        duckdb_path = os.getenv("DUCKDB_PATH", "data/duckdb/lending_club.duckdb")
        context.log.info(f"Reading customer_profile from DuckDB: {duckdb_path}")
        
        conn = duckdb.connect(database=duckdb_path, read_only=True)
        try:
            customer_profile = conn.execute("SELECT * FROM main_marts.customer_profile").df()
            context.log.info(f"Loaded {len(customer_profile)} rows from customer_profile table")
        finally:
            conn.close()
    
    # Define output path
    output_dir = Path("data/outputs")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    output_path = output_dir / "customer_profile.parquet"
    
    context.log.info(
        f"Exporting {len(customer_profile)} rows to {output_path} "
        f"(columns: {list(customer_profile.columns)})"
    )
    
    try:
        # Export to Parquet with Snappy compression
        customer_profile.to_parquet(
            output_path,
            index=False,
            compression="snappy",
            engine="pyarrow",
        )
        
        # Validate that the file was created successfully
        if not output_path.exists():
            raise OSError(f"Output file was not created: {output_path}")
        
        # Get file size for metadata
        file_size_bytes = output_path.stat().st_size
        file_size_kb = file_size_bytes / 1024
        
        # Validate file is not empty
        if file_size_bytes == 0:
            raise OSError(f"Output file is empty: {output_path}")
        
        # Log success with file details
        context.log.info(
            f"Successfully exported customer profile to {output_path}"
        )
        context.log.info(
            f"Output file details - Rows: {len(customer_profile)}, "
            f"Columns: {len(customer_profile.columns)}, "
            f"Size: {file_size_kb:.2f} KB ({file_size_bytes:,} bytes)"
        )
        
        # Log metadata (no return value needed for side-effect assets)
        context.add_output_metadata({
            "row_count": len(customer_profile),
            "column_count": len(customer_profile.columns),
            "file_path": str(output_path),
            "file_size_kb": round(file_size_kb, 2),
            "file_size_bytes": file_size_bytes,
            "compression": "snappy",
            "engine": "pyarrow",
            "execution_timestamp": datetime.now().isoformat(),
            "preview": MetadataValue.md(customer_profile.head(10).to_markdown()),
        })
        
    except OSError as e:
        context.log.error(
            f"Failed to write Parquet file to {output_path}: {str(e)}. "
            "This may be due to insufficient disk space or permission issues."
        )
        raise OSError(
            f"Insufficient disk space or permission error writing to {output_path}: {str(e)}"
        ) from e


@asset(
    group_name="outputs",
    tags={
        "layer": "output",
        "format": "json",
        "destination": "local",
        "domain": "data_quality",
        "sla": "daily",
        "priority": "high",
    },
    description="Generate data quality report from DBT test results. This asset parses DBT test results, groups them by layer and severity, and exports a comprehensive quality report to JSON format for monitoring and alerting.",
    metadata={
        "owner": "data-engineering-team",
        "format": "json",
        "destination": "data/quality_reports/",
        "data_classification": "internal",
        "consumers": ["data_engineering", "data_quality_team", "monitoring_systems"],
        "business_purpose": "Monitor data quality across all pipeline layers and track test pass/fail rates",
        "upstream_dependencies": "DBT test execution",
        "output_schema": "timestamp, summary, by_layer, by_severity, failures, warnings, errors",
    },
    owners=["data-engineering-team@company.com"],
    deps=[get_asset_key_for_model([dbt_transformations], "account_summary")],
)
def data_quality_report(
    context: AssetExecutionContext,
    data_quality_monitor: DataQualityMonitor,
) -> None:
    """
    Generate a comprehensive data quality report from DBT test results.
    
    This asset reads DBT test results from the run_results.json file,
    parses them into structured test results, generates a quality report
    with summary statistics and groupings, and exports it to JSON format.
    
    The report includes:
    - Summary statistics (total tests, pass/fail counts, pass rate)
    - Results grouped by data layer (source, staging, snapshot, intermediate, marts)
    - Results grouped by severity (error, warn)
    - Detailed failure information with error messages
    
    Args:
        context: Dagster execution context for logging and metadata
        data_quality_monitor: DataQualityMonitor resource for parsing and reporting
        
    Returns:
        None (side-effect asset that writes report to file)
        
    Raises:
        FileNotFoundError: If DBT results file is not found
        json.JSONDecodeError: If DBT results file is not valid JSON
    """
    # Define path to DBT run results
    dbt_results_path = Path("dbt_project/target/run_results.json")
    
    context.log.info(f"Reading DBT test results from {dbt_results_path}")
    
    # Check if results file exists
    if not dbt_results_path.exists():
        context.log.warning(
            f"DBT results file not found at {dbt_results_path}. "
            "This may be the first run or DBT tests have not been executed yet. "
            "Creating a placeholder report."
        )
        
        # Create a placeholder report with no test results
        report = {
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total_tests": 0,
                "passed": 0,
                "failed": 0,
                "warned": 0,
                "skipped": 0,
                "errored": 0,
                "pass_rate": 0.0,
            },
            "by_layer": {},
            "by_severity": {},
            "failures": [],
            "warnings": [],
            "errors": [],
            "note": "No DBT test results found. This is a placeholder report.",
        }
        
        test_results = []
    else:
        try:
            # Parse DBT test results
            test_results = data_quality_monitor.parse_dbt_test_results(str(dbt_results_path))
            context.log.info(f"Parsed {len(test_results)} test results from DBT")
            
            # Generate quality report
            report = data_quality_monitor.generate_report(test_results)
            context.log.info(
                f"Generated quality report: {report['summary']['total_tests']} tests, "
                f"{report['summary']['passed']} passed, "
                f"{report['summary']['failed']} failed, "
                f"{report['summary']['warned']} warned"
            )
        except Exception as e:
            context.log.error(f"Error parsing DBT test results: {str(e)}")
            raise
    
    # Define output path with timestamp
    output_dir = Path("data/quality_reports")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = output_dir / f"quality_report_{timestamp_str}.json"
    
    # Also save as latest report
    latest_path = output_dir / "quality_report_latest.json"
    
    context.log.info(f"Saving quality report to {output_path}")
    
    try:
        # Save timestamped report
        data_quality_monitor.save_report(report, str(output_path))
        
        # Save as latest report
        data_quality_monitor.save_report(report, str(latest_path))
        
        # Validate files were created
        if not output_path.exists():
            raise OSError(f"Quality report file was not created: {output_path}")
        
        if not latest_path.exists():
            raise OSError(f"Latest quality report file was not created: {latest_path}")
        
        # Get file sizes
        file_size_bytes = output_path.stat().st_size
        file_size_kb = file_size_bytes / 1024
        
        context.log.info(
            f"Successfully saved quality report to {output_path} "
            f"({file_size_kb:.2f} KB)"
        )
        
        # Log summary statistics
        if test_results:
            context.log.info(
                f"Quality Summary - Pass Rate: {report['summary']['pass_rate']}%, "
                f"Failures: {report['summary']['failed']}, "
                f"Warnings: {report['summary']['warned']}"
            )
            
            # Log layer-specific statistics
            for layer, stats in report["by_layer"].items():
                context.log.info(
                    f"Layer '{layer}': {stats['total']} tests, "
                    f"{stats['passed']} passed, "
                    f"{stats['failed']} failed "
                    f"(pass rate: {stats['pass_rate']}%)"
                )
        
        # Add output metadata
        context.add_output_metadata({
            "report_path": str(output_path),
            "latest_report_path": str(latest_path),
            "file_size_kb": round(file_size_kb, 2),
            "total_tests": report["summary"]["total_tests"],
            "passed": report["summary"]["passed"],
            "failed": report["summary"]["failed"],
            "warned": report["summary"]["warned"],
            "pass_rate": report["summary"]["pass_rate"],
            "execution_timestamp": datetime.now().isoformat(),
            "layers_tested": list(report["by_layer"].keys()) if report["by_layer"] else [],
        })
        
    except OSError as e:
        context.log.error(f"Failed to write quality report: {str(e)}")
        raise
