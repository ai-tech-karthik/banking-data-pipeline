"""
Integration tests for naming convention compliance.

These tests verify that all tables and columns follow standardized naming
conventions including snake_case, prefixes, suffixes, and singular nouns.
"""
import os
import re
from pathlib import Path

import pytest
import yaml


@pytest.fixture
def dbt_project_path():
    """Get the path to the DBT project."""
    return Path(__file__).parent.parent.parent / "dbt_project"


class TestTableNamingConventions:
    """Tests for table naming conventions."""
    
    def test_source_tables_use_src_prefix(self, dbt_project_path):
        """Test that source layer tables use 'src_' prefix."""
        source_dir = dbt_project_path / "models" / "source"
        
        if not source_dir.exists():
            pytest.skip("Source directory does not exist")
        
        sql_files = list(source_dir.glob("*.sql"))
        
        for sql_file in sql_files:
            # Skip non-model files
            if sql_file.name.startswith('_'):
                continue
            
            assert sql_file.stem.startswith('src_'), \
                f"Source model {sql_file.name} should start with 'src_' prefix"
    
    def test_staging_tables_use_stg_prefix(self, dbt_project_path):
        """Test that staging layer tables use 'stg_' prefix."""
        staging_dir = dbt_project_path / "models" / "staging"
        
        sql_files = list(staging_dir.glob("*.sql"))
        
        for sql_file in sql_files:
            # Skip non-model files
            if sql_file.name.startswith('_') or sql_file.name.startswith('quarantine_'):
                continue
            
            assert sql_file.stem.startswith('stg_'), \
                f"Staging model {sql_file.name} should start with 'stg_' prefix"
    
    def test_snapshot_tables_use_snap_prefix(self, dbt_project_path):
        """Test that snapshot layer tables use 'snap_' prefix."""
        snapshots_dir = dbt_project_path / "snapshots"
        
        if not snapshots_dir.exists():
            pytest.skip("Snapshots directory does not exist")
        
        sql_files = list(snapshots_dir.glob("*.sql"))
        
        for sql_file in sql_files:
            # Skip non-snapshot files
            if sql_file.name.startswith('_'):
                continue
            
            assert sql_file.stem.startswith('snap_'), \
                f"Snapshot model {sql_file.name} should start with 'snap_' prefix"
    
    def test_intermediate_tables_use_int_prefix(self, dbt_project_path):
        """Test that intermediate layer tables use 'int_' prefix."""
        intermediate_dir = dbt_project_path / "models" / "intermediate"
        
        sql_files = list(intermediate_dir.glob("*.sql"))
        
        for sql_file in sql_files:
            # Skip non-model files
            if sql_file.name.startswith('_'):
                continue
            
            assert sql_file.stem.startswith('int_'), \
                f"Intermediate model {sql_file.name} should start with 'int_' prefix"
    
    def test_marts_tables_no_prefix(self, dbt_project_path):
        """Test that marts layer tables have no prefix."""
        marts_dir = dbt_project_path / "models" / "marts"
        
        sql_files = list(marts_dir.glob("*.sql"))
        
        for sql_file in sql_files:
            # Skip non-model files
            if sql_file.name.startswith('_'):
                continue
            
            # Marts should not have prefixes
            assert not sql_file.stem.startswith(('src_', 'stg_', 'snap_', 'int_')), \
                f"Marts model {sql_file.name} should not have layer prefix"
    
    def test_table_names_use_snake_case(self, dbt_project_path):
        """Test that all table names use snake_case."""
        model_dirs = [
            "models/source",
            "models/staging",
            "models/intermediate",
            "models/marts",
            "snapshots"
        ]
        
        for model_dir in model_dirs:
            dir_path = dbt_project_path / model_dir
            
            if not dir_path.exists():
                continue
            
            sql_files = list(dir_path.glob("*.sql"))
            
            for sql_file in sql_files:
                # Skip non-model files
                if sql_file.name.startswith('_'):
                    continue
                
                # Check for snake_case (lowercase with underscores)
                assert sql_file.stem.islower(), \
                    f"Table name {sql_file.name} should be lowercase"
                assert not re.search(r'[A-Z]', sql_file.stem), \
                    f"Table name {sql_file.name} should not contain uppercase letters"
                assert not re.search(r'[-\s]', sql_file.stem), \
                    f"Table name {sql_file.name} should not contain hyphens or spaces"
    
    def test_table_names_use_singular_nouns(self, dbt_project_path):
        """Test that table names use singular nouns."""
        model_dirs = [
            "models/source",
            "models/staging",
            "models/intermediate",
            "models/marts",
            "snapshots"
        ]
        
        # Common plural endings to check
        plural_patterns = [
            r'customers\.sql$',
            r'accounts\.sql$',
            r'orders\.sql$',
            r'products\.sql$',
            r'users\.sql$'
        ]
        
        for model_dir in model_dirs:
            dir_path = dbt_project_path / model_dir
            
            if not dir_path.exists():
                continue
            
            sql_files = list(dir_path.glob("*.sql"))
            
            for sql_file in sql_files:
                # Skip non-model files
                if sql_file.name.startswith('_'):
                    continue
                
                # Check for plural endings
                for pattern in plural_patterns:
                    assert not re.search(pattern, sql_file.name), \
                        f"Table name {sql_file.name} should use singular noun (not plural)"


class TestColumnNamingConventions:
    """Tests for column naming conventions."""
    
    def test_columns_use_snake_case(self, dbt_project_path):
        """Test that all columns use snake_case."""
        yml_files = [
            "models/staging/_staging.yml",
            "models/intermediate/_intermediate.yml",
            "models/marts/_marts.yml",
            "snapshots/_snapshots.yml"
        ]
        
        for yml_file in yml_files:
            yml_path = dbt_project_path / yml_file
            
            if not yml_path.exists():
                continue
            
            with open(yml_path, 'r') as f:
                config = yaml.safe_load(f)
            
            # Get models or snapshots
            items = config.get('models', []) or config.get('snapshots', [])
            
            for item in items:
                if 'columns' not in item:
                    continue
                
                for column in item['columns']:
                    col_name = column['name']
                    
                    # Check for snake_case
                    assert col_name.islower(), \
                        f"Column {col_name} in {item['name']} should be lowercase"
                    assert not re.search(r'[A-Z]', col_name), \
                        f"Column {col_name} in {item['name']} should not contain uppercase"
                    assert not re.search(r'[-\s]', col_name), \
                        f"Column {col_name} in {item['name']} should not contain hyphens or spaces"
    
    def test_boolean_columns_use_flag_suffix(self, dbt_project_path):
        """Test that boolean columns use '_flag' or '_ind' suffix."""
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
                if 'columns' not in model:
                    continue
                
                for column in model['columns']:
                    col_name = column['name']
                    data_type = column.get('data_type', '').lower()
                    
                    # Check boolean columns
                    if 'bool' in data_type:
                        assert col_name.endswith(('_flag', '_ind', '_is')), \
                            f"Boolean column {col_name} in {model['name']} should end with '_flag', '_ind', or '_is'"
    
    def test_timestamp_columns_use_at_suffix(self, dbt_project_path):
        """Test that timestamp columns use '_at' or '_date' suffix."""
        yml_files = [
            "models/staging/_staging.yml",
            "models/intermediate/_intermediate.yml",
            "models/marts/_marts.yml",
            "snapshots/_snapshots.yml"
        ]
        
        for yml_file in yml_files:
            yml_path = dbt_project_path / yml_file
            
            if not yml_path.exists():
                continue
            
            with open(yml_path, 'r') as f:
                config = yaml.safe_load(f)
            
            # Get models or snapshots
            items = config.get('models', []) or config.get('snapshots', [])
            
            for item in items:
                if 'columns' not in item:
                    continue
                
                for column in item['columns']:
                    col_name = column['name']
                    data_type = column.get('data_type', '').lower()
                    
                    # Check timestamp columns
                    if 'timestamp' in data_type or 'datetime' in data_type:
                        # Skip DBT-generated columns
                        if col_name.startswith('dbt_'):
                            continue
                        
                        assert col_name.endswith(('_at', '_date', '_time', '_timestamp')), \
                            f"Timestamp column {col_name} in {item['name']} should end with '_at', '_date', '_time', or '_timestamp'"
    
    def test_amount_columns_use_amount_suffix(self, dbt_project_path):
        """Test that amount columns use '_amount' suffix."""
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
                if 'columns' not in model:
                    continue
                
                for column in model['columns']:
                    col_name = column['name']
                    
                    # Check for amount-related columns
                    if 'balance' in col_name or 'interest' in col_name:
                        if not col_name.endswith(('_pct', '_rate', '_count')):
                            assert col_name.endswith('_amount'), \
                                f"Amount column {col_name} in {model['name']} should end with '_amount'"
    
    def test_percentage_columns_use_pct_suffix(self, dbt_project_path):
        """Test that percentage columns use '_pct' suffix."""
        yml_files = [
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
                if 'columns' not in model:
                    continue
                
                for column in model['columns']:
                    col_name = column['name']
                    
                    # Check for rate/percentage columns
                    if 'rate' in col_name and 'interest' in col_name:
                        assert col_name.endswith('_pct') or col_name.endswith('_rate'), \
                            f"Percentage column {col_name} in {model['name']} should end with '_pct' or '_rate'"
    
    def test_count_columns_use_count_suffix(self, dbt_project_path):
        """Test that count columns use '_count' suffix."""
        yml_files = [
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
                if 'columns' not in model:
                    continue
                
                for column in model['columns']:
                    col_name = column['name']
                    data_type = column.get('data_type', '').lower()
                    
                    # Check for count columns
                    if 'total' in col_name and 'count' not in col_name:
                        if 'int' in data_type or 'number' in data_type:
                            # Could be a count column
                            if not col_name.endswith(('_amount', '_balance', '_id')):
                                assert col_name.endswith('_count'), \
                                    f"Count column {col_name} in {model['name']} should end with '_count'"


class TestStandardizationMacros:
    """Tests for standardization macros."""
    
    def test_standardize_column_name_macro_exists(self, dbt_project_path):
        """Test that standardize_column_name macro exists."""
        macro_path = dbt_project_path / "macros" / "standardize_column_name.sql"
        assert macro_path.exists(), \
            "standardize_column_name macro should exist"
    
    def test_clean_string_macro_exists(self, dbt_project_path):
        """Test that clean_string macro exists."""
        macro_path = dbt_project_path / "macros" / "clean_string.sql"
        assert macro_path.exists(), \
            "clean_string macro should exist"
    
    def test_standardize_boolean_macro_exists(self, dbt_project_path):
        """Test that standardize_boolean macro exists."""
        macro_path = dbt_project_path / "macros" / "standardize_boolean.sql"
        assert macro_path.exists(), \
            "standardize_boolean macro should exist"
    
    def test_standardize_column_name_macro_handles_spaces(self, dbt_project_path):
        """Test that standardize_column_name macro handles spaces."""
        macro_path = dbt_project_path / "macros" / "standardize_column_name.sql"
        content = macro_path.read_text()
        
        # Should replace spaces with underscores
        assert "replace(' ', '_')" in content or "replace(\" \", \"_\")" in content, \
            "standardize_column_name should replace spaces with underscores"
    
    def test_standardize_column_name_macro_converts_lowercase(self, dbt_project_path):
        """Test that standardize_column_name macro converts to lowercase."""
        macro_path = dbt_project_path / "macros" / "standardize_column_name.sql"
        content = macro_path.read_text()
        
        # Should convert to lowercase
        assert "lower" in content.lower(), \
            "standardize_column_name should convert to lowercase"
    
    def test_clean_string_macro_trims_whitespace(self, dbt_project_path):
        """Test that clean_string macro trims whitespace."""
        macro_path = dbt_project_path / "macros" / "clean_string.sql"
        content = macro_path.read_text()
        
        # Should trim whitespace
        assert "trim" in content.lower(), \
            "clean_string should trim whitespace"
    
    def test_standardize_boolean_macro_handles_yes_no(self, dbt_project_path):
        """Test that standardize_boolean macro handles yes/no values."""
        macro_path = dbt_project_path / "macros" / "standardize_boolean.sql"
        content = macro_path.read_text()
        
        # Should handle yes/no
        assert "'yes'" in content.lower() or "\"yes\"" in content.lower(), \
            "standardize_boolean should handle 'yes' value"
        assert "'no'" in content.lower() or "\"no\"" in content.lower(), \
            "standardize_boolean should handle 'no' value"


class TestNamingConsistency:
    """Tests for naming consistency across layers."""
    
    def test_customer_id_consistent_across_layers(self, dbt_project_path):
        """Test that customer_id is named consistently across all layers."""
        yml_files = [
            "models/staging/_staging.yml",
            "models/intermediate/_intermediate.yml",
            "models/marts/_marts.yml"
        ]
        
        customer_id_names = set()
        
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
                    col_name = column['name']
                    if 'customer' in col_name and 'id' in col_name:
                        customer_id_names.add(col_name)
        
        # Should use consistent naming
        assert len(customer_id_names) <= 1, \
            f"customer_id should be named consistently, found: {customer_id_names}"
        
        if customer_id_names:
            assert 'customer_id' in customer_id_names, \
                "customer_id should be the standard name"
    
    def test_account_id_consistent_across_layers(self, dbt_project_path):
        """Test that account_id is named consistently across all layers."""
        yml_files = [
            "models/staging/_staging.yml",
            "models/intermediate/_intermediate.yml",
            "models/marts/_marts.yml"
        ]
        
        account_id_names = set()
        
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
                    col_name = column['name']
                    if 'account' in col_name and 'id' in col_name:
                        account_id_names.add(col_name)
        
        # Should use consistent naming
        assert len(account_id_names) <= 1, \
            f"account_id should be named consistently, found: {account_id_names}"
        
        if account_id_names:
            assert 'account_id' in account_id_names, \
                "account_id should be the standard name"
    
    def test_no_camelcase_in_column_names(self, dbt_project_path):
        """Test that no columns use camelCase."""
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
                if 'columns' not in model:
                    continue
                
                for column in model['columns']:
                    col_name = column['name']
                    
                    # Skip DBT-generated columns
                    if col_name.startswith('dbt_'):
                        continue
                    
                    # Check for camelCase (lowercase followed by uppercase)
                    assert not re.search(r'[a-z][A-Z]', col_name), \
                        f"Column {col_name} in {model['name']} should not use camelCase"
    
    def test_no_abbreviations_in_names(self, dbt_project_path):
        """Test that names avoid common abbreviations."""
        yml_files = [
            "models/staging/_staging.yml",
            "models/intermediate/_intermediate.yml",
            "models/marts/_marts.yml"
        ]
        
        # Common abbreviations to avoid
        abbreviations = ['cust', 'acct', 'addr', 'qty', 'amt']
        
        for yml_file in yml_files:
            yml_path = dbt_project_path / yml_file
            
            if not yml_path.exists():
                continue
            
            with open(yml_path, 'r') as f:
                config = yaml.safe_load(f)
            
            models = config.get('models', [])
            
            for model in models:
                # Check model name
                for abbr in abbreviations:
                    assert abbr not in model['name'], \
                        f"Model {model['name']} should not use abbreviation '{abbr}'"
                
                # Check column names
                if 'columns' not in model:
                    continue
                
                for column in model['columns']:
                    col_name = column['name']
                    
                    # Check for abbreviations (as whole words)
                    for abbr in abbreviations:
                        # Check if abbreviation appears as a word (not part of another word)
                        pattern = rf'\b{abbr}\b'
                        assert not re.search(pattern, col_name), \
                            f"Column {col_name} in {model['name']} should not use abbreviation '{abbr}'"
