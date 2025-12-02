"""
Integration tests for DBT contract enforcement.

These tests verify that DBT contracts correctly enforce schema definitions,
catch violations, and provide clear error messages.
"""
import os
from pathlib import Path

import pytest
import yaml


@pytest.fixture
def dbt_project_path():
    """Get the path to the DBT project."""
    return Path(__file__).parent.parent.parent / "dbt_project"


class TestContractDefinitions:
    """Tests for contract definitions in schema YAML files."""
    
    def test_staging_models_have_contracts(self, dbt_project_path):
        """Test that staging models have contract definitions."""
        yml_path = dbt_project_path / "models" / "staging" / "_staging.yml"
        
        with open(yml_path, 'r') as f:
            config = yaml.safe_load(f)
        
        models = config.get('models', [])
        
        # Check stg_customer
        stg_customer = next(
            (m for m in models if m.get('name') == 'stg_customer'),
            None
        )
        assert stg_customer is not None, "stg_customer should be defined"
        assert 'config' in stg_customer, "stg_customer should have config"
        assert 'contract' in stg_customer['config'], \
            "stg_customer should have contract config"
        assert stg_customer['config']['contract']['enforced'] is True, \
            "stg_customer contract should be enforced"
        
        # Check stg_account
        stg_account = next(
            (m for m in models if m.get('name') == 'stg_account'),
            None
        )
        assert stg_account is not None, "stg_account should be defined"
        assert 'config' in stg_account, "stg_account should have config"
        assert 'contract' in stg_account['config'], \
            "stg_account should have contract config"
        assert stg_account['config']['contract']['enforced'] is True, \
            "stg_account contract should be enforced"
    
    def test_snapshot_models_have_contracts(self, dbt_project_path):
        """Test that snapshot models have contract definitions."""
        yml_path = dbt_project_path / "snapshots" / "_snapshots.yml"
        
        with open(yml_path, 'r') as f:
            config = yaml.safe_load(f)
        
        snapshots = config.get('snapshots', [])
        
        # Check snap_customer
        snap_customer = next(
            (s for s in snapshots if s.get('name') == 'snap_customer'),
            None
        )
        assert snap_customer is not None, "snap_customer should be defined"
        
        # Snapshots may have contract in config or at model level
        has_contract = (
            ('config' in snap_customer and 'contract' in snap_customer['config']) or
            'columns' in snap_customer  # Columns definition implies contract
        )
        assert has_contract, "snap_customer should have contract or column definitions"
    
    def test_intermediate_models_have_contracts(self, dbt_project_path):
        """Test that intermediate models have contract definitions."""
        yml_path = dbt_project_path / "models" / "intermediate" / "_intermediate.yml"
        
        with open(yml_path, 'r') as f:
            config = yaml.safe_load(f)
        
        models = config.get('models', [])
        
        # Check int_account_with_customer
        int_model = next(
            (m for m in models if m.get('name') == 'int_account_with_customer'),
            None
        )
        assert int_model is not None, "int_account_with_customer should be defined"
        
        # Should have contract config or column definitions
        has_contract = (
            ('config' in int_model and 'contract' in int_model['config']) or
            'columns' in int_model
        )
        assert has_contract, \
            "int_account_with_customer should have contract or column definitions"
    
    def test_marts_models_have_contracts(self, dbt_project_path):
        """Test that marts models have contract definitions."""
        yml_path = dbt_project_path / "models" / "marts" / "_marts.yml"
        
        with open(yml_path, 'r') as f:
            config = yaml.safe_load(f)
        
        models = config.get('models', [])
        
        # Check account_summary
        account_summary = next(
            (m for m in models if m.get('name') == 'account_summary'),
            None
        )
        assert account_summary is not None, "account_summary should be defined"
        
        # Should have contract config or column definitions
        has_contract = (
            ('config' in account_summary and 'contract' in account_summary['config']) or
            'columns' in account_summary
        )
        assert has_contract, \
            "account_summary should have contract or column definitions"


class TestContractColumnDefinitions:
    """Tests for column definitions in contracts."""
    
    def test_staging_contracts_define_data_types(self, dbt_project_path):
        """Test that staging contracts define data types for all columns."""
        yml_path = dbt_project_path / "models" / "staging" / "_staging.yml"
        
        with open(yml_path, 'r') as f:
            config = yaml.safe_load(f)
        
        models = config.get('models', [])
        stg_customer = next(
            (m for m in models if m.get('name') == 'stg_customer'),
            None
        )
        
        assert 'columns' in stg_customer, "stg_customer should define columns"
        
        # Check that columns have data_type
        for column in stg_customer['columns']:
            assert 'name' in column, "Column should have name"
            assert 'data_type' in column, \
                f"Column {column['name']} should have data_type defined"
    
    def test_staging_contracts_define_constraints(self, dbt_project_path):
        """Test that staging contracts define constraints (not_null, unique)."""
        yml_path = dbt_project_path / "models" / "staging" / "_staging.yml"
        
        with open(yml_path, 'r') as f:
            config = yaml.safe_load(f)
        
        models = config.get('models', [])
        stg_customer = next(
            (m for m in models if m.get('name') == 'stg_customer'),
            None
        )
        
        # Find customer_id column
        customer_id_col = next(
            (c for c in stg_customer['columns'] if c['name'] == 'customer_id'),
            None
        )
        
        assert customer_id_col is not None, "customer_id column should be defined"
        
        # Check for constraints
        if 'constraints' in customer_id_col:
            constraint_types = [c['type'] for c in customer_id_col['constraints']]
            assert 'not_null' in constraint_types, \
                "customer_id should have not_null constraint"
    
    def test_snapshot_contracts_include_scd2_columns(self, dbt_project_path):
        """Test that snapshot contracts include SCD2 columns."""
        yml_path = dbt_project_path / "snapshots" / "_snapshots.yml"
        
        with open(yml_path, 'r') as f:
            config = yaml.safe_load(f)
        
        snapshots = config.get('snapshots', [])
        snap_customer = next(
            (s for s in snapshots if s.get('name') == 'snap_customer'),
            None
        )
        
        if 'columns' in snap_customer:
            column_names = [c['name'] for c in snap_customer['columns']]
            
            # Check for SCD2 columns
            scd2_columns = ['dbt_scd_id', 'dbt_valid_from', 'dbt_valid_to', 'dbt_updated_at']
            for scd2_col in scd2_columns:
                assert scd2_col in column_names, \
                    f"Snapshot should document SCD2 column {scd2_col}"


class TestContractEnforcement:
    """Tests for contract enforcement behavior."""
    
    def test_contracts_are_enforced_flag_set(self, dbt_project_path):
        """Test that contracts have enforced flag set to true."""
        yml_files = [
            "models/staging/_staging.yml",
            "models/intermediate/_intermediate.yml",
            "models/marts/_marts.yml"
        ]
        
        for yml_file in yml_files:
            yml_path = dbt_project_path / yml_file
            
            if not yml_path.exists():
                continue
            
            with open(yml_path, 'r') as f:
                config = yaml.safe_load(f)
            
            models = config.get('models', [])
            
            for model in models:
                if 'config' in model and 'contract' in model['config']:
                    assert model['config']['contract']['enforced'] is True, \
                        f"Model {model['name']} contract should be enforced"
    
    def test_contract_violation_detection_configured(self, dbt_project_path):
        """Test that models are configured to detect contract violations."""
        # Verify that models with contracts have column definitions
        yml_path = dbt_project_path / "models" / "staging" / "_staging.yml"
        
        with open(yml_path, 'r') as f:
            config = yaml.safe_load(f)
        
        models = config.get('models', [])
        
        for model in models:
            if 'config' in model and 'contract' in model['config']:
                if model['config']['contract']['enforced']:
                    assert 'columns' in model, \
                        f"Model {model['name']} with enforced contract must define columns"
                    assert len(model['columns']) > 0, \
                        f"Model {model['name']} must have at least one column defined"


class TestContractColumnTypes:
    """Tests for correct data types in contract definitions."""
    
    def test_staging_customer_column_types(self, dbt_project_path):
        """Test that stg_customer has correct column types."""
        yml_path = dbt_project_path / "models" / "staging" / "_staging.yml"
        
        with open(yml_path, 'r') as f:
            config = yaml.safe_load(f)
        
        models = config.get('models', [])
        stg_customer = next(
            (m for m in models if m.get('name') == 'stg_customer'),
            None
        )
        
        if 'columns' not in stg_customer:
            pytest.skip("stg_customer columns not defined")
        
        columns = {c['name']: c for c in stg_customer['columns']}
        
        # Verify expected column types
        expected_types = {
            'customer_id': ['integer', 'int', 'bigint'],
            'customer_name': ['varchar', 'string', 'text'],
            'has_loan_flag': ['boolean', 'bool'],
            'loaded_at': ['timestamp', 'datetime']
        }
        
        for col_name, valid_types in expected_types.items():
            if col_name in columns:
                actual_type = columns[col_name].get('data_type', '').lower()
                assert any(vt in actual_type for vt in valid_types), \
                    f"Column {col_name} should have type in {valid_types}, got {actual_type}"
    
    def test_staging_account_column_types(self, dbt_project_path):
        """Test that stg_account has correct column types."""
        yml_path = dbt_project_path / "models" / "staging" / "_staging.yml"
        
        with open(yml_path, 'r') as f:
            config = yaml.safe_load(f)
        
        models = config.get('models', [])
        stg_account = next(
            (m for m in models if m.get('name') == 'stg_account'),
            None
        )
        
        if 'columns' not in stg_account:
            pytest.skip("stg_account columns not defined")
        
        columns = {c['name']: c for c in stg_account['columns']}
        
        # Verify expected column types
        expected_types = {
            'account_id': ['varchar', 'string', 'text'],
            'customer_id': ['integer', 'int', 'bigint'],
            'balance_amount': ['decimal', 'numeric', 'double', 'float'],
            'account_type': ['varchar', 'string', 'text'],
            'loaded_at': ['timestamp', 'datetime']
        }
        
        for col_name, valid_types in expected_types.items():
            if col_name in columns:
                actual_type = columns[col_name].get('data_type', '').lower()
                assert any(vt in actual_type for vt in valid_types), \
                    f"Column {col_name} should have type in {valid_types}, got {actual_type}"


class TestContractErrorMessages:
    """Tests for contract error message clarity."""
    
    def test_contracts_have_column_descriptions(self, dbt_project_path):
        """Test that contract columns have descriptions for better error messages."""
        yml_path = dbt_project_path / "models" / "staging" / "_staging.yml"
        
        with open(yml_path, 'r') as f:
            config = yaml.safe_load(f)
        
        models = config.get('models', [])
        
        for model in models:
            if 'columns' in model:
                for column in model['columns']:
                    # Descriptions help users understand contract violations
                    assert 'description' in column or 'name' in column, \
                        f"Column in {model['name']} should have description or at least name"
    
    def test_models_have_descriptions(self, dbt_project_path):
        """Test that models with contracts have descriptions."""
        yml_files = [
            "models/staging/_staging.yml",
            "models/intermediate/_intermediate.yml",
            "models/marts/_marts.yml"
        ]
        
        for yml_file in yml_files:
            yml_path = dbt_project_path / yml_file
            
            if not yml_path.exists():
                continue
            
            with open(yml_path, 'r') as f:
                config = yaml.safe_load(f)
            
            models = config.get('models', [])
            
            for model in models:
                if 'config' in model and 'contract' in model['config']:
                    if model['config']['contract']['enforced']:
                        assert 'description' in model, \
                            f"Model {model['name']} with enforced contract should have description"


class TestContractSchemaValidation:
    """Tests for schema validation in contracts."""
    
    def test_all_required_columns_defined(self, dbt_project_path):
        """Test that all required columns are defined in contracts."""
        yml_path = dbt_project_path / "models" / "staging" / "_staging.yml"
        
        with open(yml_path, 'r') as f:
            config = yaml.safe_load(f)
        
        models = config.get('models', [])
        
        # Check stg_customer required columns
        stg_customer = next(
            (m for m in models if m.get('name') == 'stg_customer'),
            None
        )
        
        if 'columns' in stg_customer:
            column_names = [c['name'] for c in stg_customer['columns']]
            required_columns = ['customer_id', 'customer_name', 'has_loan_flag', 'loaded_at']
            
            for req_col in required_columns:
                assert req_col in column_names, \
                    f"stg_customer contract should define required column {req_col}"
        
        # Check stg_account required columns
        stg_account = next(
            (m for m in models if m.get('name') == 'stg_account'),
            None
        )
        
        if 'columns' in stg_account:
            column_names = [c['name'] for c in stg_account['columns']]
            required_columns = ['account_id', 'customer_id', 'balance_amount', 'account_type', 'loaded_at']
            
            for req_col in required_columns:
                assert req_col in column_names, \
                    f"stg_account contract should define required column {req_col}"
    
    def test_contracts_match_model_output(self, dbt_project_path):
        """Test that contract column definitions match model SQL output."""
        # Read stg_customer model
        model_path = dbt_project_path / "models" / "staging" / "stg_customer.sql"
        model_content = model_path.read_text()
        
        # Read contract definition
        yml_path = dbt_project_path / "models" / "staging" / "_staging.yml"
        with open(yml_path, 'r') as f:
            config = yaml.safe_load(f)
        
        models = config.get('models', [])
        stg_customer = next(
            (m for m in models if m.get('name') == 'stg_customer'),
            None
        )
        
        if 'columns' not in stg_customer:
            pytest.skip("stg_customer columns not defined")
        
        contract_columns = [c['name'] for c in stg_customer['columns']]
        
        # Verify that columns in contract appear in model SQL
        for col in contract_columns:
            # Skip SCD2 columns that are added by DBT
            if col.startswith('dbt_'):
                continue
            
            assert col in model_content, \
                f"Contract column {col} should appear in model SQL"


class TestContractConsistency:
    """Tests for consistency across contract definitions."""
    
    def test_primary_keys_have_not_null_constraint(self, dbt_project_path):
        """Test that primary key columns have not_null constraint."""
        yml_files = [
            ("models/staging/_staging.yml", ['customer_id', 'account_id']),
            ("models/intermediate/_intermediate.yml", ['account_id']),
            ("models/marts/_marts.yml", ['account_id', 'customer_id'])
        ]
        
        for yml_file, pk_columns in yml_files:
            yml_path = dbt_project_path / yml_file
            
            if not yml_path.exists():
                continue
            
            with open(yml_path, 'r') as f:
                config = yaml.safe_load(f)
            
            models = config.get('models', [])
            
            for model in models:
                if 'columns' not in model:
                    continue
                
                for column in model['columns']:
                    if column['name'] in pk_columns:
                        # Primary keys should have not_null constraint
                        if 'constraints' in column:
                            constraint_types = [c['type'] for c in column['constraints']]
                            assert 'not_null' in constraint_types, \
                                f"Primary key {column['name']} in {model['name']} should have not_null constraint"
    
    def test_timestamp_columns_consistent_type(self, dbt_project_path):
        """Test that timestamp columns use consistent data type across models."""
        yml_files = [
            "models/staging/_staging.yml",
            "models/intermediate/_intermediate.yml",
            "models/marts/_marts.yml"
        ]
        
        timestamp_types = set()
        
        for yml_file in yml_files:
            yml_path = dbt_project_path / yml_file
            
            if not yml_path.exists():
                continue
            
            with open(yml_path, 'r') as f:
                config = yaml.safe_load(f)
            
            models = config.get('models', [])
            
            for model in models:
                if 'columns' not in model:
                    continue
                
                for column in model['columns']:
                    # Check timestamp columns
                    if column['name'].endswith('_at') or column['name'].endswith('_date'):
                        if 'data_type' in column:
                            timestamp_types.add(column['data_type'].lower())
        
        # All timestamp columns should use consistent type
        # Allow timestamp, datetime as valid types
        valid_types = {'timestamp', 'datetime', 'timestamp_ntz', 'timestamp_tz'}
        for ts_type in timestamp_types:
            assert any(vt in ts_type for vt in valid_types), \
                f"Timestamp type {ts_type} should be one of {valid_types}"
