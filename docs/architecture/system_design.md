# System Design

## Overview

The LendingClub Data Pipeline is a production-grade data processing system built with modern data engineering best practices. The system demonstrates a complete end-to-end data pipeline that ingests raw CSV files, applies multi-layer transformations, and outputs enriched analytical data in multiple formats.

## Core Design Principles

### 1. Build Once, Deploy Anywhere

The architecture uses environment-driven configuration to run identically on local DuckDB (development) or Databricks (production) with zero code changes. This principle ensures:

- Consistent behavior across environments
- Simplified testing and debugging
- Reduced deployment risk
- Lower maintenance overhead

### 2. Asset-Centric Architecture

Using Dagster's asset-centric model, we focus on data products rather than tasks. Each asset represents a materialized data artifact with:

- Clear lineage and dependencies
- Built-in metadata tracking
- Automatic dependency resolution
- Visual representation in UI

### 3. Layered Transformation Architecture

The five-layer architecture (source → staging → snapshots → intermediate → marts) provides:

- Clear separation of concerns
- Reusable intermediate components
- Quality gates at each layer
- Easy debugging and maintenance

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                  DAGSTER ORCHESTRATOR                       │
│              (Asset Management & Scheduling)                │
└────────────┬────────────────────────────────────────────────┘
             │
    ┌────────┴────────┐
    │                 │
┌───▼────────┐   ┌────▼──────────┐
│  Ingestion │   │  DBT Transform│
│   Assets   │   │    Assets     │
└───┬────────┘   └────┬──────────┘
    │                 │
    │  ┌──────────────┴──────────────┐
    │  │                             │
    │  │  ┌─────────────────────┐   │
    │  │  │  Staging Layer      │   │
    │  │  │  • stg_customers    │   │
    │  │  │  • stg_accounts     │   │
    │  │  └──────────┬──────────┘   │
    │  │             │               │
    │  │  ┌──────────▼──────────┐   │
    │  │  │  Intermediate Layer │   │
    │  │  │  • int_accounts_    │   │
    │  │  │    with_customer    │   │
    │  │  │  • int_savings_only │   │
    │  │  └──────────┬──────────┘   │
    │  │             │               │
    │  │  ┌──────────▼──────────┐   │
    │  │  │  Marts Layer        │   │
    │  │  │  • account_summary  │   │
    │  │  └──────────┬──────────┘   │
    │  └─────────────┘               │
    │                                │
┌───▼────────────────────────────────▼───┐
│         Output Layer                   │
│  • CSV Export (local)                  │
│  • Parquet Export (local)              │
│  • Databricks Delta Table (prod)      │
└────────────────────────────────────────┘
```

## Technology Stack

### Core Technologies

- **Dagster**: Modern data orchestration platform with asset-centric design
- **DBT**: SQL-based transformation framework with built-in testing
- **DuckDB**: In-process OLAP database for local development
- **Databricks**: Cloud data platform for production workloads
- **Docker Compose**: Containerized local development environment

### Supporting Technologies

- **Python 3.9+**: Primary programming language
- **Pandas**: Data manipulation and CSV/Parquet I/O
- **PostgreSQL**: Dagster metadata storage
- **Pytest**: Testing framework

## Component Architecture

### 1. Ingestion Layer

**Purpose**: Read and validate raw CSV files

**Components**:
- `customers_raw` asset: Ingests Customer.csv
- `accounts_raw` asset: Ingests accounts.csv

**Responsibilities**:
- File existence validation
- Schema validation (required columns)
- Empty file detection
- Metadata collection (row counts, timestamps)

### 2. Transformation Layer (DBT)

**Purpose**: Clean, join, and enrich data through five layers with SCD2 historical tracking

#### Staging Layer
- **Materialization**: Views (no storage overhead)
- **Purpose**: Clean and normalize raw data
- **Models**:
  - `stg_customers__cleaned`: Trim whitespace, normalize casing, type conversion
  - `stg_accounts__cleaned`: Validate balances, normalize account types

#### Intermediate Layer
- **Materialization**: Ephemeral (computed on-the-fly)
- **Purpose**: Reusable business logic components
- **Models**:
  - `int_accounts__with_customer`: Join accounts with customer data
  - `int_savings_accounts_only`: Filter to savings accounts

#### Marts Layer
- **Materialization**: Tables (persistent storage)
- **Purpose**: Business-ready analytical outputs
- **Models**:
  - `account_summary`: Calculate interest rates and projections

### 3. Output Layer

**Purpose**: Export results in multiple formats

**Components**:
- `account_summary_csv`: Export to CSV format
- `account_summary_parquet`: Export to Parquet with compression
- `account_summary_to_databricks`: Load to Databricks (production only)

### 4. Resource Layer

**Purpose**: Manage external connections and configuration

**Components**:
- `DataPlatformConfig`: Environment-driven configuration
- `DuckDBResource`: Local database connection
- `DatabricksResource`: Production database connection
- `ParquetIOManager`: Parquet file I/O management

## Data Flow

### End-to-End Pipeline Flow

1. **Ingestion Phase**
   - Read CSV files from `data/inputs/`
   - Validate file existence and schema
   - Create raw data assets in Dagster

2. **Staging Phase**
   - Clean and normalize customer data
   - Clean and normalize account data
   - Run data quality tests (uniqueness, not null, accepted values)

3. **Intermediate Phase**
   - Join accounts with customer information
   - Filter to savings accounts only
   - Prepare data for business logic

4. **Marts Phase**
   - Calculate interest rates based on balance tiers
   - Apply bonus rates for customers with loans
   - Generate final account summary with projections

5. **Output Phase**
   - Export to CSV for spreadsheet analysis
   - Export to Parquet for data science workflows
   - Load to Databricks for production analytics (prod only)

## Scalability Considerations

### Current Design (Demo Scale)

- Dataset size: < 10,000 rows
- Processing time: < 1 minute
- Storage: Local filesystem
- Compute: Single-threaded DuckDB

### Production Scale (Future)

- Dataset size: Millions to billions of rows
- Processing time: Minutes to hours
- Storage: Cloud object storage (S3, ADLS)
- Compute: Distributed Databricks clusters

### Scalability Features

1. **Partitioning Support**
   - Daily/monthly partitions for incremental processing
   - Parallel execution across partitions
   - Efficient backfill capabilities

2. **Incremental Models**
   - Process only changed records
   - Reduce compute time and cost
   - Scale to billions of rows

3. **Resource Optimization**
   - Auto-scaling compute clusters
   - Configurable DBT thread counts
   - Optimized query execution plans

## Security Considerations

### Secrets Management

- All credentials stored in environment variables
- No hardcoded secrets in source code
- `.env` file excluded from version control
- Production secrets managed via Kubernetes secrets or cloud secret managers

### Data Access Control

- Database-level access control (Databricks Unity Catalog)
- Role-based access to Dagster UI
- Audit logging for all data access

### Network Security

- Databricks connections over HTTPS
- VPC/VNet isolation in production
- Firewall rules for database access

## Monitoring and Observability

### Dagster UI Metrics

- Asset materialization success/failure rates
- Execution duration trends
- Data quality check results
- Asset lineage visualization

### Custom Metrics

- Row counts at each transformation layer
- Data quality test pass rates
- Output file sizes
- Database query performance

### Alerting Strategy

- Asset failures → PagerDuty/Slack
- Data quality failures → Email/Slack
- Performance degradation → Monitoring dashboard

## Deployment Architecture

### Local Development

```yaml
services:
  dagster-webserver:
    - Dagster UI on port 3000
    - Hot-reload for code changes
  
  dagster-daemon:
    - Background scheduler
    - Sensor execution
  
  dagster-user-code:
    - User code location
    - Volume mounts for live development
  
  postgres:
    - Dagster metadata storage
```

### Production (Kubernetes)

- Dagster deployed via Helm chart
- Auto-scaling user code deployments
- Managed PostgreSQL for metadata
- Databricks for compute and storage

## Design Trade-offs

### Dagster vs. Airflow

**Chosen**: Dagster
**Rationale**: Asset-centric model, superior DBT integration, better local development experience
**Trade-off**: Steeper learning curve, smaller community

### Five-Layer Architecture

**Chosen**: Five layers (source → staging → snapshots → intermediate → marts)
**Rationale**: 
- Clear separation of concerns with dedicated source layer
- SCD2 historical tracking via snapshots layer  
- Incremental processing for performance
- Reusable components and quality gates
- Complete audit trail of all changes

**Trade-off**: More models to maintain, additional complexity for SCD2 tracking

### DuckDB vs. SQLite for Local Development

**Chosen**: DuckDB
**Rationale**: OLAP-optimized, native CSV/Parquet support, fast analytics
**Trade-off**: Less familiar to some developers

## Future Enhancements

1. **Real-time Processing**: Add streaming ingestion with Kafka
2. **Data Catalog**: Integrate with DataHub or Amundsen
3. **ML Integration**: Add feature engineering and model training assets
4. **Advanced Monitoring**: Integrate with Datadog or New Relic
5. **Multi-region Deployment**: Support geo-distributed processing
