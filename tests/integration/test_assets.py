"""
Integration tests for Dagster assets.

These tests verify that assets execute successfully and produce expected outputs.
They test the integration between different components of the pipeline.
"""
import os
import tempfile
from pathlib import Path

import pandas as pd
import pytest
from dagster import (
    materialize,
    AssetSelection,
    build_asset_context,
)

from lending_club_pipeline.assets.ingestion import customers_raw, accounts_raw
from lending_club_pipeline.assets.dbt_assets import dbt_transformations
from lending_club_pipeline.assets.outputs import (
    account_summary_csv,
    account_summary_parquet,
)
from lending_club_pipeline.definitions import defs


@pytest.fixture
def sample_data_dir(tmp_path):
    """Create sample CSV files for testing."""
    # Create data directory structure
    data_dir = tmp_path / "data" / "inputs"
    data_dir.mkdir(parents=True, exist_ok=True)
    
    # Create sample Customer.csv
    customers_df = pd.DataFrame({
        "CustomerID": ["1", "2", "3"],
        "Name": ["Alice Smith", "Bob Jones", "Charlie Brown"],
        "HasLoan": ["Yes", "No", "None"]
    })
    customers_df.to_csv(data_dir / "Customer.csv", index=False)
    
    # Create sample accounts.csv
    accounts_df = pd.DataFrame({
        "AccountID": ["A001", "A002", "A003"],
        "CustomerID": ["1", "2", "3"],
        "Balance": ["5000.00", "15000.00", "25000.00"],
        "AccountType": ["Savings", "Savings", "Savings"]
    })
    accounts_df.to_csv(data_dir / "accounts.csv", index=False)
    
    return tmp_path


class TestIngestionAssets:
    """Integration tests for ingestion assets."""
    
    def test_customers_raw_executes_successfully(self, sample_data_dir):
        """Test that customers_raw asset executes successfully."""
        original_cwd = os.getcwd()
        try:
            os.chdir(sample_data_dir)
            context = build_asset_context()
            result = customers_raw(context)
            
            # Verify output
            assert result.value is not None
            assert isinstance(result.value, pd.DataFrame)
            assert len(result.value) == 3
            assert "CustomerID" in result.value.columns
            assert "Name" in result.value.columns
            assert "HasLoan" in result.value.columns
            
            # Verify metadata
            assert result.metadata["row_count"].value == 3
            assert "execution_timestamp" in result.metadata
        finally:
            os.chdir(original_cwd)
    
    def test_accounts_raw_executes_successfully(self, sample_data_dir):
        """Test that accounts_raw asset executes successfully."""
        original_cwd = os.getcwd()
        try:
            os.chdir(sample_data_dir)
            context = build_asset_context()
            result = accounts_raw(context)
            
            # Verify output
            assert result.value is not None
            assert isinstance(result.value, pd.DataFrame)
            assert len(result.value) == 3
            assert "AccountID" in result.value.columns
            assert "CustomerID" in result.value.columns
            assert "Balance" in result.value.columns
            assert "AccountType" in result.value.columns
            
            # Verify metadata
            assert result.metadata["row_count"].value == 3
            assert "execution_timestamp" in result.metadata
        finally:
            os.chdir(original_cwd)


class TestOutputAssets:
    """Integration tests for output assets."""
    
    def test_account_summary_csv_creates_file(self, tmp_path):
        """Test that account_summary_csv asset creates file in correct location."""
        # Create sample account summary data
        account_summary_df = pd.DataFrame({
            "customer_id": [1, 2, 3],
            "account_id": ["A001", "A002", "A003"],
            "original_balance": [5000.00, 15000.00, 25000.00],
            "interest_rate": [0.015, 0.02, 0.025],
            "annual_interest": [75.00, 300.00, 625.00],
            "new_balance": [5075.00, 15300.00, 25625.00]
        })
        
        # Change to temp directory
        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            
            # Execute asset
            context = build_asset_context()
            result = account_summary_csv(context, account_summary_df)
            
            # Verify output file was created
            output_path = Path("data/outputs/account_summary.csv")
            assert output_path.exists()
            
            # Verify file content
            loaded_df = pd.read_csv(output_path)
            assert len(loaded_df) == 3
            assert list(loaded_df.columns) == list(account_summary_df.columns)
            
            # Verify metadata
            assert result.metadata["row_count"].value == 3
            assert result.metadata["file_path"].value == str(output_path)
            assert result.metadata["encoding"].value == "utf-8"
        finally:
            os.chdir(original_cwd)
    
    def test_account_summary_parquet_creates_file(self, tmp_path):
        """Test that account_summary_parquet asset creates file in correct location."""
        # Create sample account summary data
        account_summary_df = pd.DataFrame({
            "customer_id": [1, 2, 3],
            "account_id": ["A001", "A002", "A003"],
            "original_balance": [5000.00, 15000.00, 25000.00],
            "interest_rate": [0.015, 0.02, 0.025],
            "annual_interest": [75.00, 300.00, 625.00],
            "new_balance": [5075.00, 15300.00, 25625.00]
        })
        
        # Change to temp directory
        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            
            # Execute asset
            context = build_asset_context()
            result = account_summary_parquet(context, account_summary_df)
            
            # Verify output file was created
            output_path = Path("data/outputs/account_summary.parquet")
            assert output_path.exists()
            
            # Verify file content
            loaded_df = pd.read_parquet(output_path)
            assert len(loaded_df) == 3
            assert list(loaded_df.columns) == list(account_summary_df.columns)
            
            # Verify metadata
            assert result.metadata["row_count"].value == 3
            assert result.metadata["file_path"].value == str(output_path)
            assert result.metadata["compression"].value == "snappy"
        finally:
            os.chdir(original_cwd)


class TestAssetDependencies:
    """Integration tests for asset dependency graph."""
    
    def test_asset_dependency_graph_is_configured(self):
        """Test that asset dependency graph is correctly configured."""
        from dagster import AssetKey
        
        # Get all assets from definitions
        all_assets = list(defs.assets)
        asset_keys = []
        
        # Extract asset keys from all assets
        for asset in all_assets:
            if hasattr(asset, 'keys'):
                # This is a multi-asset (like dbt_transformations)
                asset_keys.extend([key.to_user_string() for key in asset.keys])
            elif hasattr(asset, 'key'):
                # This is a single asset
                asset_keys.append(asset.key.to_user_string())
        
        # Verify ingestion assets exist
        assert "customers_raw" in asset_keys
        assert "accounts_raw" in asset_keys
        
        # Verify output assets exist
        assert "account_summary_csv" in asset_keys
        assert "account_summary_parquet" in asset_keys
        
        # Verify DBT assets exist (account_summary is the final mart)
        # DBT assets have prefixed keys like "marts/account_summary"
        assert any("account_summary" in key for key in asset_keys)
    
    def test_ingestion_assets_have_no_dependencies(self):
        """Test that ingestion assets are root assets with no dependencies."""
        # Check customers_raw asset
        customers_asset = None
        for asset in defs.assets:
            if hasattr(asset, 'key') and asset.key.to_user_string() == "customers_raw":
                customers_asset = asset
                break
        
        assert customers_asset is not None
        # Ingestion assets should have no input dependencies
        assert len(customers_asset.input_names) == 0
        
        # Check accounts_raw asset
        accounts_asset = None
        for asset in defs.assets:
            if hasattr(asset, 'key') and asset.key.to_user_string() == "accounts_raw":
                accounts_asset = asset
                break
        
        assert accounts_asset is not None
        # Ingestion assets should have no input dependencies
        assert len(accounts_asset.input_names) == 0
    
    def test_output_assets_depend_on_transformations(self):
        """Test that output assets depend on transformation layer."""
        # Check CSV output asset
        csv_asset = None
        for asset in defs.assets:
            # Handle both single assets and multi-assets
            if hasattr(asset, 'keys'):
                # Multi-asset - check if any key matches
                for key in asset.keys:
                    if key.to_user_string() == "account_summary_csv":
                        csv_asset = asset
                        break
            elif hasattr(asset, 'key'):
                # Single asset
                if asset.key.to_user_string() == "account_summary_csv":
                    csv_asset = asset
                    break
        
        assert csv_asset is not None
        # Output assets should have dependencies (account_summary from DBT)
        assert len(csv_asset.input_names) > 0
        assert "account_summary" in csv_asset.input_names
        
        # Check Parquet output asset
        parquet_asset = None
        for asset in defs.assets:
            # Handle both single assets and multi-assets
            if hasattr(asset, 'keys'):
                # Multi-asset - check if any key matches
                for key in asset.keys:
                    if key.to_user_string() == "account_summary_parquet":
                        parquet_asset = asset
                        break
            elif hasattr(asset, 'key'):
                # Single asset
                if asset.key.to_user_string() == "account_summary_parquet":
                    parquet_asset = asset
                    break
        
        assert parquet_asset is not None
        # Output assets should have dependencies (account_summary from DBT)
        assert len(parquet_asset.input_names) > 0
        assert "account_summary" in parquet_asset.input_names
