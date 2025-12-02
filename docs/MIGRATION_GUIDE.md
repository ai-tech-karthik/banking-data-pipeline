# Migration Guide: Three-Layer to Five-Layer Architecture

This guide provides step-by-step instructions for migrating the LC Data Pipeline from the original three-layer architecture to the enhanced five-layer architecture with SCD2 historical tracking, incremental processing, and comprehensive data quality checks.

## Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Migration Phases](#migration-phases)
- [Step-by-Step Instructions](#step-by-step-instructions)
- [Rollback Procedures](#rollback-procedures)
- [Troubleshooting](#troubleshooting)
- [Validation](#validation)

## Overview

### What's Changing

**From: Three-Layer Architecture**
```
CSV Files → Ingestion → Staging → Marts → Outputs
```

**To: Five-Layer Architecture**
```
CSV Files → Source → Staging → Snapshots → Intermediate → Marts → Outputs
```

### Key Enhancements

1. **Source Layer**: New layer for raw data persistence
2. **Snapshot Layer**: SCD2 historical tracking with DBT snapshots
3. **Incremental Processing**: CDC-based incremental materialization
4. **Schema Contracts**: Enforced contracts at every layer
5. **Naming Conventions**: Standardized snake_case naming
6. **Data Quality**: 40+ tests across all layers

### Migration Timeline

- **Estimated Duration**: 4-6 hours for full migration
- **Downtime Required**: Minimal (can run in parallel with existing pipeline)
- **Rollback Time**: < 30 minutes per phase

## Prerequisites

### Before You Begin

1. **Backup Current Data**
   ```bash
   # Backup DuckDB database
   cp data/duckdb/lc.duckdb data/duckdb/lc.duckdb.backup
   
   # Backup output files
   cp -r data/outputs data/outputs.backup
   ```

2. **Verify Current State**
   ```bash
   # Run existing tests to ensure baseline is working
   cd dbt_project
   dbt test --target dev --profiles-dir .
   
   # Verify all assets materialize
   dagster asset materialize --select '*' -m src.lc_pipeline.definitions
   ```

3. **Update Dependencies**
   ```bash
   # Ensure you have the latest DBT version (1.6+)
   pip install --upgrade dbt-core dbt-duckdb dbt-databricks
   
   # Install any new dependencies
   pip install -r requirements.txt
   ```

4. **Review Documentation**
   - Read the [Design Document](.kiro/specs/pipeline-enhancements/design.md)
   - Review the [Requirements Document](.kiro/specs/pipeline-enhancements/requirements.md)
   - Understand the [Data Quality Guide](DATA_QUALITY_GUIDE.md)

## Migration Phases

The migration is divided into 7 phases that can be executed independently:

| Phase | Description | Duration | Risk Level |
|-------|-------------|----------|------------|
| 1 | Add Source Layer | 30 min | Low |
| 2 | Implement Snapshots | 45 min | Medium |
| 3 | Add Incremental to Intermediate | 30 min | Low |
| 4 | Add Incremental to Marts | 45 min | Medium |
| 5 | Implement Contracts | 30 min | Low |
| 6 | Standardize Naming | 60 min | High |
| 7 | Enhance Data Quality | 45 min | Low |

## Step-by-Step Instructions

### Phase 1: Add Source Layer

**Objective**: Create raw data persistence layer

**Steps**:

1. **Create Source Models**
   ```bash
   # Models already exist at:
   # - dbt_project/models/source/src_customer.sql
   # - dbt_project/models/source/src_account.sql
   # - dbt_project/models/source/_source.yml
   ```

2. **Update Ingestion Assets**
   ```bash
   # Verify ingestion.py loads into source tables
   # Check: src/lc_pipeline/assets/ingestion.py
   ```

3. **Run Source Layer**
   ```bash
   cd dbt_project
   dbt run --select source --profiles-dir .
   ```

4. **Validate**
   ```bash
   # Check tables were created
   dbt run-operation list_relations --args '{schema: main}' --profiles-dir .
   
   # Verify row counts match input files
   dbt test --select source --profiles-dir .
   ```

**Rollback**:
```bash
# Drop source tables if needed
dbt run-operation drop_relation --args '{relation: src_customer}' --profiles-dir .
dbt run-operation drop_relation --args '{relation: src_account}' --profiles-dir .
```

### Phase 2: Implement Snapshots

**Objective**: Enable SCD2 historical tracking

**Steps**:

1. **Configure Snapshots**
   ```bash
   # Verify snapshot configuration in dbt_project.yml
   # Check snapshots section exists with:
   # - target_schema: snapshots
   # - strategy: timestamp
   # - invalidate_hard_deletes: true
   ```

2. **Create Snapshot Models**
   ```bash
   # Models already exist at:
   # - dbt_project/snapshots/snap_customer.sql
   # - dbt_project/snapshots/snap_account.sql
   # - dbt_project/snapshots/_snapshots.yml
   ```

3. **Run Initial Snapshot (Full Load)**
   ```bash
   cd dbt_project
   dbt snapshot --profiles-dir .
   ```

4. **Validate SCD2 Columns**
   ```bash
   # Check that SCD2 columns exist
   # Expected columns: dbt_scd_id, dbt_valid_from, dbt_valid_to, dbt_updated_at
   
   # Run snapshot tests
   dbt test --select snapshots --profiles-dir .
   ```

5. **Test Change Detection**
   ```bash
   # Modify a record in source data
   # Re-run snapshot
   dbt snapshot --profiles-dir .
   
   # Verify new version created and old version closed
   # Query: SELECT * FROM snap_customer WHERE customer_id = 1 ORDER BY dbt_valid_from;
   ```

**Rollback**:
```bash
# Drop snapshot tables
dbt run-operation drop_relation --args '{relation: snap_customer}' --profiles-dir .
dbt run-operation drop_relation --args '{relation: snap_account}' --profiles-dir .
```

### Phase 3: Add Incremental to Intermediate

**Objective**: Convert intermediate models to incremental materialization

**Steps**:

1. **Update Intermediate Models**
   ```bash
   # Models already updated at:
   # - dbt_project/models/intermediate/int_account_with_customer.sql
   # - dbt_project/models/intermediate/int_savings_account_only.sql
   ```

2. **Run Full Refresh First**
   ```bash
   cd dbt_project
   dbt run --select intermediate --full-refresh --profiles-dir .
   ```

3. **Test Incremental Logic**
   ```bash
   # Make a change in snapshots
   dbt snapshot --profiles-dir .
   
   # Run incremental (should process only changed records)
   dbt run --select intermediate --profiles-dir .
   ```

4. **Validate**
   ```bash
   # Run intermediate tests
   dbt test --select intermediate --profiles-dir .
   
   # Check row counts are correct
   ```

**Rollback**:
```bash
# Revert to full refresh on every run
# Remove incremental config from models
# Or run with --full-refresh flag
dbt run --select intermediate --full-refresh --profiles-dir .
```

### Phase 4: Add Incremental to Marts

**Objective**: Convert marts to incremental materialization

**Steps**:

1. **Update Marts Models**
   ```bash
   # Models already updated at:
   # - dbt_project/models/marts/account_summary.sql
   # - dbt_project/models/marts/customer_profile.sql
   ```

2. **Run Full Refresh First**
   ```bash
   cd dbt_project
   dbt run --select marts --full-refresh --profiles-dir .
   ```

3. **Test Incremental Logic**
   ```bash
   # Make a change upstream
   dbt snapshot --profiles-dir .
   dbt run --select intermediate --profiles-dir .
   
   # Run incremental marts
   dbt run --select marts --profiles-dir .
   ```

4. **Validate Calculations**
   ```bash
   # Run marts tests (including calculation accuracy tests)
   dbt test --select marts --profiles-dir .
   ```

**Rollback**:
```bash
# Run with full refresh
dbt run --select marts --full-refresh --profiles-dir .
```

### Phase 5: Implement Contracts

**Objective**: Enforce schema contracts at every layer

**Steps**:

1. **Review Contract Definitions**
   ```bash
   # Contracts defined in:
   # - dbt_project/models/source/_source.yml
   # - dbt_project/models/staging/_staging.yml
   # - dbt_project/snapshots/_snapshots.yml
   # - dbt_project/models/intermediate/_intermediate.yml
   # - dbt_project/models/marts/_marts.yml
   ```

2. **Enable Contracts Layer by Layer**
   ```bash
   # Start with source layer
   cd dbt_project
   dbt run --select source --profiles-dir .
   
   # Then staging
   dbt run --select staging --profiles-dir .
   
   # Then intermediate
   dbt run --select intermediate --profiles-dir .
   
   # Finally marts
   dbt run --select marts --profiles-dir .
   ```

3. **Fix Any Contract Violations**
   ```bash
   # If contracts fail, error message will show:
   # - Which column has the issue
   # - Expected vs actual data type
   # - Fix the model SQL to match contract
   ```

4. **Validate**
   ```bash
   # Run all models with contracts enforced
   dbt run --profiles-dir .
   ```

**Rollback**:
```bash
# Disable contracts in schema YAML files
# Set: enforced: false
# Or remove contract section entirely
```

### Phase 6: Standardize Naming

**Objective**: Apply consistent naming conventions

**Steps**:

1. **Review Naming Changes**
   ```
   Old Name                    → New Name
   ─────────────────────────────────────────────────
   stg_customers__cleaned      → stg_customer
   stg_accounts__cleaned       → stg_account
   int_accounts__with_customer → int_account_with_customer
   int_savings_accounts_only   → int_savings_account_only
   
   Column Changes:
   Name                        → customer_name
   HasLoan                     → has_loan_flag
   Balance                     → balance_amount
   AccountType                 → account_type
   ```

2. **Update Models**
   ```bash
   # All models already renamed and updated
   # Verify by checking:
   ls -la dbt_project/models/staging/
   ls -la dbt_project/models/intermediate/
   ```

3. **Run with New Names**
   ```bash
   cd dbt_project
   dbt run --full-refresh --profiles-dir .
   ```

4. **Update Downstream References**
   ```bash
   # Update Dagster output assets
   # Check: src/lc_pipeline/assets/outputs.py
   # Verify column names match new conventions
   ```

5. **Validate**
   ```bash
   # Run all tests
   dbt test --profiles-dir .
   
   # Run naming convention tests
   pytest tests/integration/test_naming.py -v
   ```

**Rollback**:
```bash
# Revert model names and column names
# Restore from backup
# Or keep old names as aliases during transition period
```

### Phase 7: Enhance Data Quality

**Objective**: Add comprehensive data quality tests

**Steps**:

1. **Review Custom Generic Tests**
   ```bash
   # Tests already created at:
   # - dbt_project/tests/generic/test_positive_value.sql
   # - dbt_project/tests/generic/test_valid_date_range.sql
   # - dbt_project/tests/generic/test_scd2_no_overlap.sql
   ```

2. **Add Tests to Models**
   ```bash
   # Tests already defined in schema YAML files
   # Review test coverage in each _*.yml file
   ```

3. **Run All Tests**
   ```bash
   cd dbt_project
   dbt test --profiles-dir .
   ```

4. **Configure Severity Levels**
   ```yaml
   # In schema YAML files, set severity:
   tests:
     - unique:
         severity: error  # Fails pipeline
     - dbt_utils.recency:
         severity: warn   # Logs warning only
   ```

5. **Set Up Quality Monitoring**
   ```bash
   # Quality reports generated automatically
   # Check: data/quality_reports/
   
   # View in Dagster UI
   dagster asset materialize --select quality_report -m src.lc_pipeline.definitions
   ```

6. **Validate**
   ```bash
   # Run data quality tests
   pytest tests/integration/test_data_quality.py -v
   ```

**Rollback**:
```bash
# Tests are non-blocking by default
# Can set all tests to severity: warn
# Or remove test definitions from YAML files
```

## Rollback Procedures

### Complete Rollback to Three-Layer Architecture

If you need to completely rollback to the original three-layer architecture:

1. **Restore Backup**
   ```bash
   # Restore database
   cp data/duckdb/lc.duckdb.backup data/duckdb/lc.duckdb
   
   # Restore outputs
   rm -rf data/outputs
   cp -r data/outputs.backup data/outputs
   ```

2. **Revert Code Changes**
   ```bash
   # If using git
   git checkout main  # or your original branch
   
   # Or manually revert files
   ```

3. **Drop New Tables**
   ```bash
   cd dbt_project
   
   # Drop source tables
   dbt run-operation drop_relation --args '{relation: src_customer}' --profiles-dir .
   dbt run-operation drop_relation --args '{relation: src_account}' --profiles-dir .
   
   # Drop snapshots
   dbt run-operation drop_relation --args '{relation: snap_customer}' --profiles-dir .
   dbt run-operation drop_relation --args '{relation: snap_account}' --profiles-dir .
   ```

4. **Run Original Pipeline**
   ```bash
   # Run with original models
   dbt run --profiles-dir .
   dbt test --profiles-dir .
   ```

### Partial Rollback (Phase-Specific)

Each phase can be rolled back independently using the rollback procedures listed in each phase section above.

## Troubleshooting

### Common Issues and Solutions

#### Issue 1: Snapshot Not Detecting Changes

**Symptoms**: Running `dbt snapshot` doesn't create new versions when data changes

**Solutions**:
```bash
# Check snapshot strategy
# For timestamp strategy: Ensure loaded_at column is updating
# For check_cols strategy: Verify columns are actually changing

# Force snapshot refresh
dbt snapshot --full-refresh --profiles-dir .

# Check snapshot configuration
cat dbt_project/snapshots/snap_customer.sql
```

#### Issue 2: Incremental Models Processing All Data

**Symptoms**: Incremental runs take as long as full refresh

**Solutions**:
```bash
# Check is_incremental() logic in model
# Verify unique_key is defined
# Check that upstream snapshots have dbt_valid_from timestamps

# Debug incremental logic
dbt run --select account_summary --profiles-dir . --debug

# Force full refresh once
dbt run --select account_summary --full-refresh --profiles-dir .
```

#### Issue 3: Contract Violations

**Symptoms**: Models fail with "Contract Error" messages

**Solutions**:
```bash
# Read error message carefully - it shows:
# - Which column has the issue
# - Expected data type
# - Actual data type

# Fix model SQL to cast to correct type
# Example: cast(customer_id as integer) as customer_id

# Or update contract definition if model is correct
```

#### Issue 4: Test Failures After Migration

**Symptoms**: Tests that passed before now fail

**Solutions**:
```bash
# Check if column names changed
# Update test references to use new names

# Check if data types changed
# Update test logic to handle new types

# Run specific test to debug
dbt test --select test_name --profiles-dir .

# View compiled SQL
cat dbt_project/target/compiled/lc_pipeline/tests/test_name.sql
```

#### Issue 5: Performance Degradation

**Symptoms**: Pipeline runs slower after migration

**Solutions**:
```bash
# Ensure incremental models are actually running incrementally
# Check: dbt run --select model_name --profiles-dir . --debug

# Verify indexes exist on snapshot tables
# Add indexes on dbt_valid_from, dbt_valid_to, and primary keys

# Check snapshot strategy
# Timestamp strategy is faster than check_cols

# Monitor query performance
# Use EXPLAIN ANALYZE on slow queries
```

#### Issue 6: Missing Data in Marts

**Symptoms**: Marts have fewer records than expected

**Solutions**:
```bash
# Check incremental logic
# Verify lookback window is sufficient for late data

# Check snapshot validity
# Ensure dbt_valid_to IS NULL filter is correct

# Run full refresh
dbt run --select marts --full-refresh --profiles-dir .

# Check upstream data
dbt run --select +account_summary --profiles-dir .
```

### Getting Help

If you encounter issues not covered here:

1. **Check Logs**
   ```bash
   # DBT logs
   cat dbt_project/logs/dbt.log
   
   # Dagster logs
   cat dagster_home/logs/event.log
   ```

2. **Run in Debug Mode**
   ```bash
   dbt run --select model_name --profiles-dir . --debug
   ```

3. **Review Documentation**
   - [Design Document](.kiro/specs/pipeline-enhancements/design.md)
   - [Data Quality Guide](DATA_QUALITY_GUIDE.md)
   - [DBT Documentation](https://docs.getdbt.com/)

4. **Contact Support**
   - Open an issue in the repository
   - Contact the data engineering team

## Validation

### Post-Migration Validation Checklist

After completing all phases, validate the migration:

- [ ] **All Layers Created**
  ```bash
  # Verify all 5 layers exist
  dbt ls --profiles-dir .
  # Should show: source, staging, snapshots, intermediate, marts
  ```

- [ ] **Snapshots Working**
  ```bash
  # Check SCD2 columns exist
  # Verify current records have dbt_valid_to = NULL
  # Verify historical records have dbt_valid_to != NULL
  ```

- [ ] **Incremental Processing**
  ```bash
  # Time a full refresh
  time dbt run --full-refresh --select account_summary --profiles-dir .
  
  # Time an incremental run
  time dbt run --select account_summary --profiles-dir .
  
  # Incremental should be significantly faster
  ```

- [ ] **Contracts Enforced**
  ```bash
  # All models should have contracts
  grep -r "enforced: true" dbt_project/models/
  ```

- [ ] **Naming Conventions**
  ```bash
  # Run naming tests
  pytest tests/integration/test_naming.py -v
  ```

- [ ] **Data Quality Tests**
  ```bash
  # All tests should pass
  dbt test --profiles-dir .
  
  # Should have 40+ tests
  dbt test --profiles-dir . | grep "PASS"
  ```

- [ ] **Quality Reports Generated**
  ```bash
  # Check reports exist
  ls -la data/quality_reports/
  
  # View latest report
  cat data/quality_reports/quality_report_*.json | jq .
  ```

- [ ] **End-to-End Pipeline**
  ```bash
  # Run complete pipeline
  dagster asset materialize --select '*' -m src.lc_pipeline.definitions
  
  # Verify all assets materialized successfully
  ```

- [ ] **Output Files Correct**
  ```bash
  # Check CSV output
  head data/outputs/account_summary.csv
  
  # Check Parquet output
  python -c "import pandas as pd; print(pd.read_parquet('data/outputs/account_summary.parquet').head())"
  ```

- [ ] **Documentation Updated**
  ```bash
  # Verify README reflects new architecture
  cat README.md | grep "Five-Layer"
  
  # Check migration guide exists
  cat docs/MIGRATION_GUIDE.md
  
  # Check data quality guide exists
  cat docs/DATA_QUALITY_GUIDE.md
  ```

### Performance Benchmarks

Record these metrics before and after migration:

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| Full refresh time | ___ min | ___ min | ___ |
| Incremental run time | N/A | ___ sec | ___ |
| Test execution time | ___ sec | ___ sec | ___ |
| Total pipeline time | ___ min | ___ min | ___ |
| Number of tests | 21 | 40+ | +90% |

### Success Criteria

Migration is successful when:

1. ✅ All 5 layers are operational
2. ✅ Snapshots capture changes correctly
3. ✅ Incremental runs are 10-100x faster
4. ✅ All 40+ tests pass
5. ✅ Contracts are enforced
6. ✅ Naming conventions are consistent
7. ✅ Quality reports are generated
8. ✅ Output data matches expected results
9. ✅ Documentation is complete
10. ✅ Team is trained on new architecture

## Next Steps

After successful migration:

1. **Monitor Performance**
   - Track incremental run times
   - Monitor snapshot storage growth
   - Optimize slow queries

2. **Expand Test Coverage**
   - Add more business rule tests
   - Implement custom generic tests
   - Set up automated alerting

3. **Enhance Documentation**
   - Document business logic
   - Create data dictionary
   - Generate DBT docs site

4. **Train Team**
   - Conduct training sessions
   - Share best practices
   - Document common patterns

5. **Plan Future Enhancements**
   - Add more data sources
   - Implement real-time processing
   - Expand to additional environments

## Conclusion

This migration transforms the pipeline from a basic ETL system into an enterprise-grade data platform with full historical tracking, incremental processing, and comprehensive data quality controls. Follow the phases sequentially, validate at each step, and use the rollback procedures if needed.

For questions or issues, refer to the troubleshooting section or contact the data engineering team.
