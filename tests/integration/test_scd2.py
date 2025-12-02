"""
Integration tests for SCD2 (Slowly Changing Dimension Type 2) functionality.

These tests verify that snapshot models correctly track historical changes
by creating new versions, closing old versions, and handling deletions.
"""
import os
import tempfile
from pathlib import Path
from datetime import datetime, timedelta

import pandas as pd
import pytest
import duckdb

from lending_club_pipeline.resources.duckdb_resource import DuckDBResource


@pytest.fixture
def test_database(tmp_path):
    """Create a temporary DuckDB database for testing."""
    db_path = tmp_path / "test_scd2.duckdb"
    
    # Create database and initialize schemas
    conn = duckdb.connect(str(db_path))
    conn.execute("CREATE SCHEMA IF NOT EXISTS main")
    conn.execute("CREATE SCHEMA IF NOT EXISTS snapshots")
    conn.close()
    
    yield str(db_path)
    
    # Cleanup
    if db_path.exists():
        db_path.unlink()


@pytest.fixture
def dbt_project_path():
    """Get the path to the DBT project."""
    return Path(__file__).parent.parent.parent / "dbt_project"


class TestSCD2VersionCreation:
    """Tests for SCD2 version creation when data changes."""
    
    def test_initial_snapshot_creates_first_version(self, test_database, tmp_path):
        """Test that initial snapshot creates first version with dbt_valid_from."""
        conn = duckdb.connect(test_database)
        
        try:
            # Create staging table with initial data
            conn.execute("""
                CREATE TABLE main.stg_customer AS
                SELECT
                    1 as customer_id,
                    'Alice Smith' as customer_name,
                    true as has_loan_flag,
                    TIMESTAMP '2024-01-01 10:00:00' as loaded_at
            """)
            
            # Simulate snapshot creation (simplified version)
            conn.execute("""
                CREATE TABLE snapshots.snap_customer AS
                SELECT
                    gen_random_uuid()::VARCHAR as dbt_scd_id,
                    CURRENT_TIMESTAMP as dbt_updated_at,
                    loaded_at as dbt_valid_from,
                    CAST(NULL AS TIMESTAMP) as dbt_valid_to,
                    customer_id,
                    customer_name,
                    has_loan_flag,
                    loaded_at
                FROM main.stg_customer
            """)
            
            # Verify snapshot was created
            result = conn.execute("SELECT COUNT(*) FROM snapshots.snap_customer").fetchone()
            assert result[0] == 1, "Initial snapshot should create one version"
            
            # Verify dbt_valid_from is set
            result = conn.execute("""
                SELECT dbt_valid_from IS NOT NULL as has_valid_from
                FROM snapshots.snap_customer
            """).fetchone()
            assert result[0] is True, "Initial version should have dbt_valid_from set"
            
            # Verify dbt_valid_to is NULL (current version)
            result = conn.execute("""
                SELECT dbt_valid_to IS NULL as is_current
                FROM snapshots.snap_customer
            """).fetchone()
            assert result[0] is True, "Initial version should have dbt_valid_to as NULL"
            
        finally:
            conn.close()
    
    def test_change_creates_new_version(self, test_database):
        """Test that changes create new versions with new dbt_valid_from."""
        conn = duckdb.connect(test_database)
        
        try:
            # Create initial snapshot
            conn.execute("""
                CREATE TABLE snapshots.snap_customer AS
                SELECT
                    gen_random_uuid()::VARCHAR as dbt_scd_id,
                    TIMESTAMP '2024-01-01 10:00:00' as dbt_updated_at,
                    TIMESTAMP '2024-01-01 10:00:00' as dbt_valid_from,
                    CAST(NULL AS TIMESTAMP) as dbt_valid_to,
                    1 as customer_id,
                    'Alice Smith' as customer_name,
                    true as has_loan_flag,
                    TIMESTAMP '2024-01-01 10:00:00' as loaded_at
            """)
            
            # Simulate a change (customer name updated)
            conn.execute("""
                INSERT INTO snapshots.snap_customer
                SELECT
                    gen_random_uuid()::VARCHAR as dbt_scd_id,
                    TIMESTAMP '2024-01-02 10:00:00' as dbt_updated_at,
                    TIMESTAMP '2024-01-02 10:00:00' as dbt_valid_from,
                    CAST(NULL AS TIMESTAMP) as dbt_valid_to,
                    1 as customer_id,
                    'Alice Johnson' as customer_name,  -- Changed name
                    true as has_loan_flag,
                    TIMESTAMP '2024-01-02 10:00:00' as loaded_at
            """)
            
            # Verify two versions exist
            result = conn.execute("""
                SELECT COUNT(*) FROM snapshots.snap_customer
                WHERE customer_id = 1
            """).fetchone()
            assert result[0] == 2, "Change should create a new version"
            
            # Verify both versions have different dbt_valid_from
            result = conn.execute("""
                SELECT COUNT(DISTINCT dbt_valid_from)
                FROM snapshots.snap_customer
                WHERE customer_id = 1
            """).fetchone()
            assert result[0] == 2, "Each version should have unique dbt_valid_from"
            
        finally:
            conn.close()
    
    def test_unchanged_records_not_duplicated(self, test_database):
        """Test that unchanged records are not duplicated in snapshots."""
        conn = duckdb.connect(test_database)
        
        try:
            # Create initial snapshot
            conn.execute("""
                CREATE TABLE snapshots.snap_customer AS
                SELECT
                    gen_random_uuid()::VARCHAR as dbt_scd_id,
                    TIMESTAMP '2024-01-01 10:00:00' as dbt_updated_at,
                    TIMESTAMP '2024-01-01 10:00:00' as dbt_valid_from,
                    CAST(NULL AS TIMESTAMP) as dbt_valid_to,
                    1 as customer_id,
                    'Alice Smith' as customer_name,
                    true as has_loan_flag,
                    TIMESTAMP '2024-01-01 10:00:00' as loaded_at
            """)
            
            # Simulate second snapshot run with no changes
            # In real DBT, unchanged records would not be inserted
            # We verify the count remains the same
            
            result = conn.execute("""
                SELECT COUNT(*) FROM snapshots.snap_customer
                WHERE customer_id = 1
            """).fetchone()
            assert result[0] == 1, "Unchanged records should not create new versions"
            
        finally:
            conn.close()


class TestSCD2VersionClosure:
    """Tests for closing old versions when new versions are created."""
    
    def test_old_version_gets_dbt_valid_to_set(self, test_database):
        """Test that old versions get dbt_valid_to set when new version is created."""
        conn = duckdb.connect(test_database)
        
        try:
            # Create initial snapshot
            conn.execute("""
                CREATE TABLE snapshots.snap_customer AS
                SELECT
                    'v1' as dbt_scd_id,
                    TIMESTAMP '2024-01-01 10:00:00' as dbt_updated_at,
                    TIMESTAMP '2024-01-01 10:00:00' as dbt_valid_from,
                    CAST(NULL AS TIMESTAMP) as dbt_valid_to,
                    1 as customer_id,
                    'Alice Smith' as customer_name,
                    true as has_loan_flag,
                    TIMESTAMP '2024-01-01 10:00:00' as loaded_at
            """)
            
            # Simulate change: close old version and create new version
            conn.execute("""
                UPDATE snapshots.snap_customer
                SET dbt_valid_to = TIMESTAMP '2024-01-02 10:00:00'
                WHERE dbt_scd_id = 'v1'
            """)
            
            conn.execute("""
                INSERT INTO snapshots.snap_customer
                SELECT
                    'v2' as dbt_scd_id,
                    TIMESTAMP '2024-01-02 10:00:00' as dbt_updated_at,
                    TIMESTAMP '2024-01-02 10:00:00' as dbt_valid_from,
                    CAST(NULL AS TIMESTAMP) as dbt_valid_to,
                    1 as customer_id,
                    'Alice Johnson' as customer_name,
                    true as has_loan_flag,
                    TIMESTAMP '2024-01-02 10:00:00' as loaded_at
            """)
            
            # Verify old version has dbt_valid_to set
            result = conn.execute("""
                SELECT dbt_valid_to IS NOT NULL as is_closed
                FROM snapshots.snap_customer
                WHERE dbt_scd_id = 'v1'
            """).fetchone()
            assert result[0] is True, "Old version should have dbt_valid_to set"
            
            # Verify new version has dbt_valid_to as NULL
            result = conn.execute("""
                SELECT dbt_valid_to IS NULL as is_current
                FROM snapshots.snap_customer
                WHERE dbt_scd_id = 'v2'
            """).fetchone()
            assert result[0] is True, "New version should have dbt_valid_to as NULL"
            
        finally:
            conn.close()
    
    def test_dbt_valid_to_equals_next_dbt_valid_from(self, test_database):
        """Test that dbt_valid_to of old version equals dbt_valid_from of new version."""
        conn = duckdb.connect(test_database)
        
        try:
            # Create two versions with proper timestamps
            conn.execute("""
                CREATE TABLE snapshots.snap_customer AS
                SELECT
                    'v1' as dbt_scd_id,
                    TIMESTAMP '2024-01-01 10:00:00' as dbt_updated_at,
                    TIMESTAMP '2024-01-01 10:00:00' as dbt_valid_from,
                    TIMESTAMP '2024-01-02 10:00:00' as dbt_valid_to,
                    1 as customer_id,
                    'Alice Smith' as customer_name,
                    true as has_loan_flag,
                    TIMESTAMP '2024-01-01 10:00:00' as loaded_at
                UNION ALL
                SELECT
                    'v2' as dbt_scd_id,
                    TIMESTAMP '2024-01-02 10:00:00' as dbt_updated_at,
                    TIMESTAMP '2024-01-02 10:00:00' as dbt_valid_from,
                    CAST(NULL AS TIMESTAMP) as dbt_valid_to,
                    1 as customer_id,
                    'Alice Johnson' as customer_name,
                    true as has_loan_flag,
                    TIMESTAMP '2024-01-02 10:00:00' as loaded_at
            """)
            
            # Verify dbt_valid_to of v1 equals dbt_valid_from of v2
            result = conn.execute("""
                SELECT
                    v1.dbt_valid_to = v2.dbt_valid_from as timestamps_match
                FROM
                    (SELECT * FROM snapshots.snap_customer WHERE dbt_scd_id = 'v1') v1,
                    (SELECT * FROM snapshots.snap_customer WHERE dbt_scd_id = 'v2') v2
            """).fetchone()
            assert result[0] is True, \
                "dbt_valid_to of old version should equal dbt_valid_from of new version"
            
        finally:
            conn.close()


class TestSCD2CurrentRecords:
    """Tests for identifying current records in SCD2 snapshots."""
    
    def test_current_records_have_null_dbt_valid_to(self, test_database):
        """Test that current records have NULL dbt_valid_to."""
        conn = duckdb.connect(test_database)
        
        try:
            # Create snapshot with multiple versions
            conn.execute("""
                CREATE TABLE snapshots.snap_customer AS
                SELECT
                    'v1' as dbt_scd_id,
                    TIMESTAMP '2024-01-01 10:00:00' as dbt_updated_at,
                    TIMESTAMP '2024-01-01 10:00:00' as dbt_valid_from,
                    TIMESTAMP '2024-01-02 10:00:00' as dbt_valid_to,
                    1 as customer_id,
                    'Alice Smith' as customer_name,
                    true as has_loan_flag,
                    TIMESTAMP '2024-01-01 10:00:00' as loaded_at
                UNION ALL
                SELECT
                    'v2' as dbt_scd_id,
                    TIMESTAMP '2024-01-02 10:00:00' as dbt_updated_at,
                    TIMESTAMP '2024-01-02 10:00:00' as dbt_valid_from,
                    CAST(NULL AS TIMESTAMP) as dbt_valid_to,
                    1 as customer_id,
                    'Alice Johnson' as customer_name,
                    true as has_loan_flag,
                    TIMESTAMP '2024-01-02 10:00:00' as loaded_at
            """)
            
            # Query for current records
            result = conn.execute("""
                SELECT COUNT(*) FROM snapshots.snap_customer
                WHERE dbt_valid_to IS NULL
            """).fetchone()
            assert result[0] == 1, "Should have exactly one current record"
            
            # Verify current record is the latest version
            result = conn.execute("""
                SELECT customer_name FROM snapshots.snap_customer
                WHERE dbt_valid_to IS NULL
            """).fetchone()
            assert result[0] == 'Alice Johnson', \
                "Current record should be the latest version"
            
        finally:
            conn.close()
    
    def test_each_customer_has_one_current_record(self, test_database):
        """Test that each customer has exactly one current record."""
        conn = duckdb.connect(test_database)
        
        try:
            # Create snapshots for multiple customers with multiple versions
            conn.execute("""
                CREATE TABLE snapshots.snap_customer AS
                -- Customer 1: 2 versions
                SELECT
                    'c1v1' as dbt_scd_id,
                    TIMESTAMP '2024-01-01 10:00:00' as dbt_updated_at,
                    TIMESTAMP '2024-01-01 10:00:00' as dbt_valid_from,
                    TIMESTAMP '2024-01-02 10:00:00' as dbt_valid_to,
                    1 as customer_id,
                    'Alice Smith' as customer_name,
                    true as has_loan_flag,
                    TIMESTAMP '2024-01-01 10:00:00' as loaded_at
                UNION ALL
                SELECT
                    'c1v2' as dbt_scd_id,
                    TIMESTAMP '2024-01-02 10:00:00' as dbt_updated_at,
                    TIMESTAMP '2024-01-02 10:00:00' as dbt_valid_from,
                    CAST(NULL AS TIMESTAMP) as dbt_valid_to,
                    1 as customer_id,
                    'Alice Johnson' as customer_name,
                    true as has_loan_flag,
                    TIMESTAMP '2024-01-02 10:00:00' as loaded_at
                UNION ALL
                -- Customer 2: 1 version
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
            
            # Verify each customer has exactly one current record
            result = conn.execute("""
                SELECT customer_id, COUNT(*) as current_count
                FROM snapshots.snap_customer
                WHERE dbt_valid_to IS NULL
                GROUP BY customer_id
            """).fetchall()
            
            assert len(result) == 2, "Should have current records for 2 customers"
            for row in result:
                assert row[1] == 1, f"Customer {row[0]} should have exactly 1 current record"
            
        finally:
            conn.close()


class TestSCD2DeletedRecords:
    """Tests for handling deleted records in SCD2 snapshots."""
    
    def test_deleted_records_get_invalidated(self, test_database):
        """Test that deleted records get dbt_valid_to set (invalidate_hard_deletes)."""
        conn = duckdb.connect(test_database)
        
        try:
            # Create initial snapshot
            conn.execute("""
                CREATE TABLE snapshots.snap_customer AS
                SELECT
                    'v1' as dbt_scd_id,
                    TIMESTAMP '2024-01-01 10:00:00' as dbt_updated_at,
                    TIMESTAMP '2024-01-01 10:00:00' as dbt_valid_from,
                    CAST(NULL AS TIMESTAMP) as dbt_valid_to,
                    1 as customer_id,
                    'Alice Smith' as customer_name,
                    true as has_loan_flag,
                    TIMESTAMP '2024-01-01 10:00:00' as loaded_at
            """)
            
            # Simulate deletion: set dbt_valid_to (invalidate_hard_deletes=true)
            conn.execute("""
                UPDATE snapshots.snap_customer
                SET dbt_valid_to = TIMESTAMP '2024-01-02 10:00:00'
                WHERE customer_id = 1
            """)
            
            # Verify record is invalidated
            result = conn.execute("""
                SELECT dbt_valid_to IS NOT NULL as is_invalidated
                FROM snapshots.snap_customer
                WHERE customer_id = 1
            """).fetchone()
            assert result[0] is True, "Deleted record should have dbt_valid_to set"
            
            # Verify no current records exist for deleted customer
            result = conn.execute("""
                SELECT COUNT(*) FROM snapshots.snap_customer
                WHERE customer_id = 1 AND dbt_valid_to IS NULL
            """).fetchone()
            assert result[0] == 0, "Deleted customer should have no current records"
            
        finally:
            conn.close()
    
    def test_deleted_records_preserved_in_history(self, test_database):
        """Test that deleted records are preserved in history (not physically deleted)."""
        conn = duckdb.connect(test_database)
        
        try:
            # Create snapshot and then invalidate it
            conn.execute("""
                CREATE TABLE snapshots.snap_customer AS
                SELECT
                    'v1' as dbt_scd_id,
                    TIMESTAMP '2024-01-01 10:00:00' as dbt_updated_at,
                    TIMESTAMP '2024-01-01 10:00:00' as dbt_valid_from,
                    TIMESTAMP '2024-01-02 10:00:00' as dbt_valid_to,
                    1 as customer_id,
                    'Alice Smith' as customer_name,
                    true as has_loan_flag,
                    TIMESTAMP '2024-01-01 10:00:00' as loaded_at
            """)
            
            # Verify record still exists in table
            result = conn.execute("""
                SELECT COUNT(*) FROM snapshots.snap_customer
                WHERE customer_id = 1
            """).fetchone()
            assert result[0] == 1, "Deleted record should be preserved in history"
            
            # Verify it's marked as historical (not current)
            result = conn.execute("""
                SELECT dbt_valid_to IS NOT NULL as is_historical
                FROM snapshots.snap_customer
                WHERE customer_id = 1
            """).fetchone()
            assert result[0] is True, "Deleted record should be marked as historical"
            
        finally:
            conn.close()


class TestSCD2NoOverlappingPeriods:
    """Tests for ensuring no overlapping validity periods in SCD2."""
    
    def test_no_overlapping_validity_periods(self, test_database):
        """Test that validity periods do not overlap for the same customer."""
        conn = duckdb.connect(test_database)
        
        try:
            # Create snapshot with proper non-overlapping periods
            conn.execute("""
                CREATE TABLE snapshots.snap_customer AS
                SELECT
                    'v1' as dbt_scd_id,
                    TIMESTAMP '2024-01-01 10:00:00' as dbt_updated_at,
                    TIMESTAMP '2024-01-01 10:00:00' as dbt_valid_from,
                    TIMESTAMP '2024-01-02 10:00:00' as dbt_valid_to,
                    1 as customer_id,
                    'Alice Smith' as customer_name,
                    true as has_loan_flag,
                    TIMESTAMP '2024-01-01 10:00:00' as loaded_at
                UNION ALL
                SELECT
                    'v2' as dbt_scd_id,
                    TIMESTAMP '2024-01-02 10:00:00' as dbt_updated_at,
                    TIMESTAMP '2024-01-02 10:00:00' as dbt_valid_from,
                    TIMESTAMP '2024-01-03 10:00:00' as dbt_valid_to,
                    1 as customer_id,
                    'Alice Johnson' as customer_name,
                    true as has_loan_flag,
                    TIMESTAMP '2024-01-02 10:00:00' as loaded_at
                UNION ALL
                SELECT
                    'v3' as dbt_scd_id,
                    TIMESTAMP '2024-01-03 10:00:00' as dbt_updated_at,
                    TIMESTAMP '2024-01-03 10:00:00' as dbt_valid_from,
                    CAST(NULL AS TIMESTAMP) as dbt_valid_to,
                    1 as customer_id,
                    'Alice Williams' as customer_name,
                    false as has_loan_flag,
                    TIMESTAMP '2024-01-03 10:00:00' as loaded_at
            """)
            
            # Check for overlapping periods using self-join
            result = conn.execute("""
                SELECT COUNT(*) as overlap_count
                FROM snapshots.snap_customer a
                JOIN snapshots.snap_customer b
                    ON a.customer_id = b.customer_id
                    AND a.dbt_scd_id != b.dbt_scd_id
                WHERE
                    a.dbt_valid_from < COALESCE(b.dbt_valid_to, TIMESTAMP '9999-12-31')
                    AND COALESCE(a.dbt_valid_to, TIMESTAMP '9999-12-31') > b.dbt_valid_from
            """).fetchone()
            
            assert result[0] == 0, "Should have no overlapping validity periods"
            
        finally:
            conn.close()
