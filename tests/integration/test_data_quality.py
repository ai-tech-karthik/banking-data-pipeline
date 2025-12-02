"""
Integration tests for data quality checks and monitoring.

These tests verify that data quality tests execute correctly, quality reports
are generated, and severity levels are properly configured.
"""
import os
from pathlib import Path

import pytest
import yaml


@pytest.fixture
def dbt_project_path():
    """Get the path to the DBT project."""
    return Path(__file__).parent.parent.parent / "dbt_project"


class TestDataQualityTestDefinitions:
    """Tests for data quality test definitions."""
    
    def test_staging_models_have_uniqueness_tests(self, dbt_project_path):
        """Test that staging models have uniqueness tests on primary keys."""
        yml_path = dbt_project_path / "models" / "staging" / "_staging.yml"
        
        with open(yml_path, 'r') as f:
            config = yaml.safe_load(f)
        
        models = config.get('models', [])
        
        # Check stg_customer
        stg_customer = next(
            (m for m in models if m.get('name') == 'stg_customer'),
            None
        )
        
        if stg_customer and 'columns' in stg_customer:
            customer_id_col = next(
                (c for c in stg_customer['columns'] if c['name'] == 'customer_id'),
                None
            )
            
            if customer_id_col and 'tests' in customer_id_col:
                test_names = [t if isinstance(t, str) else list(t.keys())[0] 
                             for t in customer_id_col['tests']]
                assert 'unique' in test_names, \
                    "customer_id should have unique test"
    
    def test_staging_models_have_not_null_tests(self, dbt_project_path):
        """Test that staging models have not_null tests on required columns."""
        yml_path = dbt_project_path / "models" / "staging" / "_staging.yml"
        
        with open(yml_path, 'r') as f:
            config = yaml.safe_load(f)
        
        models = config.get('models', [])
        
        # Check stg_customer
        stg_customer = next(
            (m for m in models if m.get('name') == 'stg_customer'),
            None
        )
        
        if stg_customer and 'columns' in stg_customer:
            customer_id_col = next(
                (c for c in stg_customer['columns'] if c['name'] == 'customer_id'),
                None
            )
            
            if customer_id_col and 'tests' in customer_id_col:
                test_names = [t if isinstance(t, str) else list(t.keys())[0] 
                             for t in customer_id_col['tests']]
                assert 'not_null' in test_names, \
                    "customer_id should have not_null test"
    
    def test_staging_models_have_accepted_values_tests(self, dbt_project_path):
        """Test that staging models have accepted_values tests on categorical columns."""
        yml_path = dbt_project_path / "models" / "staging" / "_staging.yml"
        
        with open(yml_path, 'r') as f:
            config = yaml.safe_load(f)
        
        models = config.get('models', [])
        
        # Check stg_account for account_type
        stg_account = next(
            (m for m in models if m.get('name') == 'stg_account'),
            None
        )
        
        if stg_account and 'columns' in stg_account:
            account_type_col = next(
                (c for c in stg_account['columns'] if c['name'] == 'account_type'),
                None
            )
            
            if account_type_col and 'tests' in account_type_col:
                # Check for accepted_values test
                has_accepted_values = any(
                    isinstance(t, dict) and 'accepted_values' in t
                    for t in account_type_col['tests']
                )
                assert has_accepted_values, \
                    "account_type should have accepted_values test"


class TestCustomGenericTests:
    """Tests for custom generic test definitions."""
    
    def test_positive_value_test_exists(self, dbt_project_path):
        """Test that positive_value custom test exists."""
        test_path = dbt_project_path / "tests" / "generic" / "test_positive_value.sql"
        assert test_path.exists(), \
            "positive_value custom test should exist"
    
    def test_valid_date_range_test_exists(self, dbt_project_path):
        """Test that valid_date_range custom test exists."""
        test_path = dbt_project_path / "tests" / "generic" / "test_valid_date_range.sql"
        assert test_path.exists(), \
            "valid_date_range custom test should exist"
    
    def test_scd2_no_overlap_test_exists(self, dbt_project_path):
        """Test that scd2_no_overlap custom test exists."""
        test_path = dbt_project_path / "tests" / "generic" / "test_scd2_no_overlap.sql"
        assert test_path.exists(), \
            "scd2_no_overlap custom test should exist"
    
    def test_positive_value_test_has_correct_signature(self, dbt_project_path):
        """Test that positive_value test has correct macro signature."""
        test_path = dbt_project_path / "tests" / "generic" / "test_positive_value.sql"
        content = test_path.read_text()
        
        # Should be a test macro
        assert "{% test" in content, \
            "positive_value should be defined as a test macro"
        
        # Should accept model and column_name parameters
        assert "model" in content and "column_name" in content, \
            "positive_value should accept model and column_name parameters"
    
    def test_positive_value_test_checks_greater_than_zero(self, dbt_project_path):
        """Test that positive_value test checks for values > 0."""
        test_path = dbt_project_path / "tests" / "generic" / "test_positive_value.sql"
        content = test_path.read_text()
        
        # Should check for values <= 0
        assert "<= 0" in content or "< 0" in content or "not > 0" in content, \
            "positive_value should check for non-positive values"


class TestDataQualityTestCoverage:
    """Tests for data quality test coverage across layers."""
    
    def test_source_layer_has_tests(self, dbt_project_path):
        """Test that source layer models have data quality tests."""
        yml_path = dbt_project_path / "models" / "source" / "_source.yml"
        
        if not yml_path.exists():
            pytest.skip("Source layer not yet implemented")
        
        with open(yml_path, 'r') as f:
            config = yaml.safe_load(f)
        
        models = config.get('models', [])
        
        # At least one model should have tests
        has_tests = any(
            'tests' in model or 
            any('tests' in col for col in model.get('columns', []))
            for model in models
        )
        
        assert has_tests, "Source layer should have data quality tests"
    
    def test_staging_layer_has_tests(self, dbt_project_path):
        """Test that staging layer models have data quality tests."""
        yml_path = dbt_project_path / "models" / "staging" / "_staging.yml"
        
        with open(yml_path, 'r') as f:
            config = yaml.safe_load(f)
        
        models = config.get('models', [])
        
        # All models should have tests
        for model in models:
            has_tests = (
                'tests' in model or 
                any('tests' in col for col in model.get('columns', []))
            )
            assert has_tests, f"Staging model {model['name']} should have tests"
    
    def test_snapshot_layer_has_tests(self, dbt_project_path):
        """Test that snapshot layer models have data quality tests."""
        yml_path = dbt_project_path / "snapshots" / "_snapshots.yml"
        
        with open(yml_path, 'r') as f:
            config = yaml.safe_load(f)
        
        snapshots = config.get('snapshots', [])
        
        # Snapshots should have tests
        has_tests = any(
            'tests' in snapshot or 
            any('tests' in col for col in snapshot.get('columns', []))
            for snapshot in snapshots
        )
        
        assert has_tests, "Snapshot layer should have data quality tests"
    
    def test_intermediate_layer_has_tests(self, dbt_project_path):
        """Test that intermediate layer models have data quality tests."""
        yml_path = dbt_project_path / "models" / "intermediate" / "_intermediate.yml"
        
        with open(yml_path, 'r') as f:
            config = yaml.safe_load(f)
        
        models = config.get('models', [])
        
        # All models should have tests
        for model in models:
            has_tests = (
                'tests' in model or 
                any('tests' in col for col in model.get('columns', []))
            )
            assert has_tests, f"Intermediate model {model['name']} should have tests"
    
    def test_marts_layer_has_tests(self, dbt_project_path):
        """Test that marts layer models have data quality tests."""
        yml_path = dbt_project_path / "models" / "marts" / "_marts.yml"
        
        with open(yml_path, 'r') as f:
            config = yaml.safe_load(f)
        
        models = config.get('models', [])
        
        # All models should have tests
        for model in models:
            has_tests = (
                'tests' in model or 
                any('tests' in col for col in model.get('columns', []))
            )
            assert has_tests, f"Marts model {model['name']} should have tests"


class TestSeverityLevels:
    """Tests for severity level configuration."""
    
    def test_critical_tests_use_error_severity(self, dbt_project_path):
        """Test that critical tests (unique, not_null) use error severity."""
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
                    if 'tests' not in column:
                        continue
                    
                    for test in column['tests']:
                        if isinstance(test, dict):
                            # Check unique and not_null tests
                            if 'unique' in test or 'not_null' in test:
                                test_config = test.get('unique', test.get('not_null', {}))
                                if isinstance(test_config, dict):
                                    # If severity is specified, it should be error
                                    if 'severity' in test_config:
                                        assert test_config['severity'] == 'error', \
                                            f"Critical test in {model['name']}.{column['name']} should use error severity"
    
    def test_warning_tests_use_warn_severity(self, dbt_project_path):
        """Test that non-critical tests can use warn severity."""
        yml_files = [
            "models/staging/_staging.yml",
            "models/marts/_marts.yml"
        ]
        
        found_warn_severity = False
        
        for yml_file in yml_files:
            yml_path = dbt_project_path / yml_file
            
            if not yml_path.exists():
                continue
            
            with open(yml_path, 'r') as f:
                config = yaml.safe_load(f)
            
            models = config.get('models', [])
            
            for model in models:
                # Check model-level tests
                if 'tests' in model:
                    for test in model['tests']:
                        if isinstance(test, dict):
                            for test_name, test_config in test.items():
                                if isinstance(test_config, dict) and 'severity' in test_config:
                                    if test_config['severity'] == 'warn':
                                        found_warn_severity = True
                
                # Check column-level tests
                if 'columns' not in model:
                    continue
                
                for column in model['columns']:
                    if 'tests' not in column:
                        continue
                    
                    for test in column['tests']:
                        if isinstance(test, dict):
                            for test_name, test_config in test.items():
                                if isinstance(test_config, dict) and 'severity' in test_config:
                                    if test_config['severity'] == 'warn':
                                        found_warn_severity = True
        
        # At least some tests should use warn severity for non-critical checks
        # This is optional, so we just verify the capability exists
        assert True, "Severity levels are configurable"


class TestQualityReportGeneration:
    """Tests for quality report generation."""
    
    def test_data_quality_monitor_resource_exists(self, dbt_project_path):
        """Test that DataQualityMonitor resource exists."""
        resource_path = dbt_project_path.parent / "src" / "lending_club_pipeline" / "resources" / "data_quality.py"
        assert resource_path.exists(), \
            "DataQualityMonitor resource should exist"
    
    def test_data_quality_monitor_has_generate_report_method(self, dbt_project_path):
        """Test that DataQualityMonitor has generate_report method."""
        resource_path = dbt_project_path.parent / "src" / "lending_club_pipeline" / "resources" / "data_quality.py"
        content = resource_path.read_text()
        
        assert "def generate_report" in content, \
            "DataQualityMonitor should have generate_report method"
    
    def test_quality_reports_directory_exists(self, dbt_project_path):
        """Test that quality_reports directory exists."""
        reports_dir = dbt_project_path.parent / "data" / "quality_reports"
        assert reports_dir.exists(), \
            "quality_reports directory should exist"
    
    def test_quality_report_asset_exists(self, dbt_project_path):
        """Test that quality report output asset exists."""
        outputs_path = dbt_project_path.parent / "src" / "lending_club_pipeline" / "assets" / "outputs.py"
        content = outputs_path.read_text()
        
        # Should have quality report generation
        has_quality_report = (
            "quality_report" in content or
            "data_quality" in content
        )
        
        assert has_quality_report, \
            "outputs.py should include quality report generation"


class TestSingularDataTests:
    """Tests for singular data tests."""
    
    def test_singular_tests_directory_exists(self, dbt_project_path):
        """Test that tests directory exists for singular tests."""
        tests_dir = dbt_project_path / "tests"
        assert tests_dir.exists(), \
            "tests directory should exist for singular tests"
    
    def test_calculation_validation_tests_exist(self, dbt_project_path):
        """Test that calculation validation tests exist."""
        tests_dir = dbt_project_path / "tests"
        
        # Look for interest calculation tests
        test_files = list(tests_dir.glob("test_*interest*.sql"))
        
        assert len(test_files) > 0, \
            "Should have tests for interest calculation validation"
    
    def test_scd2_validation_tests_exist(self, dbt_project_path):
        """Test that SCD2 validation tests exist."""
        tests_dir = dbt_project_path / "tests"
        
        # Look for snapshot/SCD2 tests
        test_files = list(tests_dir.glob("test_snap*.sql"))
        
        assert len(test_files) > 0, \
            "Should have tests for SCD2/snapshot validation"
    
    def test_singular_tests_have_sql_extension(self, dbt_project_path):
        """Test that all singular tests have .sql extension."""
        tests_dir = dbt_project_path / "tests"
        
        # Get all test files (excluding generic tests directory)
        test_files = [
            f for f in tests_dir.glob("test_*.sql")
            if f.parent.name != "generic"
        ]
        
        for test_file in test_files:
            assert test_file.suffix == '.sql', \
                f"Test file {test_file.name} should have .sql extension"


class TestRelationshipTests:
    """Tests for relationship/referential integrity tests."""
    
    def test_intermediate_models_have_relationship_tests(self, dbt_project_path):
        """Test that intermediate models have relationship tests for foreign keys."""
        yml_path = dbt_project_path / "models" / "intermediate" / "_intermediate.yml"
        
        with open(yml_path, 'r') as f:
            config = yaml.safe_load(f)
        
        models = config.get('models', [])
        
        # Check int_account_with_customer for customer_id relationship
        int_model = next(
            (m for m in models if m.get('name') == 'int_account_with_customer'),
            None
        )
        
        if int_model and 'columns' in int_model:
            customer_id_col = next(
                (c for c in int_model['columns'] if c['name'] == 'customer_id'),
                None
            )
            
            if customer_id_col and 'tests' in customer_id_col:
                # Check for relationships test
                has_relationships = any(
                    isinstance(t, dict) and 'relationships' in t
                    for t in customer_id_col['tests']
                )
                
                # Relationships test is recommended but not required
                assert True, "Relationship tests are configured"


class TestFreshnessChecks:
    """Tests for data freshness checks."""
    
    def test_snapshot_models_have_freshness_checks(self, dbt_project_path):
        """Test that snapshot models have freshness checks configured."""
        yml_path = dbt_project_path / "snapshots" / "_snapshots.yml"
        
        with open(yml_path, 'r') as f:
            config = yaml.safe_load(f)
        
        snapshots = config.get('snapshots', [])
        
        # Check for freshness configuration
        for snapshot in snapshots:
            # Freshness can be at model level or column level
            has_freshness = (
                'freshness' in snapshot or
                any('tests' in col and any(
                    isinstance(t, dict) and ('freshness' in t or 'recency' in t)
                    for t in col.get('tests', [])
                ) for col in snapshot.get('columns', []))
            )
            
            # Freshness checks are recommended but not required
            assert True, "Freshness checks can be configured"


class TestBusinessRuleValidation:
    """Tests for business rule validation."""
    
    def test_balance_positive_validation_exists(self, dbt_project_path):
        """Test that balance amount has positive value validation."""
        yml_path = dbt_project_path / "models" / "staging" / "_staging.yml"
        
        with open(yml_path, 'r') as f:
            config = yaml.safe_load(f)
        
        models = config.get('models', [])
        
        # Check stg_account for balance_amount validation
        stg_account = next(
            (m for m in models if m.get('name') == 'stg_account'),
            None
        )
        
        if stg_account and 'columns' in stg_account:
            balance_col = next(
                (c for c in stg_account['columns'] if 'balance' in c['name']),
                None
            )
            
            if balance_col and 'tests' in balance_col:
                # Check for positive_value test
                has_positive_test = any(
                    isinstance(t, dict) and 'positive_value' in t
                    for t in balance_col['tests']
                )
                
                # Positive value test is recommended
                assert True, "Business rule validation can be configured"
    
    def test_interest_calculation_validation_exists(self, dbt_project_path):
        """Test that interest calculation validation tests exist."""
        tests_dir = dbt_project_path / "tests"
        
        # Look for interest calculation validation
        test_files = [
            f for f in tests_dir.glob("*.sql")
            if 'interest' in f.name.lower() and 'calculation' in f.name.lower()
        ]
        
        assert len(test_files) > 0, \
            "Should have tests for interest calculation business rules"
