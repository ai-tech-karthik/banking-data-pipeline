# Lending Club Pipeline - Quick Start Guide

Quick reference for running the pipeline. For detailed instructions, see `PIPELINE_EXECUTION_GUIDE.md`.

---

## Prerequisites

```bash
# Install dependencies
pip install -r requirements.txt

# Create directories
mkdir -p data/duckdb data/outputs data/inputs dagster_home

# Add input files to data/inputs/
# - Customer.csv
# - accounts.csv
```

---

## Run Pipeline - DuckDB (Local)

### 1. Configure Environment
```bash
# Edit .env file
DATABASE_TYPE=duckdb
DBT_TARGET=dev
DUCKDB_PATH=/absolute/path/to/lc-pipeline-v1/data/duckdb/lending_club.duckdb
DAGSTER_HOME=/absolute/path/to/lc-pipeline-v1/dagster_home
```

### 2. Run Pipeline
```bash
export DAGSTER_HOME=/absolute/path/to/lc-pipeline-v1/dagster_home
dagster asset materialize --select '*' -m src.lending_club_pipeline.definitions
```

### 3. Verify Results
```bash
# Check outputs
ls -lh data/outputs/

# Run tests
python tests/smoke_test.py
```

**Expected Duration:** ~20 seconds

---

## Run Pipeline - Databricks (Production)

### 1. Configure Environment
```bash
# Edit .env file
DATABASE_TYPE=databricks
DBT_TARGET=prod
DATABRICKS_HOST=your-workspace.cloud.databricks.com
DATABRICKS_TOKEN=your-token
DATABRICKS_CATALOG=workspace
DATABRICKS_SCHEMA=default
DATABRICKS_HTTP_PATH=/sql/1.0/warehouses/your-warehouse-id
DAGSTER_HOME=/absolute/path/to/lc-pipeline-v1/dagster_home
```

### 2. Test Connection
```bash
python -c "from databricks import sql; import os; from dotenv import load_dotenv; load_dotenv(); conn = sql.connect(server_hostname=os.getenv('DATABRICKS_HOST'), http_path=os.getenv('DATABRICKS_HTTP_PATH'), access_token=os.getenv('DATABRICKS_TOKEN')); print('✓ Connected'); conn.close()"
```

### 3. Run Pipeline
```bash
export DAGSTER_HOME=/absolute/path/to/lc-pipeline-v1/dagster_home
dagster asset materialize --select '*' -m src.lending_club_pipeline.definitions
```

### 4. Verify Results
```bash
# Check outputs
ls -lh data/outputs/

# Run tests
python tests/smoke_test.py
```

**Expected Duration:** ~80 seconds

---

## Common Commands

### View Pipeline Assets
```bash
dagster asset list -m src.lending_club_pipeline.definitions
```

### Run Specific Asset
```bash
dagster asset materialize --select 'customers_raw' -m src.lending_club_pipeline.definitions
```

### Run DBT Only
```bash
# Export environment variables
export $(cat .env | grep -v '^#' | xargs)

# Run all models
dbt run --target prod --project-dir dbt_project --profiles-dir dbt_project

# Run snapshots
dbt snapshot --target prod --project-dir dbt_project --profiles-dir dbt_project

# Run tests
dbt test --target prod --project-dir dbt_project --profiles-dir dbt_project

# Or run everything with dbt build
dbt build --target prod --project-dir dbt_project --profiles-dir dbt_project
```

### Check DuckDB Tables
```bash
python -c "import duckdb; conn = duckdb.connect('data/duckdb/lending_club.duckdb'); print(conn.execute('SHOW ALL TABLES').df())"
```

### View Output Data
```bash
cat data/outputs/account_summary.csv
```

---

## Troubleshooting

### Issue: Path errors
**Solution:** Use absolute paths in `.env` for `DUCKDB_PATH` and `DAGSTER_HOME`

### Issue: Databricks connection fails
**Solution:** 
- Verify SQL Warehouse is running
- Check token is valid
- Verify HTTP path format

### Issue: DBT tests fail
**Solution:**
- Ensure ingestion completed successfully
- Check raw tables exist
- Verify database connection

### Issue: Missing input files
**Solution:** Add `Customer.csv` and `accounts.csv` to `data/inputs/`

---

## Output Files

After successful execution:
```
data/outputs/
├── account_summary.csv      # CSV format (351 bytes)
└── account_summary.parquet  # Parquet format (4.3 KB)
```

**Data:** 8 rows with columns:
- customer_id
- account_id
- original_balance
- interest_rate
- annual_interest
- new_balance

---

## Test Results

### Expected Smoke Test Output
```
============================================================
RESULTS: 3-4 passed, 0 failed, 0-1 skipped
============================================================
✓ Output Files Exist
✓ Output Data Quality
✓ CSV/Parquet Consistency
✓ Databricks Table Exists (Databricks only)
```

---

## Additional Resources

- **Full Guide:** `PIPELINE_EXECUTION_GUIDE.md`

---
