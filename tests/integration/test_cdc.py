"""
Integration tests for CDC (Change Data Capture) functionality.

These tests verify that incremental models correctly process only changed
records, improving performance while maintaining data accuracy.
"""
import os
import tempfile
from pathlib import Path
from datetime import datetime, timedelta

import pandas as pd
import pytest
import duckdb


@pytest.fixture
def test_database(tmp_path):
    """Create a temporary DuckDB database for testing."""
    db_path = tmp_path / "test_cdc.duckdb"
    
    # Create database and initialize schemas
    conn = duckdb.connect(str(db_path))
    conn.execute("CREATE SCHEMA IF NOT EXISTS main")
    conn.execute("CREATE SCHEMA IF NOT EXISTS snapshots")
    conn.execute("CREATE SCHEMA IF NOT EXISTS intermediate")
    conn.execute("CREATE SCHEMA IF NOT EXISTS marts")
    conn.close()
    
    yield str(db_path)
    
    # Cleanup
    if db_path.exists():
        db_path.unlink()


class TestCDCIncrementalProcessing:
    """Tests for incremental processing of changed records only."""
    
    def test_incremental_processes_only_new_records(self, test_database):
        """Test that incremental models process only records with new dbt_valid_from."""
        conn = duckdb.connect(test_database)
        
        try:
            # Create snapshot with initial data
            conn.execute("""
                CREATE TABLE snapshots.snap_account AS
                SELECT
                    'a1v1' as dbt_scd_id,
                    TIMESTAMP '2024-01-01 10:00:00' as dbt_updated_at,
                    TIMESTAMP '2024-01-01 10:00:00' as dbt_valid_from,
                    CAST(NULL AS TIMESTAMP) as dbt_valid_to,
                    'A001' as account_id,
                    1 as customer_id,
                    5000.00 as balance_amount,
                    'Savings' as account_type,
                    TIMESTAMP '2024-01-01 10:00:00' as loaded_at
            """)
            
            conn.execute("""
                CREATE TABLE snapshots.snap_customer AS
                SELECT
                    'c1v1' as dbt_scd_id,
                    TIMESTAMP '2024-01-01 10:00:00' as dbt_updated_at,
                    TIMESTAMP '2024-01-01 10:00:00' as dbt_valid_from,
                    CAST(NULL AS TIMESTAMP) as dbt_valid_to,
                    1 as customer_id,
                    'Alice Smith' as customer_name,
                    true as has_loan_flag,
                    TIMESTAMP '2024-01-01 10:00:00' as loaded_at
            """)
            
            # Create intermediate table (initial load)
            conn.execute("""
                CREATE TABLE intermediate.int_account_with_customer AS
                SELECT
                    a.account_id,
                    a.customer_id,
                    a.balance_amount,
                    a.account_type,
                    c.customer_name,
                    c.has_loan_flag,
                    a.dbt_valid_from as valid_from_at,
                    a.dbt_valid_to as valid_to_at
                FROM snapshots.snap_account a
                INNER JOIN snapshots.snap_customer c
                    ON a.customer_id = c.customer_id
                WHERE a.dbt_valid_to IS NULL
                    AND c.dbt_valid_to IS NULL
            """)
            
            initial_count = conn.execute("""
                SELECT COUNT(*) FROM intermediate.int_account_with_customer
            """).fetchone()[0]
            
            # Add new version to snapshot (simulating a change)
            conn.execute("""
                UPDATE snapshots.snap_account
                SET dbt_valid_to = TIMESTAMP '2024-01-02 10:00:00'
                WHERE account_id = 'A001'
            """)
            
            conn.execute("""
                INSERT INTO snapshots.snap_account
                SELECT
                    'a1v2' as dbt_scd_id,
                    TIMESTAMP '2024-01-02 10:00:00' as dbt_updated_at,
                    TIMESTAMP '2024-01-02 10:00:00' as dbt_valid_from,
                    CAST(NULL AS TIMESTAMP) as dbt_valid_to,
                    'A001' as account_id,
                    1 as customer_id,
                    6000.00 as balance_amount,  -- Changed balance
                    'Savings' as account_type,
                    TIMESTAMP '2024-01-02 10:00:00' as loaded_at
            """)
            
            # Simulate incremental run (process only new records)
            max_valid_from = conn.execute("""
                SELECT MAX(valid_from_at) FROM intermediate.int_account_with_customer
            """).fetchone()[0]
            
            # Delete old version and insert new version (merge behavior)
            conn.execute("""
                DELETE FROM intermediate.int_account_with_customer
                WHERE account_id = 'A001'
            """)
            
            conn.execute(f"""
                INSERT INTO intermediate.int_account_with_customer
                SELECT
                    a.account_id,
                    a.customer_id,
                    a.balance_amount,
                    a.account_type,
                    c.customer_name,
                    c.has_loan_flag,
                    a.dbt_valid_from as valid_from_at,
                    a.dbt_valid_to as valid_to_at
                FROM snapshots.snap_account a
                INNER JOIN snapshots.snap_customer c
                    ON a.customer_id = c.customer_id
                WHERE a.dbt_valid_to IS NULL
                    AND c.dbt_valid_to IS NULL
                    AND a.dbt_valid_from > TIMESTAMP '{max_valid_from}'
            """)
            
            # Verify only changed record was processed
            final_count = conn.execute("""
                SELECT COUNT(*) FROM intermediate.int_account_with_customer
            """).fetchone()[0]
            
            assert final_count == initial_count, \
                "Incremental run should maintain same record count (merge behavior)"
            
            # Verify balance was updated
            new_balance = conn.execute("""
                SELECT balance_amount FROM intermediate.int_account_with_customer
                WHERE account_id = 'A001'
            """).fetchone()[0]
            
            assert new_balance == 6000.00, \
                "Incremental run should update changed record"
            
        finally:
            conn.close()
    
    def test_incremental_skips_unchanged_records(self, test_database):
        """Test that incremental models skip unchanged records."""
        conn = duckdb.connect(test_database)
        
        try:
            # Create snapshots with multiple accounts
            conn.execute("""
                CREATE TABLE snapshots.snap_account AS
                SELECT
                    'a1v1' as dbt_scd_id,
                    TIMESTAMP '2024-01-01 10:00:00' as dbt_updated_at,
                    TIMESTAMP '2024-01-01 10:00:00' as dbt_valid_from,
                    CAST(NULL AS TIMESTAMP) as dbt_valid_to,
                    'A001' as account_id,
                    1 as customer_id,
                    5000.00 as balance_amount,
                    'Savings' as account_type,
                    TIMESTAMP '2024-01-01 10:00:00' as loaded_at
                UNION ALL
                SELECT
                    'a2v1' as dbt_scd_id,
                    TIMESTAMP '2024-01-01 10:00:00' as dbt_updated_at,
                    TIMESTAMP '2024-01-01 10:00:00' as dbt_valid_from,
                    CAST(NULL AS TIMESTAMP) as dbt_valid_to,
                    'A002' as account_id,
                    2 as customer_id,
                    10000.00 as balance_amount,
                    'Savings' as account_type,
                    TIMESTAMP '2024-01-01 10:00:00' as loaded_at
            """)
            
            conn.execute("""
                CREATE TABLE snapshots.snap_customer AS
                SELECT
                    'c1v1' as dbt_scd_id,
                    TIMESTAMP '2024-01-01 10:00:00' as dbt_updated_at,
                    TIMESTAMP '2024-01-01 10:00:00' as dbt_valid_from,
                    CAST(NULL AS TIMESTAMP) as dbt_valid_to,
                    1 as customer_id,
                    'Alice Smith' as customer_name,
                    true as has_loan_flag,
                    TIMESTAMP '2024-01-01 10:00:00' as loaded_at
                UNION ALL
                SELECT
                    'c2v1' as dbt_scd_id,
                    TIMESTAMP '2024-01-01 10:00:00' as dbt_updated_at,
                    TIMESTAMP '2024-01-01 10:00:00' as dbt_valid_from,
                    CAST(NULL AS TIMESTAMP) as dbt_valid_to,
                    2 as customer_id,
                    'Bob Jones' as customer_name,
                    false as has_loan_flag,
                    TIMESTAMP '2024-01-01 10:00:00' as loaded_at
            """)
            
            # Create marts table (initial load)
            conn.execute("""
                CREATE TABLE marts.account_summary AS
                SELECT
                    account_id,
                    customer_id,
                    balance_amount as original_balance_amount,
                    0.01 as interest_rate_pct,
                    balance_amount * 0.01 as annual_interest_amount,
                    balance_amount * 1.01 as new_balance_amount,
                    TIMESTAMP '2024-01-01 10:00:00' as calculated_at
                FROM snapshots.snap_account
                WHERE dbt_valid_to IS NULL
            """)
            
            # Change only one account
            conn.execute("""
                UPDATE snapshots.snap_account
                SET dbt_valid_to = TIMESTAMP '2024-01-02 10:00:00'
                WHERE account_id = 'A001'
            """)
            
            conn.execute("""
                INSERT INTO snapshots.snap_account
                SELECT
                    'a1v2' as dbt_scd_id,
                    TIMESTAMP '2024-01-02 10:00:00' as dbt_updated_at,
                    TIMESTAMP '2024-01-02 10:00:00' as dbt_valid_from,
                    CAST(NULL AS TIMESTAMP) as dbt_valid_to,
                    'A001' as account_id,
                    1 as customer_id,
                    6000.00 as balance_amount,
                    'Savings' as account_type,
                    TIMESTAMP '2024-01-02 10:00:00' as loaded_at
            """)
            
            # Simulate incremental run (process only changed records)
            max_calculated_at = conn.execute("""
                SELECT MAX(calculated_at) FROM marts.account_summary
            """).fetchone()[0]
            
            # Count records that would be processed
            records_to_process = conn.execute(f"""
                SELECT COUNT(*) FROM snapshots.snap_account
                WHERE dbt_valid_to IS NULL
                    AND dbt_valid_from > TIMESTAMP '{max_calculated_at}'
            """).fetchone()[0]
            
            assert records_to_process == 1, \
                "Incremental run should process only 1 changed record, not all records"
            
        finally:
            conn.close()


class TestCDCPerformance:
    """Tests for CDC performance improvements."""
    
    def test_incremental_faster_than_full_refresh(self, test_database):
        """Test that incremental runs process fewer records than full refresh."""
        conn = duckdb.connect(test_database)
        
        try:
            # Create large dataset
            conn.execute("""
                CREATE TABLE snapshots.snap_account AS
                SELECT
                    gen_random_uuid()::VARCHAR as dbt_scd_id,
                    TIMESTAMP '2024-01-01 10:00:00' as dbt_updated_at,
                    TIMESTAMP '2024-01-01 10:00:00' as dbt_valid_from,
                    CAST(NULL AS TIMESTAMP) as dbt_valid_to,
                    'A' || LPAD(i::VARCHAR, 5, '0') as account_id,
                    (i % 100) + 1 as customer_id,
                    (i * 1000.0) as balance_amount,
                    'Savings' as account_type,
                    TIMESTAMP '2024-01-01 10:00:00' as loaded_at
                FROM generate_series(1, 1000) as t(i)
            """)
            
            # Full refresh would process all 1000 records
            full_refresh_count = conn.execute("""
                SELECT COUNT(*) FROM snapshots.snap_account
                WHERE dbt_valid_to IS NULL
            """).fetchone()[0]
            
            # Change only 10 records
            conn.execute("""
                UPDATE snapshots.snap_account
                SET dbt_valid_to = TIMESTAMP '2024-01-02 10:00:00'
                WHERE account_id IN (
                    SELECT 'A' || LPAD(i::VARCHAR, 5, '0')
                    FROM generate_series(1, 10) as t(i)
                )
            """)
            
            conn.execute("""
                INSERT INTO snapshots.snap_account
                SELECT
                    gen_random_uuid()::VARCHAR as dbt_scd_id,
                    TIMESTAMP '2024-01-02 10:00:00' as dbt_updated_at,
                    TIMESTAMP '2024-01-02 10:00:00' as dbt_valid_from,
                    CAST(NULL AS TIMESTAMP) as dbt_valid_to,
                    'A' || LPAD(i::VARCHAR, 5, '0') as account_id,
                    (i % 100) + 1 as customer_id,
                    (i * 2000.0) as balance_amount,
                    'Savings' as account_type,
                    TIMESTAMP '2024-01-02 10:00:00' as loaded_at
                FROM generate_series(1, 10) as t(i)
            """)
            
            # Incremental would process only changed records
            incremental_count = conn.execute("""
                SELECT COUNT(*) FROM snapshots.snap_account
                WHERE dbt_valid_to IS NULL
                    AND dbt_valid_from > TIMESTAMP '2024-01-01 10:00:00'
            """).fetchone()[0]
            
            assert incremental_count < full_refresh_count, \
                "Incremental should process fewer records than full refresh"
            assert incremental_count == 10, \
                "Incremental should process only the 10 changed records"
            
            # Calculate performance improvement
            improvement_ratio = full_refresh_count / incremental_count
            assert improvement_ratio >= 10, \
                f"Incremental should be at least 10x more efficient (actual: {improvement_ratio}x)"
            
        finally:
            conn.close()


class TestCDCFullRefreshBehavior:
    """Tests for full refresh behavior in incremental models."""
    
    def test_full_refresh_processes_all_records(self, test_database):
        """Test that full refresh processes all records regardless of timestamps."""
        conn = duckdb.connect(test_database)
        
        try:
            # Create snapshot with multiple versions
            conn.execute("""
                CREATE TABLE snapshots.snap_account AS
                SELECT
                    'a1v1' as dbt_scd_id,
                    TIMESTAMP '2024-01-01 10:00:00' as dbt_updated_at,
                    TIMESTAMP '2024-01-01 10:00:00' as dbt_valid_from,
                    TIMESTAMP '2024-01-02 10:00:00' as dbt_valid_to,
                    'A001' as account_id,
                    1 as customer_id,
                    5000.00 as balance_amount,
                    'Savings' as account_type,
                    TIMESTAMP '2024-01-01 10:00:00' as loaded_at
                UNION ALL
                SELECT
                    'a1v2' as dbt_scd_id,
                    TIMESTAMP '2024-01-02 10:00:00' as dbt_updated_at,
                    TIMESTAMP '2024-01-02 10:00:00' as dbt_valid_from,
                    CAST(NULL AS TIMESTAMP) as dbt_valid_to,
                    'A001' as account_id,
                    1 as customer_id,
                    6000.00 as balance_amount,
                    'Savings' as account_type,
                    TIMESTAMP '2024-01-02 10:00:00' as loaded_at
                UNION ALL
                SELECT
                    'a2v1' as dbt_scd_id,
                    TIMESTAMP '2024-01-01 10:00:00' as dbt_updated_at,
                    TIMESTAMP '2024-01-01 10:00:00' as dbt_valid_from,
                    CAST(NULL AS TIMESTAMP) as dbt_valid_to,
                    'A002' as account_id,
                    2 as customer_id,
                    10000.00 as balance_amount,
                    'Savings' as account_type,
                    TIMESTAMP '2024-01-01 10:00:00' as loaded_at
            """)
            
            # Full refresh processes all current records (no timestamp filter)
            full_refresh_count = conn.execute("""
                SELECT COUNT(*) FROM snapshots.snap_account
                WHERE dbt_valid_to IS NULL
            """).fetchone()[0]
            
            assert full_refresh_count == 2, \
                "Full refresh should process all current records"
            
            # Verify both accounts are included
            accounts = conn.execute("""
                SELECT account_id FROM snapshots.snap_account
                WHERE dbt_valid_to IS NULL
                ORDER BY account_id
            """).fetchall()
            
            assert len(accounts) == 2, "Full refresh should include all accounts"
            assert accounts[0][0] == 'A001', "Full refresh should include A001"
            assert accounts[1][0] == 'A002', "Full refresh should include A002"
            
        finally:
            conn.close()
    
    def test_full_refresh_rebuilds_entire_table(self, test_database):
        """Test that full refresh rebuilds the entire incremental table."""
        conn = duckdb.connect(test_database)
        
        try:
            # Create snapshot
            conn.execute("""
                CREATE TABLE snapshots.snap_account AS
                SELECT
                    'a1v1' as dbt_scd_id,
                    TIMESTAMP '2024-01-01 10:00:00' as dbt_updated_at,
                    TIMESTAMP '2024-01-01 10:00:00' as dbt_valid_from,
                    CAST(NULL AS TIMESTAMP) as dbt_valid_to,
                    'A001' as account_id,
                    1 as customer_id,
                    5000.00 as balance_amount,
                    'Savings' as account_type,
                    TIMESTAMP '2024-01-01 10:00:00' as loaded_at
            """)
            
            # Create intermediate table with old data
            conn.execute("""
                CREATE TABLE intermediate.int_account_with_customer AS
                SELECT
                    'A001' as account_id,
                    1 as customer_id,
                    4000.00 as balance_amount,  -- Old balance
                    'Savings' as account_type,
                    'Alice Smith' as customer_name,
                    true as has_loan_flag,
                    TIMESTAMP '2023-12-01 10:00:00' as valid_from_at,
                    CAST(NULL AS TIMESTAMP) as valid_to_at
            """)
            
            # Simulate full refresh (drop and recreate)
            conn.execute("DROP TABLE intermediate.int_account_with_customer")
            
            conn.execute("""
                CREATE TABLE intermediate.int_account_with_customer AS
                SELECT
                    account_id,
                    customer_id,
                    balance_amount,
                    account_type,
                    'Alice Smith' as customer_name,
                    true as has_loan_flag,
                    dbt_valid_from as valid_from_at,
                    dbt_valid_to as valid_to_at
                FROM snapshots.snap_account
                WHERE dbt_valid_to IS NULL
            """)
            
            # Verify table was rebuilt with current data
            new_balance = conn.execute("""
                SELECT balance_amount FROM intermediate.int_account_with_customer
                WHERE account_id = 'A001'
            """).fetchone()[0]
            
            assert new_balance == 5000.00, \
                "Full refresh should rebuild table with current data"
            
        finally:
            conn.close()


class TestCDCLookbackWindow:
    """Tests for lookback window to handle late-arriving data."""
    
    def test_lookback_window_captures_late_data(self, test_database):
        """Test that lookback window captures late-arriving data."""
        conn = duckdb.connect(test_database)
        
        try:
            # Create snapshot with records
            conn.execute("""
                CREATE TABLE snapshots.snap_account AS
                SELECT
                    'a1v1' as dbt_scd_id,
                    TIMESTAMP '2024-01-01 10:00:00' as dbt_updated_at,
                    TIMESTAMP '2024-01-01 10:00:00' as dbt_valid_from,
                    CAST(NULL AS TIMESTAMP) as dbt_valid_to,
                    'A001' as account_id,
                    1 as customer_id,
                    5000.00 as balance_amount,
                    'Savings' as account_type,
                    TIMESTAMP '2024-01-01 10:00:00' as loaded_at
            """)
            
            # Create intermediate table
            conn.execute("""
                CREATE TABLE intermediate.int_account_with_customer AS
                SELECT
                    account_id,
                    customer_id,
                    balance_amount,
                    account_type,
                    'Alice Smith' as customer_name,
                    true as has_loan_flag,
                    dbt_valid_from as valid_from_at,
                    dbt_valid_to as valid_to_at
                FROM snapshots.snap_account
                WHERE dbt_valid_to IS NULL
            """)
            
            # Get max timestamp
            max_valid_from = conn.execute("""
                SELECT MAX(valid_from_at) FROM intermediate.int_account_with_customer
            """).fetchone()[0]
            
            # Add late-arriving data (within 3-day lookback window)
            conn.execute("""
                INSERT INTO snapshots.snap_account
                SELECT
                    'a2v1' as dbt_scd_id,
                    TIMESTAMP '2024-01-02 10:00:00' as dbt_updated_at,
                    TIMESTAMP '2023-12-30 10:00:00' as dbt_valid_from,  -- Late data
                    CAST(NULL AS TIMESTAMP) as dbt_valid_to,
                    'A002' as account_id,
                    2 as customer_id,
                    10000.00 as balance_amount,
                    'Savings' as account_type,
                    TIMESTAMP '2024-01-02 10:00:00' as loaded_at
            """)
            
            # Calculate lookback timestamp (3 days before max)
            lookback_timestamp = max_valid_from - timedelta(days=3)
            
            # Query with lookback window
            late_records = conn.execute(f"""
                SELECT COUNT(*) FROM snapshots.snap_account
                WHERE dbt_valid_to IS NULL
                    AND dbt_valid_from > TIMESTAMP '{lookback_timestamp}'
                    AND account_id NOT IN (
                        SELECT account_id FROM intermediate.int_account_with_customer
                    )
            """).fetchone()[0]
            
            assert late_records == 1, \
                "Lookback window should capture late-arriving data"
            
        finally:
            conn.close()
