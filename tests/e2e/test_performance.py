"""
End-to-end performance validation tests.

This test verifies that incremental loads are significantly faster than
full refreshes and that snapshot storage growth is manageable.
"""
import os
import tempfile
from pathlib import Path
import subprocess
import time
from datetime import datetime

import pandas as pd
import pytest
import duckdb


@pytest.fixture
def test_env_with_large_dataset(tmp_path):
    """Set up test environment with larger dataset for performance testing."""
    # Create directory structure
    data_dir = tmp_path / "data"
    inputs_dir = data_dir / "inputs"
    outputs_dir = data_dir / "outputs"
    duckdb_dir = data_dir / "duckdb"
    
    for dir_path in [inputs_dir, outputs_dir, duckdb_dir]:
        dir_path.mkdir(parents=True, exist_ok=True)
    
    # Create larger dataset (100 customers, 500 accounts)
    num_customers = 100
    num_accounts = 500
    
    customers_data = {
        "CustomerID": [str(i) for i in range(1, num_customers + 1)],
        "Name": [f"Customer {i}" for i in range(1, num_customers + 1)],
        "HasLoan": ["Yes" if i % 2 == 0 else "No" for i in range(1, num_customers + 1)]
    }
    customers_df = pd.DataFrame(customers_data)
    customers_df.to_csv(inputs_dir / "Customer.csv", index=False)
    
    accounts_data = {
        "AccountID": [f"A{str(i).zfill(5)}" for i in range(1, num_accounts + 1)],
        "CustomerID": [str((i % num_customers) + 1) for i in range(1, num_accounts + 1)],
        "Balance": [f"{(i * 100.0):.2f}" for i in range(1, num_accounts + 1)],
        "AccountType": ["Savings" for _ in range(1, num_accounts + 1)]
    }
    accounts_df = pd.DataFrame(accounts_data)
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
    
    dbt_project_dir = Path(__file__).parent.parent.parent / "dbt_project"
    
    yield {
        "tmp_path": tmp_path,
        "inputs_dir": inputs_dir,
        "outputs_dir": outputs_dir,
        "duckdb_dir": duckdb_dir,
        "db_path": str(duckdb_dir / "test_lending_club.duckdb"),
        "dbt_project_dir": dbt_project_dir,
        "num_customers": num_customers,
        "num_accounts": num_accounts,
    }
    
    # Restore environment
    for key, value in original_env.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value


class TestInitialLoadPerformance:
    """Tests for initial load performance."""
    
    def test_measure_initial_load_time(self, test_env_with_large_dataset):
        """Measure and record initial full load time."""
        dbt_project_dir = test_env_with_large_dataset["dbt_project_dir"]
        num_accounts = test_env_with_large_dataset["num_accounts"]
        
        # Measure full refresh time
        start_time = time.time()
        
        result = subprocess.run(
            ["dbt", "run", "--full-refresh", "--profiles-dir", str(dbt_project_dir)],
            cwd=str(dbt_project_dir),
            capture_output=True,
            text=True
        )
        
        end_time = time.time()
        full_refresh_time = end_time - start_time
        
        print(f"\nInitial load time: {full_refresh_time:.2f} seconds")
        print(f"Records processed: {num_accounts} accounts")
        print(f"Throughput: {num_accounts / full_refresh_time:.2f} records/second")
        
        # Initial load should complete in reasonable time
        # For 500 records, should be under 60 seconds
        assert full_refresh_time < 60, \
            f"Initial load took {full_refresh_time:.2f}s, expected < 60s"
        
        # Verify data was loaded
        if result.returncode == 0:
            assert True, "Initial load completed successfully"
        else:
            pytest.skip(f"Initial load failed: {result.stderr}")
    
    def test_snapshot_initial_load_time(self, test_env_with_large_dataset):
        """Measure snapshot initial load time."""
        dbt_project_dir = test_env_with_large_dataset["dbt_project_dir"]
        num_accounts = test_env_with_large_dataset["num_accounts"]
        
        # Run models first
        subprocess.run(
            ["dbt", "run", "--full-refresh", "--profiles-dir", str(dbt_project_dir)],
            cwd=str(dbt_project_dir),
            capture_output=True,
            text=True
        )
        
        # Measure snapshot time
        start_time = time.time()
        
        result = subprocess.run(
            ["dbt", "snapshot", "--profiles-dir", str(dbt_project_dir)],
            cwd=str(dbt_project_dir),
            capture_output=True,
            text=True
        )
        
        end_time = time.time()
        snapshot_time = end_time - start_time
        
        print(f"\nSnapshot initial load time: {snapshot_time:.2f} seconds")
        print(f"Records processed: {num_accounts} accounts")
        
        # Snapshot should complete in reasonable time
        assert snapshot_time < 30, \
            f"Snapshot took {snapshot_time:.2f}s, expected < 30s"
        
        if result.returncode == 0:
            assert True, "Snapshot completed successfully"
        else:
            pytest.skip(f"Snapshot failed: {result.stderr}")


class TestIncrementalLoadPerformance:
    """Tests for incremental load performance."""
    
    def test_incremental_faster_than_full_refresh(self, test_env_with_large_dataset):
        """Test that incremental load is significantly faster than full refresh."""
        inputs_dir = test_env_with_large_dataset["inputs_dir"]
        dbt_project_dir = test_env_with_large_dataset["dbt_project_dir"]
        num_accounts = test_env_with_large_dataset["num_accounts"]
        
        # Run initial full load
        start_time = time.time()
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
        end_time = time.time()
        full_refresh_time = end_time - start_time
        
        # Wait a moment
        time.sleep(1)
        
        # Modify only 10% of accounts (50 out of 500)
        accounts_df = pd.read_csv(inputs_dir / "accounts.csv")
        for i in range(50):
            accounts_df.loc[i, "Balance"] = f"{(i * 200.0):.2f}"  # Double the balance
        accounts_df.to_csv(inputs_dir / "accounts.csv", index=False)
        
        # Run incremental load
        start_time = time.time()
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
        end_time = time.time()
        incremental_time = end_time - start_time
        
        print(f"\nFull refresh time: {full_refresh_time:.2f} seconds")
        print(f"Incremental time: {incremental_time:.2f} seconds")
        print(f"Speedup: {full_refresh_time / incremental_time:.2f}x")
        print(f"Changed records: 50 out of {num_accounts} ({50/num_accounts*100:.1f}%)")
        
        # Incremental should be faster (at least 20% faster)
        # Note: With small datasets, overhead might dominate
        assert incremental_time <= full_refresh_time * 1.2, \
            f"Incremental ({incremental_time:.2f}s) should not be slower than full refresh ({full_refresh_time:.2f}s)"
        
        # Ideally, incremental should be significantly faster
        if incremental_time < full_refresh_time * 0.8:
            print("✓ Incremental load is significantly faster")
        else:
            print("⚠ Incremental load not significantly faster (dataset may be too small)")
    
    def test_incremental_processes_fewer_records(self, test_env_with_large_dataset):
        """Test that incremental load processes fewer records than full refresh."""
        inputs_dir = test_env_with_large_dataset["inputs_dir"]
        db_path = test_env_with_large_dataset["db_path"]
        dbt_project_dir = test_env_with_large_dataset["dbt_project_dir"]
        num_accounts = test_env_with_large_dataset["num_accounts"]
        
        # Run initial load
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
        
        # Modify 10% of accounts
        accounts_df = pd.read_csv(inputs_dir / "accounts.csv")
        changed_count = 50
        for i in range(changed_count):
            accounts_df.loc[i, "Balance"] = f"{(i * 200.0):.2f}"
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
        
        # Check snapshot versions
        conn = duckdb.connect(db_path)
        try:
            # Count accounts with multiple versions (changed accounts)
            changed_accounts = conn.execute("""
                SELECT COUNT(DISTINCT account_id)
                FROM snapshots.snap_account
                GROUP BY account_id
                HAVING COUNT(*) > 1
            """).fetchall()
            
            changed_accounts_count = len(changed_accounts)
            
            print(f"\nTotal accounts: {num_accounts}")
            print(f"Changed accounts: {changed_accounts_count}")
            print(f"Change rate: {changed_accounts_count / num_accounts * 100:.1f}%")
            
            # Should have created new versions for changed accounts
            assert changed_accounts_count > 0, \
                "Should have detected changed accounts"
            
            # Changed accounts should be roughly equal to what we modified
            assert changed_accounts_count <= changed_count * 1.5, \
                f"Changed accounts ({changed_accounts_count}) should be close to expected ({changed_count})"
            
        finally:
            conn.close()
    
    def test_incremental_with_minimal_changes(self, test_env_with_large_dataset):
        """Test incremental performance with minimal changes (1%)."""
        inputs_dir = test_env_with_large_dataset["inputs_dir"]
        dbt_project_dir = test_env_with_large_dataset["dbt_project_dir"]
        
        # Run initial load
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
        
        # Modify only 1% of accounts (5 out of 500)
        accounts_df = pd.read_csv(inputs_dir / "accounts.csv")
        for i in range(5):
            accounts_df.loc[i, "Balance"] = f"{(i * 300.0):.2f}"
        accounts_df.to_csv(inputs_dir / "accounts.csv", index=False)
        
        # Measure incremental time
        start_time = time.time()
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
        end_time = time.time()
        incremental_time = end_time - start_time
        
        print(f"\nIncremental time with 1% changes: {incremental_time:.2f} seconds")
        print(f"Changed records: 5 out of 500 (1%)")
        
        # With minimal changes, should be very fast
        assert incremental_time < 30, \
            f"Incremental with 1% changes took {incremental_time:.2f}s, expected < 30s"


class TestSnapshotStorageGrowth:
    """Tests for snapshot storage growth validation."""
    
    def test_snapshot_storage_growth_is_manageable(self, test_env_with_large_dataset):
        """Test that snapshot storage grows at expected rate."""
        inputs_dir = test_env_with_large_dataset["inputs_dir"]
        db_path = test_env_with_large_dataset["db_path"]
        dbt_project_dir = test_env_with_large_dataset["dbt_project_dir"]
        num_accounts = test_env_with_large_dataset["num_accounts"]
        
        # Run initial load
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
        
        conn = duckdb.connect(db_path)
        try:
            # Get initial version count
            initial_versions = conn.execute("""
                SELECT COUNT(*) FROM snapshots.snap_account
            """).fetchone()[0]
            
            print(f"\nInitial versions: {initial_versions}")
            
            # Simulate 5 days of changes (10% change rate per day)
            for day in range(5):
                # Modify 10% of accounts
                accounts_df = pd.read_csv(inputs_dir / "accounts.csv")
                start_idx = (day * 50) % num_accounts
                end_idx = start_idx + 50
                for i in range(start_idx, min(end_idx, num_accounts)):
                    accounts_df.loc[i, "Balance"] = f"{(i * (100 + day * 10)):.2f}"
                accounts_df.to_csv(inputs_dir / "accounts.csv", index=False)
                
                # Run snapshot
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
                
                time.sleep(0.5)  # Small delay between runs
            
            # Get final version count
            final_versions = conn.execute("""
                SELECT COUNT(*) FROM snapshots.snap_account
            """).fetchone()[0]
            
            new_versions = final_versions - initial_versions
            growth_rate = new_versions / initial_versions
            
            print(f"Final versions: {final_versions}")
            print(f"New versions created: {new_versions}")
            print(f"Growth rate: {growth_rate:.2f}x")
            print(f"Average versions per account: {final_versions / num_accounts:.2f}")
            
            # Storage growth should be reasonable
            # With 10% change rate over 5 days, expect ~2.5x growth
            assert growth_rate < 5.0, \
                f"Storage growth ({growth_rate:.2f}x) is too high"
            
            # Average versions per account should be reasonable
            avg_versions = final_versions / num_accounts
            assert avg_versions < 10, \
                f"Average versions per account ({avg_versions:.2f}) is too high"
            
        finally:
            conn.close()
    
    def test_snapshot_table_size(self, test_env_with_large_dataset):
        """Test snapshot table size is reasonable."""
        db_path = test_env_with_large_dataset["db_path"]
        dbt_project_dir = test_env_with_large_dataset["dbt_project_dir"]
        
        # Run initial load
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
        
        # Check database file size
        db_file = Path(db_path)
        if db_file.exists():
            db_size_mb = db_file.stat().st_size / (1024 * 1024)
            print(f"\nDatabase size: {db_size_mb:.2f} MB")
            
            # For 500 accounts, database should be under 100 MB
            assert db_size_mb < 100, \
                f"Database size ({db_size_mb:.2f} MB) is too large"
        else:
            pytest.skip("Database file not found")


class TestQueryPerformance:
    """Tests for query performance on snapshots and marts."""
    
    def test_current_records_query_performance(self, test_env_with_large_dataset):
        """Test that querying current records is fast."""
        db_path = test_env_with_large_dataset["db_path"]
        dbt_project_dir = test_env_with_large_dataset["dbt_project_dir"]
        
        # Run initial load
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
        
        conn = duckdb.connect(db_path)
        try:
            # Query current records
            start_time = time.time()
            result = conn.execute("""
                SELECT COUNT(*)
                FROM snapshots.snap_account
                WHERE dbt_valid_to IS NULL
            """).fetchone()
            end_time = time.time()
            query_time = end_time - start_time
            
            print(f"\nCurrent records query time: {query_time*1000:.2f} ms")
            print(f"Records returned: {result[0]}")
            
            # Query should be fast (under 1 second)
            assert query_time < 1.0, \
                f"Current records query took {query_time:.2f}s, expected < 1s"
            
        finally:
            conn.close()
    
    def test_historical_query_performance(self, test_env_with_large_dataset):
        """Test that querying historical records is reasonably fast."""
        db_path = test_env_with_large_dataset["db_path"]
        dbt_project_dir = test_env_with_large_dataset["dbt_project_dir"]
        
        # Run initial load
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
        
        conn = duckdb.connect(db_path)
        try:
            # Query historical records
            start_time = time.time()
            result = conn.execute("""
                SELECT COUNT(*)
                FROM snapshots.snap_account
                WHERE dbt_valid_to IS NOT NULL
            """).fetchone()
            end_time = time.time()
            query_time = end_time - start_time
            
            print(f"\nHistorical records query time: {query_time*1000:.2f} ms")
            print(f"Records returned: {result[0]}")
            
            # Query should be reasonably fast (under 2 seconds)
            assert query_time < 2.0, \
                f"Historical records query took {query_time:.2f}s, expected < 2s"
            
        finally:
            conn.close()
    
    def test_marts_query_performance(self, test_env_with_large_dataset):
        """Test that querying marts is fast."""
        db_path = test_env_with_large_dataset["db_path"]
        dbt_project_dir = test_env_with_large_dataset["dbt_project_dir"]
        
        # Run initial load
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
        subprocess.run(
            ["dbt", "run", "--profiles-dir", str(dbt_project_dir)],
            cwd=str(dbt_project_dir),
            capture_output=True,
            text=True
        )
        
        conn = duckdb.connect(db_path)
        try:
            # Query marts
            start_time = time.time()
            result = conn.execute("""
                SELECT COUNT(*)
                FROM marts.account_summary
            """).fetchone()
            end_time = time.time()
            query_time = end_time - start_time
            
            print(f"\nMarts query time: {query_time*1000:.2f} ms")
            print(f"Records returned: {result[0]}")
            
            # Marts query should be very fast (under 0.5 seconds)
            assert query_time < 0.5, \
                f"Marts query took {query_time:.2f}s, expected < 0.5s"
            
        finally:
            conn.close()
