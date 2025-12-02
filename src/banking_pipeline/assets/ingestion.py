"""
Ingestion assets for reading and validating raw CSV data.
"""
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Set

import pandas as pd
from dagster import (
    AssetExecutionContext, 
    asset, 
    Output, 
    MetadataValue,
    AutomationCondition,
)


class SchemaChangeError(Exception):
    """Exception raised when schema changes are detected in source data."""
    pass


def validate_csv_data(df: pd.DataFrame, filepath: str, required_columns: List[str]) -> None:
    """
    Validate CSV data for common issues.
    
    Args:
        df: DataFrame to validate
        filepath: Path to the CSV file (for error messages)
        required_columns: List of column names that must be present
        
    Raises:
        ValueError: If validation fails
    """
    # Check for empty file
    if df.empty:
        raise ValueError(f"CSV file is empty: {filepath}")
    
    # Check for missing columns
    actual_columns = set(df.columns)
    expected_columns = set(required_columns)
    missing_columns = expected_columns - actual_columns
    
    if missing_columns:
        raise ValueError(
            f"Missing required columns in {filepath}: {', '.join(sorted(missing_columns))}"
        )


def detect_schema_changes(
    actual_columns: Set[str], 
    expected_columns: Set[str], 
    filepath: str,
    context: AssetExecutionContext
) -> None:
    """
    Detect and report schema changes between expected and actual columns.
    
    This function compares the actual columns in the CSV file against the expected
    columns and raises a SchemaChangeError if any differences are found. It provides
    detailed information about missing and extra columns.
    
    Args:
        actual_columns: Set of column names found in the CSV file
        expected_columns: Set of column names that are expected
        filepath: Path to the CSV file (for error messages)
        context: Dagster execution context for logging
        
    Raises:
        SchemaChangeError: If schema changes are detected (missing or extra columns)
    """
    missing_columns = expected_columns - actual_columns
    extra_columns = actual_columns - expected_columns
    
    if missing_columns or extra_columns:
        error_details = []
        
        if missing_columns:
            missing_list = ', '.join(sorted(missing_columns))
            error_details.append(f"Missing columns: {missing_list}")
            context.log.error(f"Schema validation failed - Missing columns: {missing_list}")
        
        if extra_columns:
            extra_list = ', '.join(sorted(extra_columns))
            error_details.append(f"Extra columns: {extra_list}")
            context.log.error(f"Schema validation failed - Extra columns: {extra_list}")
        
        error_message = (
            f"Schema change detected in {filepath}. "
            f"{' | '.join(error_details)}. "
            f"Expected columns: {', '.join(sorted(expected_columns))}. "
            f"Actual columns: {', '.join(sorted(actual_columns))}."
        )
        
        context.log.error(error_message)
        raise SchemaChangeError(error_message)


@asset(
    group_name="ingestion",
    tags={
        "layer": "raw", 
        "source": "csv",
        "domain": "customer",
        "sla": "daily",
        "priority": "high",
    },
    description="Raw customer data ingested from Customer.csv with validation. This asset reads customer information including ID, name, and loan status from the source CSV file, performs data quality checks, and loads into the src_customer source table with a loaded_at timestamp for CDC tracking.",
    metadata={
        "schema": "raw",
        "owner": "data-engineering-team",
        "source_system": "lending_club_csv",
        "data_classification": "internal",
        "refresh_frequency": "daily",
        "expected_lag_hours": 24,
        "business_purpose": "Provide customer master data for account analysis",
        "data_quality_checks": "empty_file, missing_columns, column_name_validation, schema_change_detection",
        "downstream_consumers": "source layer (src_customer) -> staging layer (stg_customer) -> snapshots (snap_customer)",
        "freshness_sla": "24 hours - Expected to refresh daily at 2 AM",
        "target_table": "src_customer",
        "cdc_enabled": "true",
        "timestamp_column": "loaded_at",
    },
    owners=["data-engineering-team@company.com"],
)
def customers_raw(context: AssetExecutionContext) -> Output[pd.DataFrame]:
    """
    Read and validate customer data from CSV file.
    
    This asset ingests raw customer data and makes it available for the DBT source
    layer (src_customer). The DBT source model will add the loaded_at timestamp
    for CDC tracking and snapshot detection.
    
    Returns:
        Output containing validated customer DataFrame with metadata
        
    Raises:
        FileNotFoundError: If the CSV file does not exist
        ValueError: If the file is empty or missing required columns
        SchemaChangeError: If the CSV schema doesn't match expected columns
    """
    # Define file path and required columns
    filepath = Path("data/inputs/Customer.csv")
    required_columns = ["CustomerID", "Name", "HasLoan"]
    
    try:
        # Check if file exists
        if not filepath.exists():
            context.log.error(f"File not found: {filepath}")
            raise FileNotFoundError(f"Input file not found: {filepath}")
        
        # Read CSV file
        context.log.info(f"Reading customer data from {filepath}")
        
        try:
            df = pd.read_csv(filepath)
        except Exception as e:
            context.log.error(f"Failed to read CSV file {filepath}: {type(e).__name__} - {str(e)}")
            raise
        
        # Strip whitespace from column names
        df.columns = df.columns.str.strip()
        
        # Detect schema changes
        try:
            detect_schema_changes(
                actual_columns=set(df.columns),
                expected_columns=set(required_columns),
                filepath=str(filepath),
                context=context
            )
        except SchemaChangeError as e:
            context.log.error(f"Schema change detected in {filepath}: {str(e)}")
            raise
        
        # Validate data
        try:
            validate_csv_data(df, str(filepath), required_columns)
        except ValueError as e:
            context.log.error(f"Validation failed for {filepath}: {str(e)}")
            raise
        
        # Log success
        context.log.info(f"Successfully loaded {len(df)} customer records")
        
        # Log potential quarantine candidates (records with validation issues)
        null_ids = df[df['CustomerID'].isna()].shape[0]
        null_names = df[df['Name'].isna()].shape[0]
        
        if null_ids > 0 or null_names > 0:
            context.log.warning(
                f"Found potential quarantine candidates: "
                f"{null_ids} records with null CustomerID, "
                f"{null_names} records with null Name. "
                f"These records will be routed to quarantine_stg_customer."
            )
        
        # Return with metadata
        return Output(
            value=df,
            metadata={
                "row_count": len(df),
                "column_names": MetadataValue.text(", ".join(df.columns.tolist())),
                "execution_timestamp": datetime.now().isoformat(),
                "file_path": str(filepath),
                "preview": MetadataValue.md(df.head().to_markdown()),
                "potential_quarantine_records": null_ids + null_names,
            }
        )
    
    except FileNotFoundError:
        # Re-raise FileNotFoundError with context already logged
        raise
    except ValueError:
        # Re-raise ValueError with context already logged
        raise
    except Exception as e:
        # Catch any unexpected errors
        context.log.error(f"Unexpected error processing {filepath}: {type(e).__name__} - {str(e)}")
        raise


@asset(
    group_name="ingestion",
    tags={
        "layer": "raw", 
        "source": "csv",
        "domain": "account",
        "sla": "daily",
        "priority": "high",
    },
    description="Raw account data ingested from accounts.csv with validation. This asset reads account information including account ID, customer ID, balance, and account type from the source CSV file, performs data quality checks, and loads into the src_account source table with a loaded_at timestamp for CDC tracking.",
    metadata={
        "schema": "raw",
        "owner": "data-engineering-team",
        "source_system": "lending_club_csv",
        "data_classification": "internal",
        "refresh_frequency": "daily",
        "expected_lag_hours": 24,
        "business_purpose": "Provide account transaction data for interest calculation",
        "data_quality_checks": "empty_file, missing_columns, column_name_validation, schema_change_detection",
        "downstream_consumers": "source layer (src_account) -> staging layer (stg_account) -> snapshots (snap_account)",
        "freshness_sla": "24 hours - Expected to refresh daily at 2 AM",
        "target_table": "src_account",
        "cdc_enabled": "true",
        "timestamp_column": "loaded_at",
    },
    owners=["data-engineering-team@company.com"],
    deps=[customers_raw],  # Ensure sequential execution to avoid DuckDB lock conflicts
)
def accounts_raw(context: AssetExecutionContext) -> Output[pd.DataFrame]:
    """
    Read and validate account data from CSV file.
    
    This asset ingests raw account data and makes it available for the DBT source
    layer (src_account). The DBT source model will add the loaded_at timestamp
    for CDC tracking and snapshot detection.
    
    Returns:
        Output containing validated account DataFrame with metadata
        
    Raises:
        FileNotFoundError: If the CSV file does not exist
        ValueError: If the file is empty or missing required columns
        SchemaChangeError: If the CSV schema doesn't match expected columns
    """
    # Define file path and required columns
    filepath = Path("data/inputs/accounts.csv")
    required_columns = ["AccountID", "CustomerID", "Balance", "AccountType"]
    
    try:
        # Check if file exists
        if not filepath.exists():
            context.log.error(f"File not found: {filepath}")
            raise FileNotFoundError(f"Input file not found: {filepath}")
        
        # Read CSV file
        context.log.info(f"Reading account data from {filepath}")
        
        try:
            df = pd.read_csv(filepath)
        except Exception as e:
            context.log.error(f"Failed to read CSV file {filepath}: {type(e).__name__} - {str(e)}")
            raise
        
        # Strip whitespace from column names
        df.columns = df.columns.str.strip()
        
        # Detect schema changes
        try:
            detect_schema_changes(
                actual_columns=set(df.columns),
                expected_columns=set(required_columns),
                filepath=str(filepath),
                context=context
            )
        except SchemaChangeError as e:
            context.log.error(f"Schema change detected in {filepath}: {str(e)}")
            raise
        
        # Validate data
        try:
            validate_csv_data(df, str(filepath), required_columns)
        except ValueError as e:
            context.log.error(f"Validation failed for {filepath}: {str(e)}")
            raise
        
        # Log success
        context.log.info(f"Successfully loaded {len(df)} account records")
        
        # Log potential quarantine candidates (records with validation issues)
        null_ids = df[df['AccountID'].isna()].shape[0]
        null_customer_ids = df[df['CustomerID'].isna()].shape[0]
        null_balances = df[df['Balance'].isna()].shape[0]
        
        # Check for negative balances (convert to numeric first, handling errors)
        try:
            negative_balances = df[pd.to_numeric(df['Balance'], errors='coerce') < 0].shape[0]
        except:
            negative_balances = 0
        
        total_quarantine_candidates = null_ids + null_customer_ids + null_balances + negative_balances
        
        if total_quarantine_candidates > 0:
            context.log.warning(
                f"Found potential quarantine candidates: "
                f"{null_ids} records with null AccountID, "
                f"{null_customer_ids} records with null CustomerID, "
                f"{null_balances} records with null Balance, "
                f"{negative_balances} records with negative Balance. "
                f"These records will be routed to quarantine_stg_account."
            )
        
        # Return with metadata
        return Output(
            value=df,
            metadata={
                "row_count": len(df),
                "column_names": MetadataValue.text(", ".join(df.columns.tolist())),
                "execution_timestamp": datetime.now().isoformat(),
                "file_path": str(filepath),
                "preview": MetadataValue.md(df.head().to_markdown()),
                "potential_quarantine_records": total_quarantine_candidates,
            }
        )
    
    except FileNotFoundError:
        # Re-raise FileNotFoundError with context already logged
        raise
    except ValueError:
        # Re-raise ValueError with context already logged
        raise
    except Exception as e:
        # Catch any unexpected errors
        context.log.error(f"Unexpected error processing {filepath}: {type(e).__name__} - {str(e)}")
        raise
