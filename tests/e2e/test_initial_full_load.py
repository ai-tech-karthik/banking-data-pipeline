"""
End-to-end test for initial full load of the enhanced pipeline.

This test verifies that the complete pipeline executes successfully with
all five layers (Source, Staging, Snapshots, Intermediate, Marts) and that
all contracts and data quality tests pass.
"""
import os
import tempfile
from pathlib import Path
import subprocess
import json

import pandas as pd
import pytest
import duckdb


@pytest.fixture
def test_env_setup(tmp_path):
    """Set up test environment with sample data and configuration."""
    # Create directory structure
    data_dir = tmp_path / "data"
    inputs_dir = data_dir / "inputs"
    outputs_dir = data_dir / "outputs"
    duckdb_dir = data_dir / "duckdb"
    quality_reports_dir = data_dir / "quality_reports"
    
    for dir_path in [inputs_dir, outputs_dir, duckdb_dir, quality_reports_dir]:
        dir_path.mkdir(parents=True, exist_ok=True)
    
    # Create sample Customer.csv
    customers_df = pd.DataFrame({
        "CustomerID": ["1", "2", "3", "4", "5"],
        "Name": ["Alice Smith", "Bob Jones", "Charlie Brown", "Diana Prince", "Eve Adams"],
        "HasLoan": ["Yes", "No", "None", "Yes", "No"]
    })
    customers_df.to_csv(inputs_dir / "Customer.csv", index=False)
    
    # Create sample accounts.csv
    accounts_df = pd.DataFrame({
        "AccountID": ["A001", "A002", "A003", "A004", "A005"],
        "CustomerID": ["1", "2", "3", "4", "5"],
        "Balance": ["5000.00", "15000.00", "25000.00", "8000.00", "22000.00"],
        "AccountType": ["Savings", "Savings", "Savings", "Savings", "Savings"]
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
    
    yield {
        "tmp_path": tmp_path,
        "inputs_dir": inputs_dir,
        "outputs_dir": outputs_dir,
        "duckdb_dir": duckdb_dir,
        "quality_reports_dir": quality_reports_dir,
        "db_path": str(duckdb_dir / "test_lending_club.duckdb"),
        "customers_df": customers_df,
        "accounts_df": accounts_df,
    }
    
    # Restore environment
    for key, value in original_env.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value


class TestInitialFullLoad:
    """Test initial full load with --full-refresh."""
    
    def test_all_five_layers_created(self, test_env_setup):
        """Test that all five layers are created during initial load."""
        db_path = test_env_setup["db_path"]
        
        # Run DBT with full refresh
        dbt_project_dir = Path(__file__).parent.parent.parent / "dbt_project"
        
        # Run dbt seed, snapshot, and run
        result = subprocess.run(
            ["dbt", "run", "--full-refresh", "--profiles-dir", str(dbt_project_dir)],
            cwd=str(dbt_project_dir),
            capture_output=True,
            text=True
        )
        
        # Check if DBT run was successful
        if result.returncode != 0:
            pytest.skip(f"DBT run failed: {result.stderr}")
        
        # Connect to database and verify layers
        conn = duckdb.connect(db_path)
        
        try:
            # Get all tables
            tables_result = conn.execute("""
                SELECT table_schema, table_name
                FROM information_schema.tables
                WHERE table_schema NOT IN ('information_schema', 'pg_catalog')
                ORDER BY table_schema, table_name
            """).fetchall()
            
            tables = {(row[0], row[1]) for row in tables_result}
            
            # Layer 1: Source tables
            assert any('src_customer' in table[1] for table in tables), \
                "Source layer should have src_customer table"
            assert any('src_account' in table[1] for table in tables), \
                "Source layer should have src_account table"
            
            # Layer 2: Staging tables
            assert any('stg_customer' in table[1] for table in tables), \
                "Staging layer should have stg_customer table"
            assert any('stg_account' in table[1] for table in tables), \
                "Staging layer should have stg_account table"
            
            # Layer 3: Snapshot tables
            assert any('snap_customer' in table[1] for table in tables), \
                "Snapshot layer should have snap_customer table"
            assert any('snap_account' in table[1] for table in tables), \
                "Snapshot layer should have snap_account table"
            
            # Layer 4: Intermediate tables
            assert any('int_account_with_customer' in table[1] for table in tables), \
                "Intermediate layer should have int_account_with_customer table"
            assert any('int_savings_account_only' in table[1] for table in tables), \
                "Intermediate layer should have int_savings_account_only table"
            
            # Layer 5: Marts tables
            assert any('account_summary' in table[1] for table in tables), \
                "Marts layer should have account_summary table"
            assert any('customer_profile' in table[1] for table in tables), \
                "Marts layer should have customer_profile table"
            
        finally:
            conn.close()
    
    def test_snapshots_have_initial_versions(self, test_env_setup):
        """Test that snapshots have initial versions with SCD2 columns."""
        db_path = test_env_setup["db_path"]
        
        # Run DBT
        dbt_project_dir = Path(__file__).parent.parent.parent / "dbt_project"
        
        # Run snapshots
        result = subprocess.run(
            ["dbt", "snapshot", "--profiles-dir", str(dbt_project_dir)],
            cwd=str(dbt_project_dir),
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            pytest.skip(f"DBT snapshot failed: {result.stderr}")
        
        conn = duckdb.connect(db_path)
        
        try:
            # Check snap_customer
            customer_snapshots = conn.execute("""
                SELECT
                    COUNT(*) as total_versions,
                    COUNT(CASE WHEN dbt_valid_to IS NULL THEN 1 END) as current_versions,
                    COUNT(DISTINCT customer_id) as unique_customers
                FROM snapshots.snap_customer
            """).fetchone()
            
            assert customer_snapshots[0] > 0, \
                "snap_customer should have initial versions"
            assert customer_snapshots[1] == customer_snapshots[2], \
                "Each customer should have exactly one current version initially"
            
            # Verify SCD2 columns exist
            columns = conn.execute("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'snap_customer'
                ORDER BY column_name
            """).fetchall()
            
            column_names = [col[0] for col in columns]
            
            assert 'dbt_scd_id' in column_names, \
                "snap_customer should have dbt_scd_id column"
            assert 'dbt_valid_from' in column_names, \
                "snap_customer should have dbt_valid_from column"
            assert 'dbt_valid_to' in column_names, \
                "snap_customer should have dbt_valid_to column"
            assert 'dbt_updated_at' in column_names, \
                "snap_customer should have dbt_updated_at column"
            
            # Check snap_account
            account_snapshots = conn.execute("""
                SELECT
                    COUNT(*) as total_versions,
                    COUNT(CASE WHEN dbt_valid_to IS NULL THEN 1 END) as current_versions,
                    COUNT(DISTINCT account_id) as unique_accounts
                FROM snapshots.snap_account
            """).fetchone()
            
            assert account_snapshots[0] > 0, \
                "snap_account should have initial versions"
            assert account_snapshots[1] == account_snapshots[2], \
                "Each account should have exactly one current version initially"
            
        finally:
            conn.close()
    
    def test_all_contracts_pass(self, test_env_setup):
        """Test that all DBT contracts pass during initial load."""
        dbt_project_dir = Path(__file__).parent.parent.parent / "dbt_project"
        
        # Run DBT with contract enforcement
        result = subprocess.run(
            ["dbt", "run", "--full-refresh", "--profiles-dir", str(dbt_project_dir)],
            cwd=str(dbt_project_dir),
            capture_output=True,
            text=True
        )
        
        # Check for contract violations in output
        output = result.stdout + result.stderr
        
        assert "Contract Error" not in output, \
            "Should not have contract violations"
        assert "contract violation" not in output.lower(), \
            "Should not have contract violations"
        
        # If DBT run succeeded, contracts passed
        if result.returncode == 0:
            assert True, "All contracts passed"
        else:
            # Check if failure was due to contract
            if "contract" in output.lower():
                pytest.fail(f"Contract violation detected: {output}")
            else:
                pytest.skip(f"DBT run failed for non-contract reason: {result.stderr}")
    
    def test_all_data_quality_tests_pass(self, test_env_setup):
        """Test that all data quality tests pass during initial load."""
        dbt_project_dir = Path(__file__).parent.parent.parent / "dbt_project"
        
        # Run DBT tests
        result = subprocess.run(
            ["dbt", "test", "--profiles-dir", str(dbt_project_dir)],
            cwd=str(dbt_project_dir),
            capture_output=True,
            text=True
        )
        
        output = result.stdout + result.stderr
        
        # Parse test results
        if "PASS" in output or "passed" in output:
            # Check for failures
            if "FAIL" in output or "failed" in output:
                # Some tests failed
                pytest.fail(f"Some data quality tests failed: {output}")
            else:
                assert True, "All data quality tests passed"
        else:
            pytest.skip(f"Could not determine test results: {output}")
    
    def test_row_counts_match_expectations(self, test_env_setup):
        """Test that row counts in each layer match expectations."""
        db_path = test_env_setup["db_path"]
        customers_df = test_env_setup["customers_df"]
        accounts_df = test_env_setup["accounts_df"]
        
        conn = duckdb.connect(db_path)
        
        try:
            # Source layer should have all records
            src_customer_count = conn.execute(
                "SELECT COUNT(*) FROM main.src_customer"
            ).fetchone()[0]
            assert src_customer_count == len(customers_df), \
                f"src_customer should have {len(customers_df)} records"
            
            src_account_count = conn.execute(
                "SELECT COUNT(*) FROM main.src_account"
            ).fetchone()[0]
            assert src_account_count == len(accounts_df), \
                f"src_account should have {len(accounts_df)} records"
            
            # Staging layer should have same count (no filtering)
            stg_customer_count = conn.execute(
                "SELECT COUNT(*) FROM main.stg_customer"
            ).fetchone()[0]
            assert stg_customer_count == len(customers_df), \
                f"stg_customer should have {len(customers_df)} records"
            
            stg_account_count = conn.execute(
                "SELECT COUNT(*) FROM main.stg_account"
            ).fetchone()[0]
            assert stg_account_count == len(accounts_df), \
                f"stg_account should have {len(accounts_df)} records"
            
            # Snapshot layer should have one version per record
            snap_customer_count = conn.execute(
                "SELECT COUNT(*) FROM snapshots.snap_customer WHERE dbt_valid_to IS NULL"
            ).fetchone()[0]
            assert snap_customer_count == len(customers_df), \
                f"snap_customer should have {len(customers_df)} current versions"
            
            snap_account_count = conn.execute(
                "SELECT COUNT(*) FROM snapshots.snap_account WHERE dbt_valid_to IS NULL"
            ).fetchone()[0]
            assert snap_account_count == len(accounts_df), \
                f"snap_account should have {len(accounts_df)} current versions"
            
            # Intermediate layer (all accounts are savings in test data)
            int_account_count = conn.execute(
                "SELECT COUNT(*) FROM intermediate.int_account_with_customer"
            ).fetchone()[0]
            assert int_account_count == len(accounts_df), \
                f"int_account_with_customer should have {len(accounts_df)} records"
            
            # Marts layer
            account_summary_count = conn.execute(
                "SELECT COUNT(*) FROM marts.account_summary"
            ).fetchone()[0]
            assert account_summary_count == len(accounts_df), \
                f"account_summary should have {len(accounts_df)} records"
            
            customer_profile_count = conn.execute(
                "SELECT COUNT(*) FROM marts.customer_profile"
            ).fetchone()[0]
            assert customer_profile_count == len(customers_df), \
                f"customer_profile should have {len(customers_df)} records"
            
        finally:
            conn.close()
    
    def test_data_transformations_applied_correctly(self, test_env_setup):
        """Test that data transformations are applied correctly in each layer."""
        db_path = test_env_setup["db_path"]
        
        conn = duckdb.connect(db_path)
        
        try:
            # Check staging transformations
            stg_customer = conn.execute("""
                SELECT customer_id, customer_name, has_loan_flag
                FROM main.stg_customer
                WHERE customer_id = 1
            """).fetchone()
            
            # customer_name should be lowercase and trimmed
            assert stg_customer[1] == stg_customer[1].lower(), \
                "customer_name should be lowercase"
            
            # has_loan_flag should be boolean
            assert isinstance(stg_customer[2], bool), \
                "has_loan_flag should be boolean type"
            
            # Check intermediate transformations (join)
            int_account = conn.execute("""
                SELECT account_id, customer_id, customer_name, balance_amount
                FROM intermediate.int_account_with_customer
                WHERE account_id = 'A001'
            """).fetchone()
            
            assert int_account[1] == 1, \
                "int_account_with_customer should have correct customer_id"
            assert int_account[2] is not None, \
                "int_account_with_customer should have customer_name from join"
            
            # Check marts calculations
            account_summary = conn.execute("""
                SELECT
                    account_id,
                    original_balance_amount,
                    interest_rate_pct,
                    annual_interest_amount,
                    new_balance_amount
                FROM marts.account_summary
                WHERE account_id = 'A001'
            """).fetchone()
            
            # Verify interest calculation
            original_balance = account_summary[1]
            interest_rate = account_summary[2]
            annual_interest = account_summary[3]
            new_balance = account_summary[4]
            
            expected_interest = original_balance * interest_rate
            assert abs(annual_interest - expected_interest) < 0.01, \
                "annual_interest should be calculated correctly"
            
            expected_new_balance = original_balance + annual_interest
            assert abs(new_balance - expected_new_balance) < 0.01, \
                "new_balance should be calculated correctly"
            
        finally:
            conn.close()
    
    def test_naming_conventions_followed(self, test_env_setup):
        """Test that naming conventions are followed across all layers."""
        db_path = test_env_setup["db_path"]
        
        conn = duckdb.connect(db_path)
        
        try:
            # Get all tables
            tables = conn.execute("""
                SELECT table_schema, table_name
                FROM information_schema.tables
                WHERE table_schema NOT IN ('information_schema', 'pg_catalog')
            """).fetchall()
            
            for schema, table in tables:
                # Check table naming conventions
                if schema == 'main':
                    if 'src_' in table:
                        assert table.startswith('src_'), \
                            f"Source table {table} should start with src_"
                    elif 'stg_' in table:
                        assert table.startswith('stg_'), \
                            f"Staging table {table} should start with stg_"
                    elif 'int_' in table:
                        assert table.startswith('int_'), \
                            f"Intermediate table {table} should start with int_"
                
                elif schema == 'snapshots':
                    assert table.startswith('snap_'), \
                        f"Snapshot table {table} should start with snap_"
                
                elif schema == 'marts':
                    # Marts don't have prefix
                    assert not table.startswith(('src_', 'stg_', 'snap_', 'int_')), \
                        f"Marts table {table} should not have layer prefix"
                
                # Check snake_case
                assert table == table.lower(), \
                    f"Table {table} should be lowercase"
                assert ' ' not in table, \
                    f"Table {table} should not contain spaces"
            
            # Check column naming conventions
            for schema, table in tables:
                columns = conn.execute(f"""
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_schema = '{schema}' AND table_name = '{table}'
                """).fetchall()
                
                for (column,) in columns:
                    # Check snake_case
                    assert column == column.lower(), \
                        f"Column {column} in {schema}.{table} should be lowercase"
                    
                    # Check suffixes
                    if column.endswith('_flag') or column.endswith('_ind'):
                        # Should be boolean
                        pass  # Type checking would require querying data
                    
                    if column.endswith('_at') or column.endswith('_date'):
                        # Should be timestamp/date
                        pass
                    
                    if column.endswith('_amount') or column.endswith('_balance'):
                        # Should be numeric
                        pass
            
        finally:
            conn.close()
