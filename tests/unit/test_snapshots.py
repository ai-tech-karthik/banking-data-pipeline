"""
Unit tests for DBT snapshot models.

These tests verify that snapshot models are correctly configured with SCD2
columns and appropriate strategies for change detection.
"""
import os
import tempfile
from pathlib import Path

import pytest
import yaml


class TestSnapshotConfiguration:
    """Tests for snapshot model configuration."""
    
    @pytest.fixture
    def dbt_project_path(self):
        """Get the path to the DBT project."""
        return Path(__file__).parent.parent.parent / "dbt_project"
    
    def test_snap_customer_file_exists(self, dbt_project_path):
        """Test that snap_customer.sql file exists."""
        snapshot_path = dbt_project_path / "snapshots" / "snap_customer.sql"
        assert snapshot_path.exists(), f"Snapshot file not found at {snapshot_path}"
    
    def test_snap_account_file_exists(self, dbt_project_path):
        """Test that snap_account.sql file exists."""
        snapshot_path = dbt_project_path / "snapshots" / "snap_account.sql"
        assert snapshot_path.exists(), f"Snapshot file not found at {snapshot_path}"
    
    def test_snap_customer_uses_timestamp_strategy(self, dbt_project_path):
        """Test that snap_customer uses timestamp strategy."""
        snapshot_path = dbt_project_path / "snapshots" / "snap_customer.sql"
        content = snapshot_path.read_text()
        
        # Verify timestamp strategy is configured
        assert "strategy='timestamp'" in content, \
            "snap_customer should use timestamp strategy"
        assert "updated_at='loaded_at'" in content, \
            "snap_customer should use loaded_at as updated_at column"
    
    def test_snap_account_uses_check_cols_strategy(self, dbt_project_path):
        """Test that snap_account uses check_cols strategy."""
        snapshot_path = dbt_project_path / "snapshots" / "snap_account.sql"
        content = snapshot_path.read_text()
        
        # Verify check_cols strategy is configured
        assert "strategy='check'" in content, \
            "snap_account should use check strategy"
        assert "check_cols='all'" in content, \
            "snap_account should check all columns for changes"
    
    def test_snap_customer_has_unique_key(self, dbt_project_path):
        """Test that snap_customer has unique_key configured."""
        snapshot_path = dbt_project_path / "snapshots" / "snap_customer.sql"
        content = snapshot_path.read_text()
        
        assert "unique_key='customer_id'" in content, \
            "snap_customer should have customer_id as unique_key"
    
    def test_snap_account_has_unique_key(self, dbt_project_path):
        """Test that snap_account has unique_key configured."""
        snapshot_path = dbt_project_path / "snapshots" / "snap_account.sql"
        content = snapshot_path.read_text()
        
        assert "unique_key='account_id'" in content, \
            "snap_account should have account_id as unique_key"
    
    def test_snap_customer_invalidates_hard_deletes(self, dbt_project_path):
        """Test that snap_customer has invalidate_hard_deletes enabled."""
        snapshot_path = dbt_project_path / "snapshots" / "snap_customer.sql"
        content = snapshot_path.read_text()
        
        assert "invalidate_hard_deletes=true" in content, \
            "snap_customer should have invalidate_hard_deletes=true"
    
    def test_snap_account_invalidates_hard_deletes(self, dbt_project_path):
        """Test that snap_account has invalidate_hard_deletes enabled."""
        snapshot_path = dbt_project_path / "snapshots" / "snap_account.sql"
        content = snapshot_path.read_text()
        
        assert "invalidate_hard_deletes=true" in content, \
            "snap_account should have invalidate_hard_deletes=true"
    
    def test_snap_customer_has_target_schema(self, dbt_project_path):
        """Test that snap_customer has target_schema configured."""
        snapshot_path = dbt_project_path / "snapshots" / "snap_customer.sql"
        content = snapshot_path.read_text()
        
        assert "target_schema='snapshots'" in content, \
            "snap_customer should have target_schema='snapshots'"
    
    def test_snap_account_has_target_schema(self, dbt_project_path):
        """Test that snap_account has target_schema configured."""
        snapshot_path = dbt_project_path / "snapshots" / "snap_account.sql"
        content = snapshot_path.read_text()
        
        assert "target_schema='snapshots'" in content, \
            "snap_account should have target_schema='snapshots'"


class TestSnapshotSchema:
    """Tests for snapshot model schema and column selection."""
    
    @pytest.fixture
    def dbt_project_path(self):
        """Get the path to the DBT project."""
        return Path(__file__).parent.parent.parent / "dbt_project"
    
    def test_snap_customer_selects_required_columns(self, dbt_project_path):
        """Test that snap_customer selects all required columns."""
        snapshot_path = dbt_project_path / "snapshots" / "snap_customer.sql"
        content = snapshot_path.read_text()
        
        # Required columns for customer snapshot
        required_columns = [
            "customer_id",
            "customer_name",
            "has_loan_flag",
            "loaded_at"
        ]
        
        for column in required_columns:
            assert column in content, \
                f"snap_customer should select {column} column"
    
    def test_snap_account_selects_required_columns(self, dbt_project_path):
        """Test that snap_account selects all required columns."""
        snapshot_path = dbt_project_path / "snapshots" / "snap_account.sql"
        content = snapshot_path.read_text()
        
        # Required columns for account snapshot
        required_columns = [
            "account_id",
            "customer_id",
            "balance_amount",
            "account_type",
            "loaded_at"
        ]
        
        for column in required_columns:
            assert column in content, \
                f"snap_account should select {column} column"
    
    def test_snap_customer_references_staging_model(self, dbt_project_path):
        """Test that snap_customer references stg_customer."""
        snapshot_path = dbt_project_path / "snapshots" / "snap_customer.sql"
        content = snapshot_path.read_text()
        
        assert "ref('stg_customer')" in content, \
            "snap_customer should reference stg_customer staging model"
    
    def test_snap_account_references_staging_model(self, dbt_project_path):
        """Test that snap_account references stg_account."""
        snapshot_path = dbt_project_path / "snapshots" / "snap_account.sql"
        content = snapshot_path.read_text()
        
        assert "ref('stg_account')" in content, \
            "snap_account should reference stg_account staging model"


class TestSnapshotDocumentation:
    """Tests for snapshot model documentation."""
    
    @pytest.fixture
    def dbt_project_path(self):
        """Get the path to the DBT project."""
        return Path(__file__).parent.parent.parent / "dbt_project"
    
    def test_snapshots_yml_exists(self, dbt_project_path):
        """Test that _snapshots.yml documentation file exists."""
        yml_path = dbt_project_path / "snapshots" / "_snapshots.yml"
        assert yml_path.exists(), f"Snapshots documentation file not found at {yml_path}"
    
    def test_snapshots_yml_is_valid_yaml(self, dbt_project_path):
        """Test that _snapshots.yml is valid YAML."""
        yml_path = dbt_project_path / "snapshots" / "_snapshots.yml"
        
        try:
            with open(yml_path, 'r') as f:
                yaml.safe_load(f)
        except yaml.YAMLError as e:
            pytest.fail(f"_snapshots.yml is not valid YAML: {e}")
    
    def test_snap_customer_is_documented(self, dbt_project_path):
        """Test that snap_customer is documented in _snapshots.yml."""
        yml_path = dbt_project_path / "snapshots" / "_snapshots.yml"
        
        with open(yml_path, 'r') as f:
            config = yaml.safe_load(f)
        
        # Find snap_customer in snapshots
        snapshots = config.get('snapshots', [])
        snap_customer = next(
            (s for s in snapshots if s.get('name') == 'snap_customer'),
            None
        )
        
        assert snap_customer is not None, \
            "snap_customer should be documented in _snapshots.yml"
        assert 'description' in snap_customer, \
            "snap_customer should have a description"
    
    def test_snap_account_is_documented(self, dbt_project_path):
        """Test that snap_account is documented in _snapshots.yml."""
        yml_path = dbt_project_path / "snapshots" / "_snapshots.yml"
        
        with open(yml_path, 'r') as f:
            config = yaml.safe_load(f)
        
        # Find snap_account in snapshots
        snapshots = config.get('snapshots', [])
        snap_account = next(
            (s for s in snapshots if s.get('name') == 'snap_account'),
            None
        )
        
        assert snap_account is not None, \
            "snap_account should be documented in _snapshots.yml"
        assert 'description' in snap_account, \
            "snap_account should have a description"
    
    def test_scd2_columns_are_documented(self, dbt_project_path):
        """Test that SCD2 columns are documented in _snapshots.yml."""
        yml_path = dbt_project_path / "snapshots" / "_snapshots.yml"
        
        with open(yml_path, 'r') as f:
            config = yaml.safe_load(f)
        
        # SCD2 columns that should be documented
        scd2_columns = ['dbt_scd_id', 'dbt_valid_from', 'dbt_valid_to', 'dbt_updated_at']
        
        # Check snap_customer columns
        snapshots = config.get('snapshots', [])
        snap_customer = next(
            (s for s in snapshots if s.get('name') == 'snap_customer'),
            None
        )
        
        if snap_customer and 'columns' in snap_customer:
            documented_columns = [col['name'] for col in snap_customer['columns']]
            for scd2_col in scd2_columns:
                assert scd2_col in documented_columns, \
                    f"SCD2 column {scd2_col} should be documented in snap_customer"


class TestSnapshotNamingConventions:
    """Tests for snapshot naming conventions."""
    
    @pytest.fixture
    def dbt_project_path(self):
        """Get the path to the DBT project."""
        return Path(__file__).parent.parent.parent / "dbt_project"
    
    def test_snapshot_files_use_snap_prefix(self, dbt_project_path):
        """Test that all snapshot files use 'snap_' prefix."""
        snapshots_dir = dbt_project_path / "snapshots"
        
        # Get all .sql files in snapshots directory
        snapshot_files = list(snapshots_dir.glob("*.sql"))
        
        for snapshot_file in snapshot_files:
            assert snapshot_file.stem.startswith('snap_'), \
                f"Snapshot file {snapshot_file.name} should start with 'snap_' prefix"
    
    def test_snapshot_uses_singular_nouns(self, dbt_project_path):
        """Test that snapshot names use singular nouns."""
        snapshots_dir = dbt_project_path / "snapshots"
        
        # Get all .sql files in snapshots directory
        snapshot_files = list(snapshots_dir.glob("*.sql"))
        
        # Check that names use singular forms
        for snapshot_file in snapshot_files:
            name = snapshot_file.stem
            # Should not end with 's' (plural) after 'snap_'
            # snap_customer (singular) not snap_customers (plural)
            assert not name.endswith('customers'), \
                f"Snapshot {name} should use singular 'customer' not plural 'customers'"
            assert not name.endswith('accounts'), \
                f"Snapshot {name} should use singular 'account' not plural 'accounts'"
