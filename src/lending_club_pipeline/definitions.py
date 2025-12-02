"""
Dagster definitions for the LendingClub data pipeline.

This module wires together all assets, resources, and schedules to create
the complete Dagster deployment. It configures the pipeline to run in both
development (DuckDB) and production (Databricks) environments based on
environment variables.
"""

import os
from pathlib import Path
from dagster import (
    Definitions, 
    AssetSelection, 
    define_asset_job, 
    ScheduleDefinition,
    in_process_executor,
)
from dagster_dbt import DbtCliResource

# Import all assets
from .assets.ingestion import customers_raw, accounts_raw
from .assets.dbt_assets import (
    dbt_transformations, 
    DBT_PROJECT_DIR,
)
from .assets.outputs import (
    account_summary_csv, 
    account_summary_parquet,
    account_summary_to_databricks,
    data_quality_report,
)

# Import all resources
from .resources.duckdb_io_manager import DuckDBIOManager
from .resources.databricks_io_manager import DatabricksIOManager
from .resources.databricks_resource import DatabricksResource
from .resources.config import DataPlatformConfig
from .resources.data_quality import DataQualityMonitor
from .io_managers.parquet_manager import ParquetIOManager

# Load configuration from environment
config = DataPlatformConfig.from_env()

# Configure resources based on environment
# Choose IO manager based on database type
if config.database_type == "databricks":
    io_manager = DatabricksIOManager(
        host=config.databricks_host or "",
        token=config.databricks_token or "",
        http_path=config.databricks_http_path or "",
        catalog=config.databricks_catalog or "",
        schema=config.databricks_schema or "",
    )
else:
    io_manager = DuckDBIOManager(database_path=config.duckdb_path)

resources = {
    # IO Manager for persisting ingestion assets (DuckDB or Databricks)
    "io_manager": io_manager,
    
    # DBT CLI resource for executing transformations
    "dbt": DbtCliResource(
        project_dir=os.fspath(DBT_PROJECT_DIR),
        profiles_dir=os.fspath(DBT_PROJECT_DIR),
        target=config.dbt_target,
    ),
    
    # Parquet IO Manager for efficient file storage
    "parquet_io_manager": ParquetIOManager(output_path=config.output_path),
    
    # Data Quality Monitor for tracking and reporting test results
    "data_quality_monitor": DataQualityMonitor(),
}

# Add Databricks resource if configured for production
if config.database_type == "databricks":
    resources["databricks"] = DatabricksResource(
        host=config.databricks_host or "",
        token=config.databricks_token or "",
        http_path=config.databricks_http_path or "",
        catalog=config.databricks_catalog or "",
        schema=config.databricks_schema or "",
    )
else:
    # Provide a dummy Databricks resource for dev environment
    # This allows the asset to be defined but will skip execution
    resources["databricks"] = DatabricksResource(
        host="dummy",
        token="dummy",
        http_path="dummy",
        catalog="dummy",
        schema="dummy",
    )

# Define asset jobs for selective execution
# Use in_process_executor to avoid DuckDB concurrency issues
# Job 1: Ingestion only
ingestion_job = define_asset_job(
    name="ingestion_job",
    selection=AssetSelection.groups("ingestion"),
    description="Run only the data ingestion assets (customers_raw, accounts_raw)",
    executor_def=in_process_executor,
)

# Job 2: Transformations only (requires ingestion to have run first)
transformations_job = define_asset_job(
    name="transformations_job",
    selection=AssetSelection.groups("staging", "intermediate", "marts"),
    description="Run only the DBT transformation assets (staging, intermediate, marts)",
    executor_def=in_process_executor,
)

# Job 3: Outputs only (requires transformations to have run first)
outputs_job = define_asset_job(
    name="outputs_job",
    selection=AssetSelection.groups("outputs"),
    description="Run only the output export assets (CSV, Parquet, Databricks)",
    executor_def=in_process_executor,
)

# Job 4: Full pipeline (all assets)
full_pipeline_job = define_asset_job(
    name="full_pipeline_job",
    selection=AssetSelection.all(),
    description="Run the complete pipeline from ingestion to outputs",
    executor_def=in_process_executor,
)

# Define schedules for automated execution
# Schedule 1: Daily full pipeline run (production)
# Uses in_process_executor to avoid DuckDB concurrency issues
daily_pipeline_schedule = ScheduleDefinition(
    name="daily_pipeline_schedule",
    job=full_pipeline_job,
    cron_schedule="0 2 * * *",  # Run at 2 AM daily
    description="Run the full pipeline daily at 2 AM (sequential execution to avoid DuckDB locks)",
)

# Define all assets and resources
defs = Definitions(
    assets=[
        # Ingestion assets (group: ingestion)
        customers_raw,
        accounts_raw,
        
        # DBT transformation assets (groups: staging, intermediate, marts)
        dbt_transformations,
        
        # Output assets (group: outputs)
        account_summary_csv,
        account_summary_parquet,
        account_summary_to_databricks,
        data_quality_report,
    ],
    resources=resources,
    jobs=[
        ingestion_job,
        transformations_job,
        outputs_job,
        full_pipeline_job,
    ],
    schedules=[
        daily_pipeline_schedule,
    ],
)
