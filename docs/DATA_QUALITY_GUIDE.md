# Data Quality Guide

This guide provides comprehensive documentation for the data quality framework implemented in the LC Data Pipeline. It covers all data quality tests, severity levels, custom test creation, quality monitoring, and alerting mechanisms.

## Table of Contents

- [Overview](#overview)
- [Test Hierarchy](#test-hierarchy)
- [Built-in DBT Tests](#built-in-dbt-tests)
- [Custom Generic Tests](#custom-generic-tests)
- [Singular Tests](#singular-tests)
- [Test Severity Levels](#test-severity-levels)
- [Quality Monitoring](#quality-monitoring)
- [Creating Custom Tests](#creating-custom-tests)
- [Best Practices](#best-practices)
- [Troubleshooting](#troubleshooting)

## Overview

### Data Quality Philosophy

The pipeline implements a **quality-first** approach with tests at every layer:

1. **Prevention**: Catch issues early with schema contracts
2. **Detection**: Validate data at each transformation layer
3. **Monitoring**: Track quality metrics over time
4. **Alerting**: Notify team of critical failures

### Test Coverage

| Layer | Test Count | Test Types |
|-------|-----------|------------|
| Source | 6 | Schema validation, row count, not_null |
| Staging | 12 | Unique, not_null, accepted_values, positive_value |
| Snapshots | 8 | SCD2 integrity, freshness, current/historical |
| Intermediate | 6 | Referential integrity, relationships |
| Marts | 8 | Calculation accuracy, completeness, freshness |
| **Total** | **40+** | **Multiple types across all layers** |

### Running Tests

```bash
# Run all tests
cd dbt_project
dbt test --profiles-dir .

# Run tests for specific layer
dbt test --select source --profiles-dir .
dbt test --select staging --profiles-dir .
dbt test --select snapshots --profiles-dir .
dbt test --select intermediate --profiles-dir .
dbt test --select marts --profiles-dir .

# Run specific test
dbt test --select test_name --profiles-dir .

# Run tests with specific tag
dbt test --select tag:critical --profiles-dir .
```

## Test Hierarchy

### Level 1: Source Layer Tests

**Purpose**: Validate raw data integrity

**Test Types**:
- Schema validation (expected columns present)
- Row count > 0 (data was loaded)
- Not null on key columns
- Data type validation (via contracts)

**Example**:
```yaml
# dbt_project/models/source/_source.yml
models:
  - name: src_customer
    tests:
      - dbt_utils.expression_is_true:
          expression: "count(*) > 0"
          config:
            severity: error
    columns:
      - name: customer_id
        tests:
          - not_null
          - unique
      - name: loaded_at
        tests:
          - not_null
```

### Level 2: Staging Layer Tests

**Purpose**: Validate cleaned and standardized data

**Test Types**:
- Unique constraints on primary keys
- Not null on required fields
- Accepted values for categorical fields
- Positive values for amounts
- Data type validation (via contracts)

**Example**:
```yaml
# dbt_project/models/staging/_staging.yml
models:
  - name: stg_customer
    columns:
      - name: customer_id
        tests:
          - unique
          - not_null
      - name: customer_name
        tests:
          - not_null
      - name: has_loan_flag
        tests:
          - not_null
          - accepted_values:
              values: [true, false]
```

### Level 3: Snapshot Layer Tests

**Purpose**: Validate SCD2 historical tracking

**Test Types**:
- SCD2 integrity (no overlapping validity periods)
- Current records have null dbt_valid_to
- Historical records have non-null dbt_valid_to
- Freshness checks

**Example**:
```yaml
# dbt_project/snapshots/_snapshots.yml
snapshots:
  - name: snap_customer
    tests:
      - test_scd2_no_overlap:
          unique_key: customer_id
          valid_from: dbt_valid_from
          valid_to: dbt_valid_to
      - dbt_utils.recency:
          datepart: day
          field: dbt_updated_at
          interval: 1
          config:
            severity: warn
```

### Level 4: Intermediate Layer Tests

**Purpose**: Validate business logic and relationships

**Test Types**:
- Referential integrity (foreign keys exist)
- Relationship tests between models
- Business rule validation
- Join completeness

**Example**:
```yaml
# dbt_project/models/intermediate/_intermediate.yml
models:
  - name: int_account_with_customer
    columns:
      - name: customer_id
        tests:
          - relationships:
              to: ref('snap_customer')
              field: customer_id
              where: "dbt_valid_to is null"
      - name: balance_amount
        tests:
          - positive_value
```

### Level 5: Marts Layer Tests

**Purpose**: Validate final analytical outputs

**Test Types**:
- Calculation accuracy
- Completeness (all expected records present)
- Freshness (data is recent)
- Business metric validation

**Example**:
```yaml
# dbt_project/models/marts/_marts.yml
models:
  - name: account_summary
    tests:
      - dbt_utils.expression_is_true:
          expression: "new_balance_amount = original_balance_amount + annual_interest_amount"
          config:
            severity: error
    columns:
      - name: interest_rate_pct
        tests:
          - dbt_utils.accepted_range:
              min_value: 0
              max_value: 10
```

## Built-in DBT Tests

### Unique Test

Validates that all values in a column are unique.

**Usage**:
```yaml
columns:
  - name: customer_id
    tests:
      - unique
```

**When to Use**:
- Primary key columns
- Unique identifiers
- Columns that should have no duplicates

### Not Null Test

Validates that a column contains no null values.

**Usage**:
```yaml
columns:
  - name: customer_name
    tests:
      - not_null
```

**When to Use**:
- Required fields
- Primary keys
- Foreign keys
- Critical business fields

### Accepted Values Test

Validates that column values are within a specified set.

**Usage**:
```yaml
columns:
  - name: account_type
    tests:
      - accepted_values:
          values: ['Checking', 'Savings']
```

**When to Use**:
- Categorical fields
- Status columns
- Type columns
- Enum-like fields

### Relationships Test

Validates referential integrity between tables.

**Usage**:
```yaml
columns:
  - name: customer_id
    tests:
      - relationships:
          to: ref('stg_customer')
          field: customer_id
```

**When to Use**:
- Foreign key columns
- Join columns
- Reference fields

## Custom Generic Tests

### Positive Value Test

Validates that numeric values are positive (> 0).

**Implementation**:
```sql
-- dbt_project/tests/generic/test_positive_value.sql
{% test positive_value(model, column_name) %}

select *
from {{ model }}
where {{ column_name }} <= 0
   or {{ column_name }} is null

{% endtest %}
```

**Usage**:
```yaml
columns:
  - name: balance_amount
    tests:
      - positive_value
```

**When to Use**:
- Balance amounts
- Quantities
- Counts
- Prices

### Valid Date Range Test

Validates that dates fall within an expected range.

**Implementation**:
```sql
-- dbt_project/tests/generic/test_valid_date_range.sql
{% test valid_date_range(model, column_name, min_date=None, max_date=None) %}

select *
from {{ model }}
where 1=1
  {% if min_date %}
    and {{ column_name }} < '{{ min_date }}'
  {% endif %}
  {% if max_date %}
    and {{ column_name }} > '{{ max_date }}'
  {% endif %}

{% endtest %}
```

**Usage**:
```yaml
columns:
  - name: loaded_at
    tests:
      - valid_date_range:
          min_date: '2020-01-01'
          max_date: '2030-12-31'
```

**When to Use**:
- Date columns
- Timestamp columns
- Validity periods

### SCD2 No Overlap Test

Validates that SCD2 validity periods don't overlap for the same entity.

**Implementation**:
```sql
-- dbt_project/tests/generic/test_scd2_no_overlap.sql
{% test test_scd2_no_overlap(model, unique_key, valid_from, valid_to) %}

with overlaps as (
    select
        a.{{ unique_key }},
        a.{{ valid_from }} as a_valid_from,
        a.{{ valid_to }} as a_valid_to,
        b.{{ valid_from }} as b_valid_from,
        b.{{ valid_to }} as b_valid_to
    from {{ model }} a
    join {{ model }} b
        on a.{{ unique_key }} = b.{{ unique_key }}
        and a.dbt_scd_id != b.dbt_scd_id
    where
        -- Check for overlapping periods
        a.{{ valid_from }} < coalesce(b.{{ valid_to }}, '9999-12-31')
        and coalesce(a.{{ valid_to }}, '9999-12-31') > b.{{ valid_from }}
)

select * from overlaps

{% endtest %}
```

**Usage**:
```yaml
snapshots:
  - name: snap_customer
    tests:
      - test_scd2_no_overlap:
          unique_key: customer_id
          valid_from: dbt_valid_from
          valid_to: dbt_valid_to
```

**When to Use**:
- All snapshot models
- SCD2 tables
- Temporal data with validity periods

## Singular Tests

Singular tests are specific SQL queries that validate business logic.

### Interest Calculation Test

Validates that interest calculations are correct.

**Implementation**:
```sql
-- dbt_project/tests/test_interest_calculation.sql
with validation as (
    select
        account_id,
        original_balance_amount,
        interest_rate_pct,
        annual_interest_amount,
        new_balance_amount,
        -- Calculate expected interest
        original_balance_amount * (interest_rate_pct / 100.0) as expected_interest,
        -- Calculate expected new balance
        original_balance_amount + (original_balance_amount * (interest_rate_pct / 100.0)) as expected_new_balance
    from {{ ref('account_summary') }}
)

select *
from validation
where
    -- Check interest calculation (with small tolerance for rounding)
    abs(annual_interest_amount - expected_interest) > 0.01
    or abs(new_balance_amount - expected_new_balance) > 0.01
```

**When to Use**:
- Complex calculations
- Business-specific logic
- Multi-column validations

### SCD2 Current Records Test

Validates that current snapshot records have null dbt_valid_to.

**Implementation**:
```sql
-- dbt_project/tests/test_snap_customer_current_records.sql
select *
from {{ ref('snap_customer') }}
where dbt_valid_to is not null
  and dbt_scd_id in (
      -- Get the latest version for each customer
      select max(dbt_scd_id)
      from {{ ref('snap_customer') }}
      group by customer_id
  )
```

**When to Use**:
- Snapshot validation
- SCD2 integrity checks
- Temporal data validation

### SCD2 Historical Records Test

Validates that historical snapshot records have non-null dbt_valid_to.

**Implementation**:
```sql
-- dbt_project/tests/test_snap_customer_historical_records.sql
select *
from {{ ref('snap_customer') }}
where dbt_valid_to is null
  and dbt_scd_id not in (
      -- Get the latest version for each customer
      select max(dbt_scd_id)
      from {{ ref('snap_customer') }}
      group by customer_id
  )
```

## Test Severity Levels

### Error Severity

Tests with `severity: error` will **fail the pipeline** if they don't pass.

**Usage**:
```yaml
tests:
  - unique:
      config:
        severity: error
```

**When to Use**:
- Critical data quality issues
- Schema violations
- Referential integrity failures
- Calculation errors

**Examples**:
- Primary key uniqueness
- Not null on required fields
- Referential integrity
- Calculation accuracy

### Warn Severity

Tests with `severity: warn` will **log a warning** but allow the pipeline to continue.

**Usage**:
```yaml
tests:
  - dbt_utils.recency:
      datepart: day
      field: loaded_at
      interval: 1
      config:
        severity: warn
```

**When to Use**:
- Non-critical issues
- Freshness checks
- Data quality monitoring
- Informational validations

**Examples**:
- Data freshness
- Optional field completeness
- Performance metrics
- Trend monitoring

### Configuring Severity

**In Schema YAML**:
```yaml
columns:
  - name: customer_id
    tests:
      - unique:
          config:
            severity: error
      - not_null:
          config:
            severity: error
```

**In dbt_project.yml**:
```yaml
tests:
  lc_pipeline:
    +severity: error  # Default for all tests
    staging:
      +severity: error  # Critical layer
    marts:
      +severity: warn   # Allow warnings in marts
```

### Error Thresholds

Configure tests to fail only when errors exceed a threshold:

```yaml
tests:
  - unique:
      config:
        error_if: ">10"    # Fail if more than 10 duplicates
        warn_if: ">0"      # Warn if any duplicates
```

## Quality Monitoring

### Quality Report Generation

Quality reports are automatically generated after each pipeline run.

**Report Location**: `data/quality_reports/quality_report_TIMESTAMP.json`

**Report Structure**:
```json
{
  "timestamp": "2024-01-15T10:30:00Z",
  "total_tests": 42,
  "passed": 40,
  "failed": 2,
  "warned": 0,
  "by_layer": {
    "source": {"passed": 6, "failed": 0},
    "staging": {"passed": 12, "failed": 0},
    "snapshots": {"passed": 8, "failed": 0},
    "intermediate": {"passed": 6, "failed": 0},
    "marts": {"passed": 8, "failed": 2}
  },
  "failures": [
    {
      "test_name": "unique_account_summary_account_id",
      "model": "account_summary",
      "column": "account_id",
      "failure_count": 3,
      "message": "Found 3 duplicate account_id values"
    }
  ]
}
```

### Viewing Quality Reports

**Command Line**:
```bash
# View latest report
cat data/quality_reports/quality_report_*.json | jq .

# View failures only
cat data/quality_reports/quality_report_*.json | jq '.failures'

# View by layer
cat data/quality_reports/quality_report_*.json | jq '.by_layer'
```

**Dagster UI**:
```bash
# Materialize quality report asset
dagster asset materialize --select quality_report -m src.lc_pipeline.definitions

# View in UI at http://localhost:3000
```

**Python**:
```python
import json
from pathlib import Path

# Load latest report
reports_dir = Path('data/quality_reports')
latest_report = max(reports_dir.glob('quality_report_*.json'))

with open(latest_report) as f:
    report = json.load(f)

print(f"Total tests: {report['total_tests']}")
print(f"Passed: {report['passed']}")
print(f"Failed: {report['failed']}")

if report['failures']:
    print("\nFailures:")
    for failure in report['failures']:
        print(f"  - {failure['test_name']}: {failure['message']}")
```

### Quality Metrics Tracking

Track quality metrics over time:

```python
# src/lc_pipeline/resources/data_quality.py
class DataQualityMonitor:
    def generate_report(self, test_results):
        """Generate data quality report from DBT test results"""
        report = {
            'timestamp': datetime.now().isoformat(),
            'total_tests': len(test_results),
            'passed': sum(1 for t in test_results if t.status == 'pass'),
            'failed': sum(1 for t in test_results if t.status == 'fail'),
            'warned': sum(1 for t in test_results if t.status == 'warn'),
            'by_layer': self._group_by_layer(test_results),
            'failures': [
                {
                    'test_name': t.name,
                    'model': t.model,
                    'column': t.column,
                    'failure_count': t.failure_count,
                    'message': t.message
                }
                for t in test_results if t.status == 'fail'
            ]
        }
        return report
    
    def _group_by_layer(self, test_results):
        """Group test results by layer"""
        layers = ['source', 'staging', 'snapshots', 'intermediate', 'marts']
        by_layer = {}
        
        for layer in layers:
            layer_tests = [t for t in test_results if layer in t.model]
            by_layer[layer] = {
                'passed': sum(1 for t in layer_tests if t.status == 'pass'),
                'failed': sum(1 for t in layer_tests if t.status == 'fail'),
                'warned': sum(1 for t in layer_tests if t.status == 'warn')
            }
        
        return by_layer
```

### Alerting

Configure alerts for critical failures:

**Slack Alerting** (example):
```python
def send_slack_alert(report):
    """Send Slack alert for test failures"""
    if report['failed'] > 0:
        message = f"""
        ❌ Data Quality Alert
        
        Total Tests: {report['total_tests']}
        Failed: {report['failed']}
        Passed: {report['passed']}
        
        Failures:
        {chr(10).join(f"  - {f['test_name']}: {f['message']}" for f in report['failures'])}
        """
        
        # Send to Slack
        slack_webhook_url = os.getenv('SLACK_WEBHOOK_URL')
        requests.post(slack_webhook_url, json={'text': message})
```

**Email Alerting** (example):
```python
def send_email_alert(report):
    """Send email alert for test failures"""
    if report['failed'] > 0:
        subject = f"Data Quality Alert: {report['failed']} tests failed"
        body = f"""
        Data quality tests have failed in the pipeline.
        
        Summary:
        - Total Tests: {report['total_tests']}
        - Passed: {report['passed']}
        - Failed: {report['failed']}
        
        Please review the failures and take corrective action.
        """
        
        # Send email
        send_email(to=ALERT_EMAIL, subject=subject, body=body)
```

## Creating Custom Tests

### Creating a Custom Generic Test

**Step 1: Create Test File**

Create a new file in `dbt_project/tests/generic/`:

```sql
-- dbt_project/tests/generic/test_custom_validation.sql
{% test custom_validation(model, column_name, threshold=100) %}

select *
from {{ model }}
where {{ column_name }} > {{ threshold }}

{% endtest %}
```

**Step 2: Use in Schema YAML**

```yaml
columns:
  - name: balance_amount
    tests:
      - custom_validation:
          threshold: 1000000
```

**Step 3: Test the Test**

```bash
cd dbt_project
dbt test --select test_custom_validation --profiles-dir .
```

### Creating a Singular Test

**Step 1: Create Test File**

Create a new file in `dbt_project/tests/`:

```sql
-- dbt_project/tests/test_custom_business_rule.sql
-- Validate that savings accounts have higher balances than checking
with account_averages as (
    select
        account_type,
        avg(balance_amount) as avg_balance
    from {{ ref('stg_account') }}
    group by account_type
)

select *
from account_averages
where account_type = 'Savings'
  and avg_balance < (
      select avg_balance
      from account_averages
      where account_type = 'Checking'
  )
```

**Step 2: Run the Test**

```bash
cd dbt_project
dbt test --select test_custom_business_rule --profiles-dir .
```

### Test Development Best Practices

1. **Start Simple**: Begin with basic validation, add complexity as needed
2. **Test the Test**: Verify test catches actual issues
3. **Document**: Add comments explaining what the test validates
4. **Performance**: Avoid expensive operations in tests
5. **Reusability**: Create generic tests for common patterns

## Best Practices

### Test Coverage Guidelines

**Minimum Coverage**:
- All primary keys: `unique` and `not_null`
- All foreign keys: `not_null` and `relationships`
- All required fields: `not_null`
- All categorical fields: `accepted_values`
- All amount fields: `positive_value`

**Recommended Coverage**:
- Freshness checks on time-sensitive data
- Calculation validation for derived fields
- Referential integrity across all joins
- Business rule validation
- SCD2 integrity for snapshots

### Test Organization

**By Layer**:
```
tests/
├── source/           # Source layer tests
├── staging/          # Staging layer tests
├── snapshots/        # Snapshot layer tests
├── intermediate/     # Intermediate layer tests
└── marts/           # Marts layer tests
```

**By Type**:
```
tests/
├── generic/          # Reusable generic tests
├── singular/         # One-off singular tests
└── integration/      # Cross-model tests
```

### Test Naming Conventions

- Generic tests: `test_{validation_type}.sql`
- Singular tests: `test_{model}_{validation}.sql`
- Clear, descriptive names
- Consistent prefixes

### Performance Optimization

**Optimize Test Queries**:
```sql
-- Bad: Full table scan
select * from {{ model }}
where expensive_calculation(column) > 100

-- Good: Use indexes and filters
select * from {{ model }}
where column > 100  -- Simple filter first
  and expensive_calculation(column) > 100
```

**Limit Test Scope**:
```yaml
tests:
  - unique:
      config:
        limit: 100  # Only check first 100 rows in dev
```

**Use Sampling in Development**:
```yaml
tests:
  - custom_test:
      config:
        where: "random() < 0.1"  # Sample 10% in dev
```

## Troubleshooting

### Test Failures

**Step 1: Identify the Failure**
```bash
# Run tests and capture output
dbt test --profiles-dir . > test_results.txt 2>&1

# View failures
grep "FAIL" test_results.txt
```

**Step 2: View Compiled SQL**
```bash
# Find compiled test SQL
cat dbt_project/target/compiled/lc_pipeline/tests/test_name.sql

# Run manually to debug
duckdb data/duckdb/lc.duckdb < dbt_project/target/compiled/lc_pipeline/tests/test_name.sql
```

**Step 3: Analyze Results**
```sql
-- Add LIMIT to see sample failures
select * from (
    -- compiled test SQL here
) limit 10;
```

**Step 4: Fix Root Cause**
- Update model logic
- Fix data issues
- Adjust test threshold
- Update test logic

### Common Issues

**Issue: Test Passes Locally, Fails in Production**

**Solution**:
- Check for environment-specific data
- Verify data volumes (tests may timeout)
- Check for timing issues (freshness tests)
- Review production-specific configurations

**Issue: Test is Too Slow**

**Solution**:
- Add indexes on tested columns
- Use sampling in development
- Optimize test query
- Consider moving to warn severity

**Issue: False Positives**

**Solution**:
- Review test logic
- Add appropriate thresholds
- Use warn severity for informational tests
- Add context-specific filters

**Issue: Test Flakiness**

**Solution**:
- Add lookback windows for timing issues
- Use appropriate severity levels
- Add retry logic for transient failures
- Review test assumptions

## Conclusion

The data quality framework provides comprehensive validation at every layer of the pipeline. By following the guidelines in this document, you can:

- Ensure data integrity throughout the pipeline
- Catch issues early before they propagate
- Monitor quality metrics over time
- Create custom tests for business-specific validations
- Maintain high confidence in data quality

For additional support:
- Review the [Design Document](.kiro/specs/pipeline-enhancements/design.md)
- Check the [Migration Guide](MIGRATION_GUIDE.md)
- Consult [DBT Testing Documentation](https://docs.getdbt.com/docs/building-a-dbt-project/tests)
- Contact the data engineering team

Remember: **Quality is not an afterthought—it's built into every layer of the pipeline.**
