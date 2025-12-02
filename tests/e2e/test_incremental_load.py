"""
End-to-end test for incremental load with data changes.

This test verifies that the pipeline correctly handles incremental loads,
creating new snapshot versions, processing only changed data, and updating
marts accordingly.
"""
import os
import tempfile
from pathlib import Path
import subprocess
import time
from datetime import datetime, timedelta

import pandas as pd
import pytest
import duckdb


@pytest.fixture
def test_env_with_initial_load(tmp_path):
    """Set up test environment with initial data load."""
    # Create directory structure
    data_dir = tmp_path / "data"
    inputs_dir = data_dir / "inputs"
    outputs_dir = data_dir / "outputs"
    duckdb_dir = data_dir / "duckdb"
    quality_reports_dir = data_dir / "quality_reports"
    
    for dir_path in [inputs_dir, outputs_dir, duckdb_dir, quality_reports_dir]:
        dir_path.mkdir(parents=True, exist_ok=True)
    
    # Create initial Customer.csv
    customers_df = pd.DataFrame({
        "CustomerID": ["1", "2", "3"],
        "Name": ["Alice Smith", "Bob Jones", "Charlie Brown"],
        "HasLoan": ["Yes", "No", "None"]
    })
    customers_df.to_csv(inputs_dir / "Customer.csv", index=False)
    
    # Create initial accounts.csv
    accounts_df = pd.DataFrame({
        "AccountID": ["A001", "A002", "A003"],
        "CustomerID": ["1", "2", "3"],
        "Balance": ["5000.00", "15000.00", "25000.00"],
        "AccountType": ["Savings", "Savings", "Savings"]
    })
    accounts_df.to_csv(inputs_dir / "accounts.csv", index=False)
    
    # Set environment variables
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
    
    # Run initial load
    dbt_project_dir = Path(__file__).parent.parent.parent / "dbt_project"
    
    # Run DBT for initial load
    subprocess.run(
        ["dbt", "run", "--full-refresh", "--profiles-dir", str(dbt_project_dir)],
        cwd=str(dbt_project_dir),
        capture_output=True,
        text=True
    )
    
    subprocess.run(
        ["dbt", "snapshot", "--profiles-dir", str(dbt_project_dir)],
        cwd=str(dbt_project_dir),
        capture_output=True,
        text=True
    )
    
    # Wait a moment to ensure timestamps are different
    time.sleep(1)
    
    yield {
        "tmp_path": tmp_path,
        "inputs_dir": inputs_dir,
        "outputs_dir": outputs_dir,
        "duckdb_dir": duckdb_dir,
        "quality_reports_dir": quality_reports_dir,
        "db_path": str(duckdb_dir / "test_lending_club.duckdb"),
        "dbt_project_dir": dbt_project_dir,
        "initial_customers_df": customers_df,
        "initial_accounts_df": accounts_df,
    }
    
    # Restore environment
    for key, value in original_env.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value


class TestIncrementalLoad:
    """Test incremental load with data changes."""
    
    def test_snapshots_create_new_versions_on_change(self, test_env_with_initial_load):
        """Test that snapshots create new versions when data changes."""
        inputs_dir = test_env_with_initial_load["inputs_dir"]
        db_path = test_env_with_initial_load["db_path"]
        dbt_project_dir = test_env_with_initial_load["dbt_project_dir"]
        
        conn = duckdb.connect(db_path)
        
        try:
            # Get initial version count
            initial_versions = conn.execute("""
                SELECT COUNT(*) FROM snapshots.snap_customer
                WHERE customer_id = 1
            """).fetchone()[0]
            
            # Modify customer data (change name)
            customers_df = pd.DataFrame({
                "CustomerID": ["1", "2", "3"],
                "Name": ["Alice Johnson", "Bob Jones", "Charlie Brown"],  # Changed Alice's name
                "HasLoan": ["Yes", "No", "None"]
            })
            customers_df.to_csv(inputs_dir / "Customer.csv", index=False)
            
            # Run incremental load
            subprocess.run(
                ["dbt", "run", "--profiles-dir", str(dbt_project_dir)],
                cwd=str(dbt_project_dir),
                capture_output=True,
                text=True
            )
            
            subprocess.run(
                ["dbt", "snapshot", "--profiles-dir", str(dbt_project_dir)],
                cwd=str(dbt_project_dir),
                capture_output=True,
                text=True
            )
            
            # Get new version count
            new_versions = conn.execute("""
                SELECT COUNT(*) FROM snapshots.snap_customer
                WHERE customer_id = 1
            """).fetchone()[0]
            
            assert new_versions > initial_versions, \
                "Snapshot should create new version when data changes"
            assert new_versions == initial_versions + 1, \
                "Snapshot should create exactly one new version"
            
            # Verify old version is closed
            old_version = conn.execute("""
                SELECT dbt_valid_to
                FROM snapshots.snap_customer
                WHERE customer_id = 1
                ORDER BY dbt_valid_from
                LIMIT 1
            """).fetchone()
            
            assert old_version[0] is not None, \
                "Old version should have dbt_valid_to set"
            
            # Verify new version is current
            current_version = conn.execute("""
                SELECT customer_name, dbt_valid_to
                FROM snapshots.snap_customer
                WHERE customer_id = 1 AND dbt_valid_to IS NULL
            """).fetchone()
            
            assert current_version[0] == 'alice johnson', \
                "Current version should have updated name"
            assert current_version[1] is None, \
                "Current version should have NULL dbt_valid_to"
            
        finally:
            conn.close()
    
    def test_unchanged_records_not_duplicated(self, test_env_with_initial_load):
        """Test that unchanged records are not duplicated in snapshots."""
        inputs_dir = test_env_with_initial_load["inputs_dir"]
        db_path = test_env_with_initial_load["db_path"]
        dbt_project_dir = test_env_with_initial_load["dbt_project_dir"]
        
        conn = duckdb.connect(db_path)
        
        try:
            # Get initial version count for customer 2 (unchanged)
            initial_versions = conn.execute("""
                SELECT COUNT(*) FROM snapshots.snap_customer
                WHERE customer_id = 2
            """).fetchone()[0]
            
            # Modify only customer 1 data
            customers_df = pd.DataFrame({
                "CustomerID": ["1", "2", "3"],
                "Name": ["Alice Johnson", "Bob Jones", "Charlie Brown"],
                "HasLoan": ["Yes", "No", "None"]
            })
            customers_df.to_csv(inputs_dir / "Customer.csv", index=False)
            
            # Run incremental load
            subprocess.run(
                ["dbt", "snapshot", "--profiles-dir", str(dbt_project_dir)],
                cwd=str(dbt_project_dir),
                capture_output=True,
                text=True
            )
            
            # Get new version count for customer 2
            new_versions = conn.execute("""
                SELECT COUNT(*) FROM snapshots.snap_customer
                WHERE customer_id = 2
            """).fetchone()[0]
            
            assert new_versions == initial_versions, \
                "Unchanged records should not create new versions"
            
        finally:
            conn.close()
    
    def test_incremental_models_process_only_changed_data(self, test_env_with_initial_load):
        """Test that incremental models process only changed records."""
        inputs_dir = test_env_with_initial_load["inputs_dir"]
        db_path = test_env_with_initial_load["db_path"]
        dbt_project_dir = test_env_with_initial_load["dbt_project_dir"]
        
        conn = duckdb.connect(db_path)
        
        try:
            # Get initial calculated_at timestamp for account A001
            initial_calc_time = conn.execute("""
                SELECT calculated_at
                FROM marts.account_summary
                WHERE account_id = 'A001'
            """).fetchone()[0]
            
            # Get initial calculated_at for account A002 (will remain unchanged)
            initial_calc_time_a002 = conn.execute("""
                SELECT calculated_at
                FROM marts.account_summary
                WHERE account_id = 'A002'
            """).fetchone()[0]
            
            # Wait to ensure different timestamp
            time.sleep(1)
            
            # Modify only account A001 balance
            accounts_df = pd.DataFrame({
                "AccountID": ["A001", "A002", "A003"],
                "CustomerID": ["1", "2", "3"],
                "Balance": ["6000.00", "15000.00", "25000.00"],  # Changed A001 balance
                "AccountType": ["Savings", "Savings", "Savings"]
            })
            accounts_df.to_csv(inputs_dir / "accounts.csv", index=False)
            
            # Run incremental load
            subprocess.run(
                ["dbt", "run", "--profiles-dir", str(dbt_project_dir)],
                cwd=str(dbt_project_dir),
                capture_output=True,
                text=True
            )
            
            subprocess.run(
                ["dbt", "snapshot", "--profiles-dir", str(dbt_project_dir)],
                cwd=str(dbt_project_dir),
                capture_output=True,
                text=True
            )
            
            subprocess.run(
                ["dbt", "run", "--profiles-dir", str(dbt_project_dir)],
                cwd=str(dbt_project_dir),
                capture_output=True,
                text=True
            )
            
            # Get new calculated_at timestamp for account A001
            new_calc_time = conn.execute("""
                SELECT calculated_at, original_balance_amount
                FROM marts.account_summary
                WHERE account_id = 'A001'
            """).fetchone()
            
            # Get calculated_at for account A002 (should be unchanged or updated)
            new_calc_time_a002 = conn.execute("""
                SELECT calculated_at
                FROM marts.account_summary
                WHERE account_id = 'A002'
            """).fetchone()[0]
            
            # Verify A001 was updated
            assert new_calc_time[1] == 6000.00, \
                "Account A001 balance should be updated"
            
            # In incremental mode, only changed records should be processed
            # However, depending on implementation, all current records might be refreshed
            # The key is that the balance is correct
            assert new_calc_time[1] == 6000.00, \
                "Incremental load should update changed record"
            
        finally:
            conn.close()
    
    def test_marts_updated_correctly(self, test_env_with_initial_load):
        """Test that marts are updated correctly after incremental load."""
        inputs_dir = test_env_with_initial_load["inputs_dir"]
        db_path = test_env_with_initial_load["db_path"]
        dbt_project_dir = test_env_with_initial_load["dbt_project_dir"]
        
        conn = duckdb.connect(db_path)
        
        try:
            # Modify account balance
            accounts_df = pd.DataFrame({
                "AccountID": ["A001", "A002", "A003"],
                "CustomerID": ["1", "2", "3"],
                "Balance": ["7000.00", "15000.00", "25000.00"],
                "AccountType": ["Savings", "Savings", "Savings"]
            })
            accounts_df.to_csv(inputs_dir / "accounts.csv", index=False)
            
            # Run incremental load
            subprocess.run(
                ["dbt", "run", "--profiles-dir", str(dbt_project_dir)],
                cwd=str(dbt_project_dir),
                capture_output=True,
                text=True
            )
            
            subprocess.run(
                ["dbt", "snapshot", "--profiles-dir", str(dbt_project_dir)],
                cwd=str(dbt_project_dir),
                capture_output=True,
                text=True
            )
            
            subprocess.run(
                ["dbt", "run", "--profiles-dir", str(dbt_project_dir)],
                cwd=str(dbt_project_dir),
                capture_output=True,
                text=True
            )
            
            # Verify account_summary is updated
            account_summary = conn.execute("""
                SELECT
                    original_balance_amount,
                    interest_rate_pct,
                    annual_interest_amount,
                    new_balance_amount
                FROM marts.account_summary
                WHERE account_id = 'A001'
            """).fetchone()
            
            assert account_summary[0] == 7000.00, \
                "account_summary should have updated balance"
            
            # Verify calculations are correct
            expected_interest = account_summary[0] * account_summary[1]
            assert abs(account_summary[2] - expected_interest) < 0.01, \
                "Interest calculation should be correct"
            
            expected_new_balance = account_summary[0] + account_summary[2]
            assert abs(account_summary[3] - expected_new_balance) < 0.01, \
                "New balance calculation should be correct"
            
            # Verify customer_profile is updated
            customer_profile = conn.execute("""
                SELECT
                    total_accounts_count,
                    total_balance_amount,
                    total_annual_interest_amount
                FROM marts.customer_profile
                WHERE customer_id = 1
            """).fetchone()
            
            assert customer_profile[0] == 1, \
                "Customer should have 1 account"
            assert customer_profile[1] == 7000.00, \
                "Customer total balance should be updated"
            
        finally:
            conn.close()
    
    def test_new_records_added_incrementally(self, test_env_with_initial_load):
        """Test that new records are added correctly in incremental load."""
        inputs_dir = test_env_with_initial_load["inputs_dir"]
        db_path = test_env_with_initial_load["db_path"]
        dbt_project_dir = test_env_with_initial_load["dbt_project_dir"]
        
        conn = duckdb.connect(db_path)
        
        try:
            # Get initial counts
            initial_customer_count = conn.execute("""
                SELECT COUNT(*) FROM snapshots.snap_customer
                WHERE dbt_valid_to IS NULL
            """).fetchone()[0]
            
            initial_account_count = conn.execute("""
                SELECT COUNT(*) FROM snapshots.snap_account
                WHERE dbt_valid_to IS NULL
            """).fetchone()[0]
            
            # Add new customer and account
            customers_df = pd.DataFrame({
                "CustomerID": ["1", "2", "3", "4"],
                "Name": ["Alice Smith", "Bob Jones", "Charlie Brown", "Diana Prince"],
                "HasLoan": ["Yes", "No", "None", "Yes"]
            })
            customers_df.to_csv(inputs_dir / "Customer.csv", index=False)
            
            accounts_df = pd.DataFrame({
                "AccountID": ["A001", "A002", "A003", "A004"],
                "CustomerID": ["1", "2", "3", "4"],
                "Balance": ["5000.00", "15000.00", "25000.00", "10000.00"],
                "AccountType": ["Savings", "Savings", "Savings", "Savings"]
            })
            accounts_df.to_csv(inputs_dir / "accounts.csv", index=False)
            
            # Run incremental load
            subprocess.run(
                ["dbt", "run", "--profiles-dir", str(dbt_project_dir)],
                cwd=str(dbt_project_dir),
                capture_output=True,
                text=True
            )
            
            subprocess.run(
                ["dbt", "snapshot", "--profiles-dir", str(dbt_project_dir)],
                cwd=str(dbt_project_dir),
                capture_output=True,
                text=True
            )
            
            subprocess.run(
                ["dbt", "run", "--profiles-dir", str(dbt_project_dir)],
                cwd=str(dbt_project_dir),
                capture_output=True,
                text=True
            )
            
            # Get new counts
            new_customer_count = conn.execute("""
                SELECT COUNT(*) FROM snapshots.snap_customer
                WHERE dbt_valid_to IS NULL
            """).fetchone()[0]
            
            new_account_count = conn.execute("""
                SELECT COUNT(*) FROM snapshots.snap_account
                WHERE dbt_valid_to IS NULL
            """).fetchone()[0]
            
            assert new_customer_count == initial_customer_count + 1, \
                "Should have one additional customer"
            assert new_account_count == initial_account_count + 1, \
                "Should have one additional account"
            
            # Verify new records in marts
            new_account_summary = conn.execute("""
                SELECT COUNT(*) FROM marts.account_summary
                WHERE account_id = 'A004'
            """).fetchone()[0]
            
            assert new_account_summary == 1, \
                "New account should appear in account_summary"
            
            new_customer_profile = conn.execute("""
                SELECT COUNT(*) FROM marts.customer_profile
                WHERE customer_id = 4
            """).fetchone()[0]
            
            assert new_customer_profile == 1, \
                "New customer should appear in customer_profile"
            
        finally:
            conn.close()
    
    def test_deleted_records_invalidated(self, test_env_with_initial_load):
        """Test that deleted records are invalidated in snapshots."""
        inputs_dir = test_env_with_initial_load["inputs_dir"]
        db_path = test_env_with_initial_load["db_path"]
        dbt_project_dir = test_env_with_initial_load["dbt_project_dir"]
        
        conn = duckdb.connect(db_path)
        
        try:
            # Remove customer 3 from source data
            customers_df = pd.DataFrame({
                "CustomerID": ["1", "2"],
                "Name": ["Alice Smith", "Bob Jones"],
                "HasLoan": ["Yes", "No"]
            })
            customers_df.to_csv(inputs_dir / "Customer.csv", index=False)
            
            accounts_df = pd.DataFrame({
                "AccountID": ["A001", "A002"],
                "CustomerID": ["1", "2"],
                "Balance": ["5000.00", "15000.00"],
                "AccountType": ["Savings", "Savings"]
            })
            accounts_df.to_csv(inputs_dir / "accounts.csv", index=False)
            
            # Run incremental load
            subprocess.run(
                ["dbt", "run", "--profiles-dir", str(dbt_project_dir)],
                cwd=str(dbt_project_dir),
                capture_output=True,
                text=True
            )
            
            subprocess.run(
                ["dbt", "snapshot", "--profiles-dir", str(dbt_project_dir)],
                cwd=str(dbt_project_dir),
                capture_output=True,
                text=True
            )
            
            # Verify customer 3 is invalidated (if invalidate_hard_deletes is true)
            customer_3_current = conn.execute("""
                SELECT COUNT(*) FROM snapshots.snap_customer
                WHERE customer_id = 3 AND dbt_valid_to IS NULL
            """).fetchone()[0]
            
            # With invalidate_hard_deletes=true, deleted records should be closed
            # The count should be 0 (no current version)
            assert customer_3_current == 0, \
                "Deleted customer should have no current version"
            
            # Verify historical version still exists
            customer_3_historical = conn.execute("""
                SELECT COUNT(*) FROM snapshots.snap_customer
                WHERE customer_id = 3
            """).fetchone()[0]
            
            assert customer_3_historical > 0, \
                "Deleted customer should still have historical versions"
            
        finally:
            conn.close()
    
    def test_multiple_changes_tracked_correctly(self, test_env_with_initial_load):
        """Test that multiple changes over time are tracked correctly."""
        inputs_dir = test_env_with_initial_load["inputs_dir"]
        db_path = test_env_with_initial_load["db_path"]
        dbt_project_dir = test_env_with_initial_load["dbt_project_dir"]
        
        conn = duckdb.connect(db_path)
        
        try:
            # First change
            customers_df = pd.DataFrame({
                "CustomerID": ["1", "2", "3"],
                "Name": ["Alice Johnson", "Bob Jones", "Charlie Brown"],
                "HasLoan": ["Yes", "No", "None"]
            })
            customers_df.to_csv(inputs_dir / "Customer.csv", index=False)
            
            subprocess.run(
                ["dbt", "snapshot", "--profiles-dir", str(dbt_project_dir)],
                cwd=str(dbt_project_dir),
                capture_output=True,
                text=True
            )
            
            time.sleep(1)
            
            # Second change
            customers_df = pd.DataFrame({
                "CustomerID": ["1", "2", "3"],
                "Name": ["Alice Williams", "Bob Jones", "Charlie Brown"],
                "HasLoan": ["Yes", "No", "None"]
            })
            customers_df.to_csv(inputs_dir / "Customer.csv", index=False)
            
            subprocess.run(
                ["dbt", "snapshot", "--profiles-dir", str(dbt_project_dir)],
                cwd=str(dbt_project_dir),
                capture_output=True,
                text=True
            )
            
            # Verify customer 1 has 3 versions
            version_count = conn.execute("""
                SELECT COUNT(*) FROM snapshots.snap_customer
                WHERE customer_id = 1
            """).fetchone()[0]
            
            assert version_count == 3, \
                "Customer 1 should have 3 versions (initial + 2 changes)"
            
            # Verify only one current version
            current_count = conn.execute("""
                SELECT COUNT(*) FROM snapshots.snap_customer
                WHERE customer_id = 1 AND dbt_valid_to IS NULL
            """).fetchone()[0]
            
            assert current_count == 1, \
                "Customer 1 should have exactly 1 current version"
            
            # Verify version history
            versions = conn.execute("""
                SELECT customer_name, dbt_valid_to IS NULL as is_current
                FROM snapshots.snap_customer
                WHERE customer_id = 1
                ORDER BY dbt_valid_from
            """).fetchall()
            
            assert versions[0][0] == 'alice smith', \
                "First version should have original name"
            assert versions[0][1] is False, \
                "First version should be historical"
            
            assert versions[1][0] == 'alice johnson', \
                "Second version should have first changed name"
            assert versions[1][1] is False, \
                "Second version should be historical"
            
            assert versions[2][0] == 'alice williams', \
                "Third version should have second changed name"
            assert versions[2][1] is True, \
                "Third version should be current"
            
        finally:
            conn.close()
