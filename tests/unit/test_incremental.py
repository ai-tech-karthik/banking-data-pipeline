"""
Unit tests for DBT incremental models.

These tests verify that incremental models are correctly configured with
unique keys, merge strategies, and is_incremental() logic.
"""
import os
from pathlib import Path

import pytest
import yaml


class TestIncrementalConfiguration:
    """Tests for incremental model configuration."""
    
    @pytest.fixture
    def dbt_project_path(self):
        """Get the path to the DBT project."""
        return Path(__file__).parent.parent.parent / "dbt_project"
    
    def test_int_account_with_customer_file_exists(self, dbt_project_path):
        """Test that int_account_with_customer.sql file exists."""
        model_path = dbt_project_path / "models" / "intermediate" / "int_account_with_customer.sql"
        assert model_path.exists(), f"Incremental model not found at {model_path}"
    
    def test_int_savings_account_only_file_exists(self, dbt_project_path):
        """Test that int_savings_account_only.sql file exists."""
        model_path = dbt_project_path / "models" / "intermediate" / "int_savings_account_only.sql"
        assert model_path.exists(), f"Incremental model not found at {model_path}"
    
    def test_account_summary_file_exists(self, dbt_project_path):
        """Test that account_summary.sql file exists."""
        model_path = dbt_project_path / "models" / "marts" / "account_summary.sql"
        assert model_path.exists(), f"Incremental model not found at {model_path}"
    
    def test_customer_profile_file_exists(self, dbt_project_path):
        """Test that customer_profile.sql file exists."""
        model_path = dbt_project_path / "models" / "marts" / "customer_profile.sql"
        assert model_path.exists(), f"Incremental model not found at {model_path}"


class TestIncrementalMaterializationConfig:
    """Tests for incremental materialization configuration."""
    
    @pytest.fixture
    def dbt_project_path(self):
        """Get the path to the DBT project."""
        return Path(__file__).parent.parent.parent / "dbt_project"
    
    def test_int_account_with_customer_is_incremental(self, dbt_project_path):
        """Test that int_account_with_customer uses incremental materialization."""
        model_path = dbt_project_path / "models" / "intermediate" / "int_account_with_customer.sql"
        content = model_path.read_text()
        
        assert "materialized='incremental'" in content, \
            "int_account_with_customer should use incremental materialization"
    
    def test_int_savings_account_only_is_incremental(self, dbt_project_path):
        """Test that int_savings_account_only uses incremental materialization."""
        model_path = dbt_project_path / "models" / "intermediate" / "int_savings_account_only.sql"
        content = model_path.read_text()
        
        assert "materialized='incremental'" in content, \
            "int_savings_account_only should use incremental materialization"
    
    def test_account_summary_is_incremental(self, dbt_project_path):
        """Test that account_summary uses incremental materialization."""
        model_path = dbt_project_path / "models" / "marts" / "account_summary.sql"
        content = model_path.read_text()
        
        assert "materialized='incremental'" in content, \
            "account_summary should use incremental materialization"
    
    def test_customer_profile_is_incremental(self, dbt_project_path):
        """Test that customer_profile uses incremental materialization."""
        model_path = dbt_project_path / "models" / "marts" / "customer_profile.sql"
        content = model_path.read_text()
        
        assert "materialized='incremental'" in content, \
            "customer_profile should use incremental materialization"


class TestUniqueKeyConfiguration:
    """Tests for unique_key configuration in incremental models."""
    
    @pytest.fixture
    def dbt_project_path(self):
        """Get the path to the DBT project."""
        return Path(__file__).parent.parent.parent / "dbt_project"
    
    def test_int_account_with_customer_has_unique_key(self, dbt_project_path):
        """Test that int_account_with_customer has unique_key configured."""
        model_path = dbt_project_path / "models" / "intermediate" / "int_account_with_customer.sql"
        content = model_path.read_text()
        
        assert "unique_key='account_id'" in content, \
            "int_account_with_customer should have account_id as unique_key"
    
    def test_int_savings_account_only_has_unique_key(self, dbt_project_path):
        """Test that int_savings_account_only has unique_key configured."""
        model_path = dbt_project_path / "models" / "intermediate" / "int_savings_account_only.sql"
        content = model_path.read_text()
        
        assert "unique_key='account_id'" in content, \
            "int_savings_account_only should have account_id as unique_key"
    
    def test_account_summary_has_unique_key(self, dbt_project_path):
        """Test that account_summary has unique_key configured."""
        model_path = dbt_project_path / "models" / "marts" / "account_summary.sql"
        content = model_path.read_text()
        
        assert "unique_key='account_id'" in content, \
            "account_summary should have account_id as unique_key"
    
    def test_customer_profile_has_unique_key(self, dbt_project_path):
        """Test that customer_profile has unique_key configured."""
        model_path = dbt_project_path / "models" / "marts" / "customer_profile.sql"
        content = model_path.read_text()
        
        assert "unique_key='customer_id'" in content, \
            "customer_profile should have customer_id as unique_key"


class TestMergeStrategyConfiguration:
    """Tests for merge strategy configuration in incremental models."""
    
    @pytest.fixture
    def dbt_project_path(self):
        """Get the path to the DBT project."""
        return Path(__file__).parent.parent.parent / "dbt_project"
    
    def test_models_use_merge_strategy_implicitly(self, dbt_project_path):
        """Test that incremental models use merge strategy (default when unique_key is set)."""
        # When unique_key is set, DBT uses merge strategy by default
        # We verify that unique_key is set, which implies merge strategy
        
        models_to_check = [
            "models/intermediate/int_account_with_customer.sql",
            "models/intermediate/int_savings_account_only.sql",
            "models/marts/account_summary.sql",
            "models/marts/customer_profile.sql"
        ]
        
        for model_path_str in models_to_check:
            model_path = dbt_project_path / model_path_str
            content = model_path.read_text()
            
            # Verify unique_key is set (which enables merge strategy)
            assert "unique_key=" in content, \
                f"{model_path.name} should have unique_key set for merge strategy"
    
    def test_models_have_on_schema_change_configured(self, dbt_project_path):
        """Test that incremental models have on_schema_change configured."""
        models_to_check = [
            "models/intermediate/int_account_with_customer.sql",
            "models/intermediate/int_savings_account_only.sql",
            "models/marts/account_summary.sql",
            "models/marts/customer_profile.sql"
        ]
        
        for model_path_str in models_to_check:
            model_path = dbt_project_path / model_path_str
            content = model_path.read_text()
            
            # Verify on_schema_change is configured
            assert "on_schema_change=" in content, \
                f"{model_path.name} should have on_schema_change configured"


class TestIsIncrementalLogic:
    """Tests for is_incremental() logic in incremental models."""
    
    @pytest.fixture
    def dbt_project_path(self):
        """Get the path to the DBT project."""
        return Path(__file__).parent.parent.parent / "dbt_project"
    
    def test_int_account_with_customer_uses_is_incremental(self, dbt_project_path):
        """Test that int_account_with_customer uses is_incremental() logic."""
        model_path = dbt_project_path / "models" / "intermediate" / "int_account_with_customer.sql"
        content = model_path.read_text()
        
        assert "is_incremental()" in content, \
            "int_account_with_customer should use is_incremental() logic"
        
        # Verify it filters based on timestamp
        assert "dbt_valid_from" in content, \
            "int_account_with_customer should filter on dbt_valid_from in incremental mode"
    
    def test_int_savings_account_only_uses_is_incremental(self, dbt_project_path):
        """Test that int_savings_account_only uses is_incremental() logic."""
        model_path = dbt_project_path / "models" / "intermediate" / "int_savings_account_only.sql"
        content = model_path.read_text()
        
        assert "is_incremental()" in content, \
            "int_savings_account_only should use is_incremental() logic"
    
    def test_account_summary_uses_is_incremental(self, dbt_project_path):
        """Test that account_summary uses is_incremental() logic."""
        model_path = dbt_project_path / "models" / "marts" / "account_summary.sql"
        content = model_path.read_text()
        
        assert "is_incremental()" in content, \
            "account_summary should use is_incremental() logic"
        
        # Verify it filters based on timestamp
        assert "valid_from_at" in content or "calculated_at" in content, \
            "account_summary should filter on timestamp in incremental mode"
    
    def test_customer_profile_uses_is_incremental(self, dbt_project_path):
        """Test that customer_profile uses is_incremental() logic."""
        model_path = dbt_project_path / "models" / "marts" / "customer_profile.sql"
        content = model_path.read_text()
        
        assert "is_incremental()" in content, \
            "customer_profile should use is_incremental() logic"


class TestIncrementalErrorHandling:
    """Tests for error handling in incremental models."""
    
    @pytest.fixture
    def dbt_project_path(self):
        """Get the path to the DBT project."""
        return Path(__file__).parent.parent.parent / "dbt_project"
    
    def test_models_use_coalesce_for_null_handling(self, dbt_project_path):
        """Test that incremental models use COALESCE to handle NULL max values."""
        models_to_check = [
            "models/intermediate/int_account_with_customer.sql",
            "models/marts/account_summary.sql"
        ]
        
        for model_path_str in models_to_check:
            model_path = dbt_project_path / model_path_str
            content = model_path.read_text()
            
            # Verify COALESCE is used for error handling
            assert "coalesce" in content.lower(), \
                f"{model_path.name} should use COALESCE for NULL handling in incremental logic"
    
    def test_models_have_fallback_timestamp(self, dbt_project_path):
        """Test that incremental models have fallback timestamp for empty table scenario."""
        models_to_check = [
            "models/intermediate/int_account_with_customer.sql",
            "models/marts/account_summary.sql"
        ]
        
        for model_path_str in models_to_check:
            model_path = dbt_project_path / model_path_str
            content = model_path.read_text()
            
            # Verify fallback timestamp exists (e.g., '1900-01-01')
            assert "'1900-01-01'" in content, \
                f"{model_path.name} should have fallback timestamp for empty table scenario"


class TestIncrementalReferences:
    """Tests for model references in incremental models."""
    
    @pytest.fixture
    def dbt_project_path(self):
        """Get the path to the DBT project."""
        return Path(__file__).parent.parent.parent / "dbt_project"
    
    def test_int_account_with_customer_references_snapshots(self, dbt_project_path):
        """Test that int_account_with_customer references snapshot models."""
        model_path = dbt_project_path / "models" / "intermediate" / "int_account_with_customer.sql"
        content = model_path.read_text()
        
        assert "ref('snap_account')" in content, \
            "int_account_with_customer should reference snap_account"
        assert "ref('snap_customer')" in content, \
            "int_account_with_customer should reference snap_customer"
    
    def test_int_savings_account_only_references_upstream(self, dbt_project_path):
        """Test that int_savings_account_only references upstream intermediate model."""
        model_path = dbt_project_path / "models" / "intermediate" / "int_savings_account_only.sql"
        content = model_path.read_text()
        
        assert "ref('int_account_with_customer')" in content, \
            "int_savings_account_only should reference int_account_with_customer"
    
    def test_account_summary_references_upstream(self, dbt_project_path):
        """Test that account_summary references upstream intermediate model."""
        model_path = dbt_project_path / "models" / "marts" / "account_summary.sql"
        content = model_path.read_text()
        
        assert "ref('int_savings_account_only')" in content, \
            "account_summary should reference int_savings_account_only"
    
    def test_customer_profile_references_upstream(self, dbt_project_path):
        """Test that customer_profile references upstream model."""
        model_path = dbt_project_path / "models" / "marts" / "customer_profile.sql"
        content = model_path.read_text()
        
        # Should reference either account_summary or int_account_with_customer
        has_reference = (
            "ref('account_summary')" in content or
            "ref('int_account_with_customer')" in content or
            "ref('int_savings_account_only')" in content
        )
        
        assert has_reference, \
            "customer_profile should reference an upstream model"


class TestIncrementalCurrentRecordsFilter:
    """Tests for filtering to current records in incremental models."""
    
    @pytest.fixture
    def dbt_project_path(self):
        """Get the path to the DBT project."""
        return Path(__file__).parent.parent.parent / "dbt_project"
    
    def test_int_account_with_customer_filters_current_records(self, dbt_project_path):
        """Test that int_account_with_customer filters to current records from snapshots."""
        model_path = dbt_project_path / "models" / "intermediate" / "int_account_with_customer.sql"
        content = model_path.read_text()
        
        # Should filter where dbt_valid_to is null (current records)
        assert "dbt_valid_to is null" in content.lower(), \
            "int_account_with_customer should filter to current records (dbt_valid_to IS NULL)"
    
    def test_models_use_proper_scd2_filtering(self, dbt_project_path):
        """Test that models properly filter SCD2 snapshots to current records."""
        model_path = dbt_project_path / "models" / "intermediate" / "int_account_with_customer.sql"
        content = model_path.read_text()
        
        # Count occurrences of dbt_valid_to is null filter
        # Should appear for both snap_account and snap_customer
        count = content.lower().count("dbt_valid_to is null")
        
        assert count >= 2, \
            "int_account_with_customer should filter both snapshots to current records"
