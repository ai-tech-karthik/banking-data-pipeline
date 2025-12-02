"""
Unit tests for ingestion assets.
"""
import tempfile
from pathlib import Path

import pandas as pd
import pytest
from dagster import AssetExecutionContext, build_asset_context

from lending_club_pipeline.assets.ingestion import (
    customers_raw,
    accounts_raw,
    validate_csv_data,
)


class TestValidateCsvData:
    """Tests for the validate_csv_data helper function."""
    
    def test_valid_data(self):
        """Test validation passes with valid data."""
        df = pd.DataFrame({
            "col1": [1, 2, 3],
            "col2": ["a", "b", "c"]
        })
        # Should not raise any exception
        validate_csv_data(df, "test.csv", ["col1", "col2"])
    
    def test_empty_file_raises_error(self):
        """Test validation fails with empty DataFrame."""
        df = pd.DataFrame()
        with pytest.raises(ValueError, match="CSV file is empty"):
            validate_csv_data(df, "test.csv", ["col1"])
    
    def test_missing_columns_raises_error(self):
        """Test validation fails when required columns are missing."""
        df = pd.DataFrame({"col1": [1, 2, 3]})
        with pytest.raises(ValueError, match="Missing required columns"):
            validate_csv_data(df, "test.csv", ["col1", "col2", "col3"])


class TestCustomersRaw:
    """Tests for the customers_raw asset."""
    
    def test_customers_raw_with_valid_csv(self, tmp_path):
        """Test customers_raw asset reads valid CSV file successfully."""
        # Create a valid customer CSV file
        csv_path = tmp_path / "Customer.csv"
        df = pd.DataFrame({
            "CustomerID": ["1", "2", "3"],
            "Name": ["Alice", "Bob", "Charlie"],
            "HasLoan": ["Yes", "No", "None"]
        })
        df.to_csv(csv_path, index=False)
        
        # Temporarily change the file path in the asset
        import lending_club_pipeline.assets.ingestion as ingestion_module
        original_path = Path("data/inputs/Customer.csv")
        
        # Mock the filepath by creating the directory structure
        test_data_dir = tmp_path / "data" / "inputs"
        test_data_dir.mkdir(parents=True, exist_ok=True)
        test_csv = test_data_dir / "Customer.csv"
        df.to_csv(test_csv, index=False)
        
        # Change working directory temporarily
        import os
        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            context = build_asset_context()
            result = customers_raw(context)
            
            # Verify the output
            assert result.value is not None
            assert len(result.value) == 3
            assert "CustomerID" in result.value.columns
            assert "Name" in result.value.columns
            assert "HasLoan" in result.value.columns
            
            # Verify metadata
            assert result.metadata["row_count"].value == 3
            assert "execution_timestamp" in result.metadata
        finally:
            os.chdir(original_cwd)
    
    def test_customers_raw_file_not_found(self, tmp_path):
        """Test customers_raw raises error when file doesn't exist."""
        import os
        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            context = build_asset_context()
            with pytest.raises(FileNotFoundError, match="Input file not found"):
                customers_raw(context)
        finally:
            os.chdir(original_cwd)
    
    def test_customers_raw_empty_file(self, tmp_path):
        """Test customers_raw raises error with empty CSV file."""
        # Create an empty CSV file with headers only
        test_data_dir = tmp_path / "data" / "inputs"
        test_data_dir.mkdir(parents=True, exist_ok=True)
        test_csv = test_data_dir / "Customer.csv"
        
        df = pd.DataFrame(columns=["CustomerID", "Name", "HasLoan"])
        df.to_csv(test_csv, index=False)
        
        import os
        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            context = build_asset_context()
            with pytest.raises(ValueError, match="CSV file is empty"):
                customers_raw(context)
        finally:
            os.chdir(original_cwd)
    
    def test_customers_raw_missing_columns(self, tmp_path):
        """Test customers_raw raises error when required columns are missing."""
        # Create a CSV file with missing columns
        test_data_dir = tmp_path / "data" / "inputs"
        test_data_dir.mkdir(parents=True, exist_ok=True)
        test_csv = test_data_dir / "Customer.csv"
        
        df = pd.DataFrame({
            "CustomerID": ["1", "2"],
            "Name": ["Alice", "Bob"]
            # Missing HasLoan column
        })
        df.to_csv(test_csv, index=False)
        
        import os
        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            context = build_asset_context()
            with pytest.raises(ValueError, match="Missing required columns"):
                customers_raw(context)
        finally:
            os.chdir(original_cwd)


class TestAccountsRaw:
    """Tests for the accounts_raw asset."""
    
    def test_accounts_raw_with_valid_csv(self, tmp_path):
        """Test accounts_raw asset reads valid CSV file successfully."""
        # Create a valid accounts CSV file
        test_data_dir = tmp_path / "data" / "inputs"
        test_data_dir.mkdir(parents=True, exist_ok=True)
        test_csv = test_data_dir / "accounts.csv"
        
        df = pd.DataFrame({
            "AccountID": ["A001", "A002", "A003"],
            "CustomerID": ["1", "2", "3"],
            "Balance": ["5000.00", "15000.00", "25000.00"],
            "AccountType": ["Savings", "Checking", "Savings"]
        })
        df.to_csv(test_csv, index=False)
        
        import os
        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            context = build_asset_context()
            result = accounts_raw(context)
            
            # Verify the output
            assert result.value is not None
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
    
    def test_accounts_raw_file_not_found(self, tmp_path):
        """Test accounts_raw raises error when file doesn't exist."""
        import os
        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            context = build_asset_context()
            with pytest.raises(FileNotFoundError, match="Input file not found"):
                accounts_raw(context)
        finally:
            os.chdir(original_cwd)
    
    def test_accounts_raw_empty_file(self, tmp_path):
        """Test accounts_raw raises error with empty CSV file."""
        # Create an empty CSV file with headers only
        test_data_dir = tmp_path / "data" / "inputs"
        test_data_dir.mkdir(parents=True, exist_ok=True)
        test_csv = test_data_dir / "accounts.csv"
        
        df = pd.DataFrame(columns=["AccountID", "CustomerID", "Balance", "AccountType"])
        df.to_csv(test_csv, index=False)
        
        import os
        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            context = build_asset_context()
            with pytest.raises(ValueError, match="CSV file is empty"):
                accounts_raw(context)
        finally:
            os.chdir(original_cwd)
    
    def test_accounts_raw_missing_columns(self, tmp_path):
        """Test accounts_raw raises error when required columns are missing."""
        # Create a CSV file with missing columns
        test_data_dir = tmp_path / "data" / "inputs"
        test_data_dir.mkdir(parents=True, exist_ok=True)
        test_csv = test_data_dir / "accounts.csv"
        
        df = pd.DataFrame({
            "AccountID": ["A001", "A002"],
            "CustomerID": ["1", "2"],
            "Balance": ["5000.00", "15000.00"]
            # Missing AccountType column
        })
        df.to_csv(test_csv, index=False)
        
        import os
        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            context = build_asset_context()
            with pytest.raises(ValueError, match="Missing required columns"):
                accounts_raw(context)
        finally:
            os.chdir(original_cwd)
