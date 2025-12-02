# Asset Lineage and Metadata

This document describes the asset lineage, metadata configuration, and governance policies for the LendingClub data pipeline.

## Overview

The pipeline uses Dagster's asset-centric approach to manage data transformations. Each asset represents a data artifact (table, file, etc.) with:

- **Clear ownership** - Every asset has designated owners responsible for its quality
- **Rich metadata** - Descriptive information about purpose, schema, consumers, etc.
- **Freshness policies** - SLAs for how fresh data should be
- **Logical grouping** - Assets organized by layer (ingestion, staging, intermediate, marts, outputs)
- **Automatic lineage tracking** - Dependencies tracked automatically via DBT refs and Dagster inputs

## Asset Groups

Assets are organized into logical groups that correspond to the data pipeline layers:

### 1. Ingestion Group

**Purpose**: Read and validate raw data from source CSV files

**Assets**:
- `customers_raw` - Customer master data (ID, name, loan status)
- `accounts_raw` - Account transaction data (ID, customer ID, balance, type)

**Characteristics**:
- Source: CSV files in `data/inputs/`
- Validation: Empty file checks, missing column checks
- Freshness: 24 hours
- Owners: data-engineering-team@company.com

### 2. Staging Group

**Purpose**: Clean and normalize raw data

**Assets**:
- `staging/stg_customers__cleaned` - Cleaned customer data
- `staging/stg_accounts__cleaned` - Cleaned account data

**Characteristics**:
- Materialization: Views (no storage overhead)
- Transformations: Trim whitespace, type casting, standardization
- Freshness: 24 hours
- Owners: data-engineering-team@company.com

### 3. Intermediate Group

**Purpose**: Apply business logic and create reusable components

**Assets**:
- `intermediate/int_accounts__with_customer` - Accounts joined with customer info
- `intermediate/int_savings_accounts_only` - Filtered to savings accounts only

**Characteristics**:
- Materialization: Ephemeral (computed on-the-fly)
- Transformations: Joins, filters, business rules
- Freshness: 25 hours
- Owners: data-engineering-team@company.com

### 4. Marts Group

**Purpose**: Create business-ready analytical outputs

**Assets**:
- `marts/account_summary` - Final account summary with interest calculations

**Characteristics**:
- Materialization: Table (persistent for query performance)
- Transformations: Interest rate calculation, aggregations
- Freshness: 26 hours
- Owners: analytics-team@company.com, data-engineering-team@company.com

### 5. Outputs Group

**Purpose**: Export data to various formats and destinations

**Assets**:
- `account_summary_csv` - CSV export for BI tools
- `account_summary_parquet` - Parquet export for data science
- `account_summary_to_databricks` - Delta table for enterprise analytics (production only)

**Characteristics**:
- Destinations: Local files, Databricks
- Formats: CSV, Parquet, Delta
- Freshness: Not applicable (derived from marts)
- Owners: analytics-team@company.com

## Asset Lineage

The pipeline follows a clear data flow from ingestion to outputs:

```
┌─────────────────┐
│  customers_raw  │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────┐
│ stg_customers__cleaned      │
└────────┬────────────────────┘
         │
         │         ┌─────────────────┐
         │         │  accounts_raw   │
         │         └────────┬────────┘
         │                  │
         │                  ▼
         │         ┌─────────────────────────┐
         │         │ stg_accounts__cleaned   │
         │         └────────┬────────────────┘
         │                  │
         └──────────────────┴──────────────────┐
                                                │
                                                ▼
                                ┌───────────────────────────────────┐
                                │ int_accounts__with_customer       │
                                └───────────────┬───────────────────┘
                                                │
                                                ▼
                                ┌───────────────────────────────────┐
                                │ int_savings_accounts_only         │
                                └───────────────┬───────────────────┘
                                                │
                                                ▼
                                ┌───────────────────────────────────┐
                                │ account_summary                   │
                                └───────────────┬───────────────────┘
                                                │
                        ┌───────────────────────┼───────────────────────┐
                        │                       │                       │
                        ▼                       ▼                       ▼
            ┌───────────────────┐   ┌───────────────────┐   ┌──────────────────────────┐
            │ account_summary_  │   │ account_summary_  │   │ account_summary_to_      │
            │ csv               │   │ parquet           │   │ databricks               │
            └───────────────────┘   └───────────────────┘   └──────────────────────────┘
```

## Metadata Configuration

Each asset includes comprehensive metadata for governance and observability:

### Required Metadata

All assets must have:

1. **Description** - Clear explanation of what the asset represents
2. **Owners** - Email addresses of responsible teams/individuals
3. **Tags** - Key-value pairs for categorization (layer, domain, sla, priority)
4. **Group** - Logical grouping (ingestion, staging, intermediate, marts, outputs)

### Optional Metadata

Assets may include:

1. **Freshness SLA** - Expected data freshness documented in metadata
2. **Custom Metadata** - Additional context-specific information

### Metadata Fields by Asset Type

#### Ingestion Assets

```python
{
    "schema": "raw",
    "owner": "data-engineering-team",
    "source_system": "lending_club_csv",
    "data_classification": "internal",
    "refresh_frequency": "daily",
    "expected_lag_hours": 24,
    "business_purpose": "...",
    "data_quality_checks": "...",
    "downstream_consumers": "...",
    "freshness_sla": "24 hours - Expected to refresh daily at 2 AM",
}
```

#### DBT Transformation Assets

```python
{
    "layer": "staging|intermediate|marts",
    "purpose": "...",
    "transformation_type": "...",
    "materialization": "view|ephemeral|table",
    "materialization_rationale": "...",
    "schema": "...",
    "data_classification": "internal",
    "refresh_frequency": "daily",
    "expected_lag_hours": 24.5,
    "business_domain": "...",
    "dbt_model_name": "...",
    "dbt_file_path": "...",
    "freshness_sla": "24-26 hours depending on layer - Expected to refresh daily at 2 AM",
}
```

#### Output Assets

```python
{
    "owner": "analytics-team",
    "format": "csv|parquet|delta",
    "destination": "local|databricks",
    "data_classification": "internal",
    "consumers": ["..."],
    "expected_lag_hours": 24.5,
    "business_purpose": "...",
    "upstream_dependencies": "...",
    "output_schema": "...",
}
```

## Freshness SLAs

Freshness SLAs define expectations for how fresh data should be. The pipeline uses cascading freshness SLAs documented in asset metadata:

| Layer        | Maximum Lag | Expected Schedule | Rationale                                    |
|--------------|-------------|-------------------|----------------------------------------------|
| Ingestion    | 24 hours    | 0 2 * * *         | Source data refreshed daily at 2 AM          |
| Staging      | 24 hours    | 0 2 * * *         | Depends on ingestion, runs immediately after |
| Intermediate | 25 hours    | 0 2 * * *         | Depends on staging, small buffer for delays  |
| Marts        | 26 hours    | 0 2 * * *         | Depends on intermediate, final buffer        |

**Note**: Output assets don't have freshness SLAs since they're derived from marts and execute immediately after.

**Implementation**: Freshness SLAs are documented in the `freshness_sla` metadata field for each asset. This provides visibility into expectations without enforcing automated checks (which can be added later if needed).

## Ownership Model

### Data Engineering Team

**Responsibilities**:
- Ingestion layer (raw data validation)
- Staging layer (data cleaning)
- Intermediate layer (business logic)
- Infrastructure and pipeline reliability

**Contact**: data-engineering-team@company.com

### Analytics Team

**Responsibilities**:
- Marts layer (business-ready outputs)
- Output layer (export to various formats)
- Business logic validation
- Consumer support

**Contact**: analytics-team@company.com

### Shared Ownership

Some assets have shared ownership:
- `marts/account_summary` - Both teams (analytics defines logic, engineering maintains)
- `account_summary_to_databricks` - Both teams (engineering for reliability, analytics for consumers)

## Tags and Classification

### Standard Tags

All assets use consistent tags for filtering and organization:

| Tag Key    | Possible Values                          | Purpose                          |
|------------|------------------------------------------|----------------------------------|
| layer      | raw, staging, intermediate, marts, output| Pipeline layer                   |
| domain     | customer, account, analytics             | Business domain                  |
| sla        | daily, hourly, weekly                    | Refresh frequency                |
| priority   | high, medium, low                        | Business criticality             |
| source     | csv, database, api                       | Data source type                 |
| format     | csv, parquet, delta                      | Output format                    |
| destination| local, databricks, s3                    | Output destination               |
| environment| development, staging, production         | Execution environment            |

### Tag Usage Examples

**Find all high-priority assets**:
```python
AssetSelection.tag("priority", "high")
```

**Find all staging layer assets**:
```python
AssetSelection.tag("layer", "staging")
```

**Find all customer domain assets**:
```python
AssetSelection.tag("domain", "customer")
```

## Viewing Lineage in Dagster UI

### Accessing the Lineage Graph

1. Start Dagster UI: `dagster dev` or access deployed instance
2. Navigate to **Assets** tab
3. Click on any asset to see its lineage
4. Use the **Lineage** tab to see upstream and downstream dependencies

### Lineage Features

- **Upstream Dependencies**: Assets that this asset depends on
- **Downstream Dependencies**: Assets that depend on this asset
- **Materialization History**: When the asset was last materialized
- **Metadata**: All configured metadata visible in the UI
- **Asset Checks**: Data quality checks and their results

### Filtering Assets

Use the asset catalog filters:

- **By Group**: Filter by ingestion, staging, intermediate, marts, outputs
- **By Tag**: Filter by any tag (layer, domain, priority, etc.)
- **By Owner**: Filter by owner email
- **By Freshness**: See which assets are stale

## Validation

### Automated Validation

Run the validation script to check asset metadata:

```bash
python scripts/validate_asset_metadata.py
```

This script validates:
- All assets have descriptions
- All assets have owners
- All assets have tags
- All assets have metadata
- All assets have groups
- Freshness policies are set where appropriate

### Manual Validation

Check the Dagster UI:

1. Navigate to **Assets** tab
2. Click on each asset
3. Verify metadata is displayed correctly
4. Check lineage graph shows correct dependencies
5. Verify freshness policies are active

## Best Practices

### Adding New Assets

When adding new assets:

1. **Set a clear description** - Explain what the asset represents and its purpose
2. **Assign owners** - Use team email addresses
3. **Add comprehensive tags** - Include layer, domain, sla, priority
4. **Configure metadata** - Add business context, consumers, schema info
5. **Set freshness policy** - Define SLA for data freshness (if applicable)
6. **Assign to a group** - Place in appropriate layer group

### Updating Metadata

When updating metadata:

1. Update the asset decorator in the code
2. Run validation script to verify changes
3. Deploy to Dagster
4. Verify in UI that metadata displays correctly
5. Update documentation if needed

### Monitoring Freshness

Monitor asset freshness:

1. Review asset metadata for freshness SLA expectations
2. Check asset materialization timestamps in Dagster UI
3. Compare last materialization time against SLA
4. Set up custom alerts for SLA violations if needed
5. Review freshness SLAs quarterly
6. Adjust SLAs based on business needs

## Troubleshooting

### Asset Not Showing in UI

**Possible causes**:
- Asset not imported in `definitions.py`
- Syntax error in asset definition
- Dagster daemon not running

**Solution**:
1. Check `definitions.py` imports
2. Run `dagster asset list` to see all assets
3. Check logs for errors

### Lineage Not Displaying Correctly

**Possible causes**:
- DBT refs not used correctly
- Asset dependencies not declared
- Manifest not up to date

**Solution**:
1. Verify DBT models use `{{ ref('model_name') }}`
2. Check asset `ins` parameter
3. Run `dbt compile` to regenerate manifest
4. Restart Dagster

### Freshness SLA Violations

**Possible causes**:
- Asset not materialized on schedule
- Upstream dependencies delayed
- Pipeline execution failures

**Solution**:
1. Check asset materialization history in Dagster UI
2. Review execution logs for errors
3. Check upstream asset status
4. Manually materialize asset to catch up
5. Investigate root cause of delay

## References

- [Dagster Asset Documentation](https://docs.dagster.io/concepts/assets/software-defined-assets)
- [Dagster Metadata Documentation](https://docs.dagster.io/concepts/metadata-tags/asset-metadata)
- [Dagster Freshness Policies](https://docs.dagster.io/concepts/assets/asset-checks/freshness-checks)
- [DBT Asset Integration](https://docs.dagster.io/integrations/dbt)
