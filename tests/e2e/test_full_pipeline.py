"""
End-to-end tests for the complete data pipeline.

These tests verify that the entire pipeline executes successfully from
ingestion through transformations to final outputs, validating data quality
and consistency at each stage.
"""
import os
import tempfile
from pathlib import Path

import pandas as pd
import pytest
from dagster import materialize, AssetSelection

from lending_club_pipeline.definitions import defs
from lending_club_pipeline.assets.ingestion import customers_raw, accounts_raw
from lending_club_pipeline.assets.dbt_assets import dbt_transformations
from lending_club_pipeline.assets.outputs import (
    account_summary_csv,
    account_summary_parquet,
)


@pytest.fixture
def pipeline_test_env(tmp_path):
    """
    Set up a complete test environment for pipeline execution.
    
    Creates:
    - Sample input CSV files with realistic data
    - Output directories for results
    - Temporary DuckDB database
    """
    # Create data directory structure
    data_dir = tmp_path / "data"
    inputs_dir = data_dir / "inputs"
    outputs_dir = data_dir / "outputs"
    duckdb_dir = data_dir / "duckdb"
    
    inputs_dir.mkdir(parents=True, exist_ok=True)
    outputs_dir.mkdir(parents=True, exist_ok=True)
    duckdb_dir.mkdir(parents=True, exist_ok=True)
    
    # Create sample Customer.csv with diverse data
    customers_df = pd.DataFrame({
        "CustomerID": ["1", "2", "3", "4", "5"],
        "Name": ["Alice Smith", "Bob Jones", "Charlie Brown", "Diana Prince", "Eve Adams"],
        "HasLoan": ["Yes", "No", "None", "Yes", "No"]
    })
    customers_df.to_csv(inputs_dir / "Customer.csv", index=False)
    
    # Create sample accounts.csv with different balance tiers
    # Balance tiers: <10k, 10k-20k, >=20k to test interest rate logic
    accounts_df = pd.DataFrame({
        "AccountID": ["A001", "A002", "A003", "A004", "A005"],
        "CustomerID": ["1", "2", "3", "4", "5"],
        "Balance": ["5000.00", "15000.00", "25000.00", "8000.00", "22000.00"],
        "AccountType": ["Savings", "Savings", "Savings", "Savings", "Savings"]
    })
    accounts_df.to_csv(inputs_dir / "accounts.csv", index=False)
    
    # Set environment variables for test
    original_env = {}
    test_env_vars = {
        "DATABASE_TYPE": "duckdb",
        "DBT_TARGET": "dev",
        "DUCKDB_PATH": str(duckdb_dir / "test_lending_club.duckdb"),
        "OUTPUT_PATH": str(outputs_dir),
    }
    
    for key, value in test_env_vars.items():
        original_env[key] = os.environ.get(key)
        os.environ[key] = value
    
    # Change to temp directory for test execution
    original_cwd = os.getcwd()
    os.chdir(tmp_path)
    
    yield {
        "tmp_path": tmp_path,
        "inputs_dir": inputs_dir,
        "outputs_dir": outputs_dir,
        "duckdb_dir": duckdb_dir,
        "customers_df": customers_df,
        "accounts_df": accounts_df,
    }
    
    # Restore original environment
    os.chdir(original_cwd)
    for key, value in original_env.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value


class TestFullPipeline:
    """End-to-end tests for the complete data pipeline."""
    
    def test_full_pipeline_execution(self, pipeline_test_env):
        """
        Test that the complete pipeline executes successfully from ingestion to outputs.
        
        This test:
        - Materializes all assets in the pipeline
        - Verifies that ingestion, transformation, and output assets all succeed
        - Validates that output files are created
        """
        # Get all assets from definitions
        all_assets = [
            customers_raw,
            accounts_raw,
            dbt_transformations,
            account_summary_csv,
            account_summary_parquet,
        ]
        
        # Materialize all assets (excluding Databricks output for local test)
        result = materialize(
            all_assets,
            resources=defs.resources,
        )
        
        # Verify materialization was successful
        assert result.success, "Pipeline execution failed"
        
        # Verify all expected assets were materialized
        materialized_keys = {event.asset_key for event in result.asset_materializations()}
        
        assert any("customers_raw" in str(key) for key in materialized_keys), \
            "customers_raw asset was not materialized"
        assert any("accounts_raw" in str(key) for key in materialized_keys), \
            "accounts_raw asset was not materialized"
        assert any("account_summary_csv" in str(key) for key in materialized_keys), \
            "account_summary_csv asset was not materialized"
        assert any("account_summary_parquet" in str(key) for key in materialized_keys), \
            "account_summary_parquet asset was not materialized"
    
    def test_output_files_exist(self, pipeline_test_env):
        """
        Test that CSV and Parquet output files are created in the correct locations.
        """
        outputs_dir = pipeline_test_env["outputs_dir"]
        
        # Materialize output assets
        all_assets = [
            customers_raw,
            accounts_raw,
            dbt_transformations,
            account_summary_csv,
            account_summary_parquet,
        ]
        
        result = materialize(
            all_assets,
            resources=defs.resources,
        )
        
        assert result.success, "Pipeline execution failed"
        
        # Verify CSV output file exists
        csv_path = outputs_dir / "account_summary.csv"
        assert csv_path.exists(), f"CSV output file not found at {csv_path}"
        assert csv_path.stat().st_size > 0, "CSV output file is empty"
        
        # Verify Parquet output file exists
        parquet_path = outputs_dir / "account_summary.parquet"
        assert parquet_path.exists(), f"Parquet output file not found at {parquet_path}"
        assert parquet_path.stat().st_size > 0, "Parquet output file is empty"
    
    def test_output_schema_matches_expected(self, pipeline_test_env):
        """
        Test that output files have the expected schema with all required columns.
        """
        outputs_dir = pipeline_test_env["outputs_dir"]
        
        # Expected columns in the account summary output
        expected_columns = [
            "customer_id",
            "account_id",
            "original_balance",
            "interest_rate",
            "annual_interest",
            "new_balance"
        ]
        
        # Materialize all assets
        all_assets = [
            customers_raw,
            accounts_raw,
            dbt_transformations,
            account_summary_csv,
            account_summary_parquet,
        ]
        
        result = materialize(
            all_assets,
            resources=defs.resources,
        )
        
        assert result.success, "Pipeline execution failed"
        
        # Verify CSV schema
        csv_path = outputs_dir / "account_summary.csv"
        csv_df = pd.read_csv(csv_path)
        
        assert list(csv_df.columns) == expected_columns, \
            f"CSV columns {list(csv_df.columns)} do not match expected {expected_columns}"
        
        # Verify Parquet schema
        parquet_path = outputs_dir / "account_summary.parquet"
        parquet_df = pd.read_parquet(parquet_path)
        
        assert list(parquet_df.columns) == expected_columns, \
            f"Parquet columns {list(parquet_df.columns)} do not match expected {expected_columns}"
    
    def test_data_consistency_between_csv_and_parquet(self, pipeline_test_env):
        """
        Test that CSV and Parquet outputs contain identical data.
        """
        outputs_dir = pipeline_test_env["outputs_dir"]
        
        # Materialize all assets
        all_assets = [
            customers_raw,
            accounts_raw,
            dbt_transformations,
            account_summary_csv,
            account_summary_parquet,
        ]
        
        result = materialize(
            all_assets,
            resources=defs.resources,
        )
        
        assert result.success, "Pipeline execution failed"
        
        # Load both output files
        csv_path = outputs_dir / "account_summary.csv"
        parquet_path = outputs_dir / "account_summary.parquet"
        
        csv_df = pd.read_csv(csv_path)
        parquet_df = pd.read_parquet(parquet_path)
        
        # Verify row counts match
        assert len(csv_df) == len(parquet_df), \
            f"Row count mismatch: CSV has {len(csv_df)} rows, Parquet has {len(parquet_df)} rows"
        
        # Verify column names match
        assert list(csv_df.columns) == list(parquet_df.columns), \
            "Column names do not match between CSV and Parquet"
        
        # Verify data values match (allowing for minor floating point differences)
        pd.testing.assert_frame_equal(
            csv_df.sort_values("account_id").reset_index(drop=True),
            parquet_df.sort_values("account_id").reset_index(drop=True),
            check_dtype=False,  # Allow type differences between CSV and Parquet
            atol=0.01,  # Allow small floating point differences
        )
    
    def test_row_counts_and_data_quality(self, pipeline_test_env):
        """
        Test that output data has correct row counts and meets quality standards.
        """
        outputs_dir = pipeline_test_env["outputs_dir"]
        customers_df = pipeline_test_env["customers_df"]
        accounts_df = pipeline_test_env["accounts_df"]
        
        # Materialize all assets
        all_assets = [
            customers_raw,
            accounts_raw,
            dbt_transformations,
            account_summary_csv,
            account_summary_parquet,
        ]
        
        result = materialize(
            all_assets,
            resources=defs.resources,
        )
        
        assert result.success, "Pipeline execution failed"
        
        # Load output
        csv_path = outputs_dir / "account_summary.csv"
        output_df = pd.read_csv(csv_path)
        
        # Verify row count matches input (all accounts are savings accounts in test data)
        expected_row_count = len(accounts_df)
        assert len(output_df) == expected_row_count, \
            f"Expected {expected_row_count} rows in output, got {len(output_df)}"
        
        # Verify no null values in required fields
        required_fields = ["customer_id", "account_id", "original_balance", "interest_rate"]
        for field in required_fields:
            null_count = output_df[field].isna().sum()
            assert null_count == 0, f"Found {null_count} null values in {field}"
        
        # Verify interest rates are in valid range (1% to 2.5%)
        assert (output_df["interest_rate"] >= 0.01).all(), \
            "Some interest rates are below minimum (1%)"
        assert (output_df["interest_rate"] <= 0.025).all(), \
            "Some interest rates are above maximum (2.5%)"
        
        # Verify annual interest calculation is correct
        calculated_interest = (output_df["original_balance"] * output_df["interest_rate"]).round(2)
        pd.testing.assert_series_equal(
            output_df["annual_interest"],
            calculated_interest,
            check_names=False,
            atol=0.01,
        )
        
        # Verify new balance calculation is correct
        calculated_new_balance = (output_df["original_balance"] + output_df["annual_interest"]).round(2)
        pd.testing.assert_series_equal(
            output_df["new_balance"],
            calculated_new_balance,
            check_names=False,
            atol=0.01,
        )
    
    def test_interest_rate_logic(self, pipeline_test_env):
        """
        Test that interest rates are calculated correctly based on balance tiers and loan status.
        """
        outputs_dir = pipeline_test_env["outputs_dir"]
        
        # Materialize all assets
        all_assets = [
            customers_raw,
            accounts_raw,
            dbt_transformations,
            account_summary_csv,
            account_summary_parquet,
        ]
        
        result = materialize(
            all_assets,
            resources=defs.resources,
        )
        
        assert result.success, "Pipeline execution failed"
        
        # Load output
        csv_path = outputs_dir / "account_summary.csv"
        output_df = pd.read_csv(csv_path)
        
        # Test data has specific balances and loan statuses:
        # Customer 1: Balance 5000, HasLoan=Yes -> Rate should be 0.015 (1% + 0.5% bonus)
        # Customer 2: Balance 15000, HasLoan=No -> Rate should be 0.015 (1.5%)
        # Customer 3: Balance 25000, HasLoan=None -> Rate should be 0.02 (2%)
        # Customer 4: Balance 8000, HasLoan=Yes -> Rate should be 0.015 (1% + 0.5% bonus)
        # Customer 5: Balance 22000, HasLoan=No -> Rate should be 0.02 (2%)
        
        # Verify specific interest rates
        customer_1_rate = output_df[output_df["customer_id"] == 1]["interest_rate"].iloc[0]
        assert abs(customer_1_rate - 0.015) < 0.001, \
            f"Customer 1 rate should be 0.015 (1% + 0.5% bonus), got {customer_1_rate}"
        
        customer_2_rate = output_df[output_df["customer_id"] == 2]["interest_rate"].iloc[0]
        assert abs(customer_2_rate - 0.015) < 0.001, \
            f"Customer 2 rate should be 0.015 (1.5%), got {customer_2_rate}"
        
        customer_3_rate = output_df[output_df["customer_id"] == 3]["interest_rate"].iloc[0]
        assert abs(customer_3_rate - 0.02) < 0.001, \
            f"Customer 3 rate should be 0.02 (2%), got {customer_3_rate}"
        
        customer_4_rate = output_df[output_df["customer_id"] == 4]["interest_rate"].iloc[0]
        assert abs(customer_4_rate - 0.015) < 0.001, \
            f"Customer 4 rate should be 0.015 (1% + 0.5% bonus), got {customer_4_rate}"
        
        customer_5_rate = output_df[output_df["customer_id"] == 5]["interest_rate"].iloc[0]
        assert abs(customer_5_rate - 0.02) < 0.001, \
            f"Customer 5 rate should be 0.02 (2%), got {customer_5_rate}"
    
    def test_pipeline_handles_empty_results_gracefully(self, pipeline_test_env):
        """
        Test that the pipeline handles edge cases like filtering that produces no results.
        
        Note: This test uses checking accounts which should be filtered out,
        resulting in empty output.
        """
        inputs_dir = pipeline_test_env["inputs_dir"]
        outputs_dir = pipeline_test_env["outputs_dir"]
        
        # Create accounts with only checking accounts (should be filtered out)
        accounts_df = pd.DataFrame({
            "AccountID": ["A001", "A002"],
            "CustomerID": ["1", "2"],
            "Balance": ["5000.00", "15000.00"],
            "AccountType": ["Checking", "Checking"]  # Only checking accounts
        })
        accounts_df.to_csv(inputs_dir / "accounts.csv", index=False)
        
        # Materialize all assets
        all_assets = [
            customers_raw,
            accounts_raw,
            dbt_transformations,
            account_summary_csv,
            account_summary_parquet,
        ]
        
        result = materialize(
            all_assets,
            resources=defs.resources,
        )
        
        # Pipeline should still succeed even with empty results
        assert result.success, "Pipeline should handle empty results gracefully"
        
        # Verify output files exist but are empty (or have only headers)
        csv_path = outputs_dir / "account_summary.csv"
        if csv_path.exists():
            csv_df = pd.read_csv(csv_path)
            assert len(csv_df) == 0, \
                "Output should be empty when all accounts are filtered out"
