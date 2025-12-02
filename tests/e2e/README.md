# End-to-End Testing Suite

This directory contains comprehensive end-to-end tests for the enhanced LendingClub data pipeline with five-layer architecture, SCD2 tracking, and incremental processing.

## Test Files

### 1. test_initial_full_load.py
Tests for initial full load with `--full-refresh` flag.

**Test Classes:**
- `TestInitialFullLoad`: Validates that all five layers are created, snapshots have initial versions, contracts pass, and data quality tests pass.

**Key Tests:**
- `test_all_five_layers_created`: Verifies Source, Staging, Snapshots, Intermediate, and Marts layers
- `test_snapshots_have_initial_versions`: Validates SCD2 columns (dbt_scd_id, dbt_valid_from, dbt_valid_to)
- `test_all_contracts_pass`: Ensures DBT contracts are enforced
- `test_all_data_quality_tests_pass`: Validates all data quality checks
- `test_row_counts_match_expectations`: Verifies data flows correctly through layers
- `test_data_transformations_applied_correctly`: Checks staging transformations and mart calculations
- `test_naming_conventions_followed`: Validates snake_case and layer prefixes

### 2. test_incremental_load.py
Tests for incremental load with data changes.

**Test Classes:**
- `TestIncrementalLoad`: Validates CDC processing and snapshot versioning.

**Key Tests:**
- `test_snapshots_create_new_versions_on_change`: Verifies new SCD2 versions are created
- `test_unchanged_records_not_duplicated`: Ensures unchanged records don't create new versions
- `test_incremental_models_process_only_changed_data`: Validates CDC efficiency
- `test_marts_updated_correctly`: Checks mart calculations after incremental load
- `test_new_records_added_incrementally`: Validates new record insertion
- `test_deleted_records_invalidated`: Tests invalidate_hard_deletes behavior
- `test_multiple_changes_tracked_correctly`: Validates version history over time

### 3. test_error_scenarios.py
Tests for error handling and recovery.

**Test Classes:**
- `TestSchemaChangeDetection`: Validates schema change detection
- `TestContractViolations`: Tests contract enforcement
- `TestDataQualityTestFailures`: Validates data quality test failures
- `TestIncrementalLoadFailureRecovery`: Tests recovery procedures
- `TestErrorMessageClarity`: Validates error message quality
- `TestRecoveryProcedures`: Tests recovery mechanisms

**Key Tests:**
- `test_missing_column_detected`: Schema change detection
- `test_contract_violation_fails_build`: Contract enforcement
- `test_uniqueness_violation_detected`: Data quality validation
- `test_full_refresh_recovers_from_corruption`: Recovery procedures
- `test_missing_file_error_is_clear`: Error message clarity

### 4. test_performance.py
Tests for performance validation.

**Test Classes:**
- `TestInitialLoadPerformance`: Measures initial load times
- `TestIncrementalLoadPerformance`: Validates incremental performance gains
- `TestSnapshotStorageGrowth`: Monitors storage growth
- `TestQueryPerformance`: Tests query performance

**Key Tests:**
- `test_measure_initial_load_time`: Baseline performance measurement
- `test_incremental_faster_than_full_refresh`: Validates CDC performance benefit
- `test_incremental_processes_fewer_records`: Confirms only changed records processed
- `test_snapshot_storage_growth_is_manageable`: Validates storage efficiency
- `test_current_records_query_performance`: Query optimization validation

### 5. test_documentation.py
Tests for documentation completeness and accessibility.

**Test Classes:**
- `TestDocumentationGeneration`: Validates dbt docs generate
- `TestLineageGraph`: Tests lineage graph completeness
- `TestModelDocumentation`: Validates model descriptions
- `TestColumnDocumentation`: Validates column descriptions
- `TestDocumentationAccessibility`: Tests dbt docs serve
- `TestDocumentationCompleteness`: Overall documentation validation

**Key Tests:**
- `test_dbt_docs_generate_succeeds`: Documentation generation
- `test_lineage_graph_shows_all_layers`: Five-layer lineage validation
- `test_all_models_have_descriptions`: Model documentation completeness
- `test_all_columns_have_descriptions`: Column documentation completeness
- `test_scd2_columns_documented`: SCD2 column documentation

## Running Tests

### Run All E2E Tests
```bash
pytest tests/e2e/
```

### Run Specific Test File
```bash
pytest tests/e2e/test_initial_full_load.py
```

### Run Specific Test Class
```bash
pytest tests/e2e/test_initial_full_load.py::TestInitialFullLoad
```

### Run Specific Test
```bash
pytest tests/e2e/test_initial_full_load.py::TestInitialFullLoad::test_all_five_layers_created
```

### Run with Verbose Output
```bash
pytest tests/e2e/ -v
```

### Run with Coverage
```bash
pytest tests/e2e/ --cov=src/lending_club_pipeline
```

## Test Requirements

### Prerequisites
- DBT installed and configured
- DuckDB (for local testing)
- Python dependencies from requirements.txt
- Sample data files (Customer.csv, accounts.csv)

### Environment Variables
Tests use temporary directories and set up their own environments, but you may need:
- `DATABASE_TYPE=duckdb`
- `DBT_TARGET=dev`

## Test Data

Tests create their own sample data with:
- 3-100 customers (depending on test)
- 3-500 accounts (depending on test)
- Various balance tiers to test interest rate logic
- Different account types (Savings, Checking)

## Expected Behavior

### Initial Load
- All 5 layers created (Source, Staging, Snapshots, Intermediate, Marts)
- Each record has exactly 1 snapshot version
- All contracts pass
- All data quality tests pass
- Naming conventions followed

### Incremental Load
- Changed records create new snapshot versions
- Unchanged records not duplicated
- Old versions get dbt_valid_to set
- New versions have dbt_valid_to = NULL
- Marts updated correctly

### Error Scenarios
- Schema changes detected
- Contract violations fail build
- Data quality test failures reported
- Clear error messages provided
- Recovery procedures work

### Performance
- Incremental faster than full refresh
- Storage growth manageable
- Query performance acceptable

### Documentation
- All models documented
- All columns documented
- Lineage graph complete
- Documentation accessible via dbt docs serve

## Test Coverage

Total: 69 tests across 5 files

- Initial Full Load: 7 tests
- Incremental Load: 7 tests
- Error Scenarios: 18 tests
- Performance: 10 tests
- Documentation: 20 tests

## Notes

- Tests use temporary directories and databases
- Tests clean up after themselves
- Some tests may skip if prerequisites not met
- Performance tests use larger datasets (100-500 records)
- Documentation tests validate YAML structure and content
