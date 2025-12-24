# Environment Switching Guide

Quick reference for switching between development (DuckDB) and production (Databricks) environments.

---

## 🔄 Quick Switch

### Switch to Development (Local)
```bash
# Edit .env file - change these 3 lines:
ENVIRONMENT=dev
DATABASE_TYPE=duckdb
DBT_TARGET=dev
```

### Switch to Production (Databricks)
```bash
# Edit .env file - change these 3 lines:
ENVIRONMENT=prod
DATABASE_TYPE=databricks
DBT_TARGET=prod
```

**That's it!** No code changes needed.

---

## 📋 Complete Configuration Examples

### Development Configuration (.env)
```properties
# Environment Configuration
ENVIRONMENT=dev
DATABASE_TYPE=duckdb
DBT_TARGET=dev

# DuckDB Configuration
DUCKDB_PATH=/absolute/path/to/banking-data-pipeline/data/duckdb/banking.duckdb

# Dagster Configuration
DAGSTER_HOME=/absolute/path/to/banking-data-pipeline/dagster_home

# Optional configurations (with defaults)
SNAPSHOT_TARGET_SCHEMA=snapshots
INCREMENTAL_STRATEGY=merge
DATA_QUALITY_ENABLED=true
OUTPUT_PATH=data/outputs
LOG_LEVEL=INFO
```

### Production Configuration (.env)
```properties
# Environment Configuration
ENVIRONMENT=prod
DATABASE_TYPE=databricks
DBT_TARGET=prod

# Databricks Configuration
DATABRICKS_HOST=your-workspace.cloud.databricks.com
DATABRICKS_TOKEN=your-databricks-token-here
DATABRICKS_CATALOG=workspace
DATABRICKS_SCHEMA=default
DATABRICKS_HTTP_PATH=/sql/1.0/warehouses/your-warehouse-id

# Dagster Configuration
DAGSTER_HOME=/absolute/path/to/banking-data-pipeline/dagster_home

# Optional configurations (with defaults)
SNAPSHOT_TARGET_SCHEMA=snapshots
INCREMENTAL_STRATEGY=merge
DATA_QUALITY_ENABLED=true
OUTPUT_PATH=data/outputs
LOG_LEVEL=INFO
```

---

## ✅ Verification

After switching, verify your configuration:

```bash
# Check environment variables
python -c "
from dotenv import load_dotenv
import os
load_dotenv()
print('Current Configuration:')
print(f'  Environment: {os.getenv(\"ENVIRONMENT\")}')
print(f'  Database: {os.getenv(\"DATABASE_TYPE\")}')
print(f'  DBT Target: {os.getenv(\"DBT_TARGET\")}')
"
```

Expected output for **Development**:
```
Current Configuration:
  Environment: dev
  Database: duckdb
  DBT Target: dev
```

Expected output for **Production**:
```
Current Configuration:
  Environment: prod
  Database: databricks
  DBT Target: prod
```

---

## 🚀 Running After Switch

### Development Mode
```bash
# Set Dagster home
export DAGSTER_HOME=/absolute/path/to/banking-data-pipeline/dagster_home

# Run pipeline
dagster asset materialize --select '*' -m src.banking_pipeline.definitions
```

### Production Mode
```bash
# Set Dagster home
export DAGSTER_HOME=/absolute/path/to/banking-data-pipeline/dagster_home

# Test Databricks connection first
python -c "from databricks import sql; import os; from dotenv import load_dotenv; load_dotenv(); conn = sql.connect(server_hostname=os.getenv('DATABRICKS_HOST'), http_path=os.getenv('DATABRICKS_HTTP_PATH'), access_token=os.getenv('DATABRICKS_TOKEN')); print('✓ Connected'); conn.close()"

# Run pipeline
dagster asset materialize --select '*' -m src.banking_pipeline.definitions
```

---

## 🐳 Docker Users

If using Docker Compose, restart services after switching:

```bash
# Stop services
docker-compose down

# Rebuild if needed (after .env changes)
docker-compose build --no-cache dagster-user-code

# Start services
docker-compose up -d

# View logs
docker-compose logs -f dagster-user-code
```

---

## 📊 Environment Comparison

| Feature | Development (DuckDB) | Production (Databricks) |
|---------|---------------------|------------------------|
| **Database** | Local DuckDB file | Databricks SQL Warehouse |
| **Cost** | Free | Pay per compute |
| **Speed** | Fast (20-30s) | Moderate (60-90s) |
| **Scale** | Small-Medium datasets | Large-Enterprise datasets |
| **Setup** | Minimal | Requires Databricks account |
| **Credentials** | Not required | Token required |
| **Outputs** | CSV + Parquet (local) | CSV + Parquet + Delta tables |
| **Use Case** | Development & Testing | Production workloads |

---

## 🔐 Security Notes

### Development
- No credentials needed
- Data stored locally
- Safe for testing with sample data

### Production
- **Never commit** `.env` file with real credentials
- Use environment variables in CI/CD
- Rotate Databricks tokens regularly (every 90 days)
- Use service principals instead of personal tokens
- Limit token permissions to minimum required

---

## 🐛 Troubleshooting

### Issue: Changes not taking effect
**Solution:** Restart services or reload environment
```bash
# For Docker
docker-compose restart

# For local Python
# Re-run with fresh environment
export $(cat .env | grep -v '^#' | xargs)
```

### Issue: Databricks connection fails
**Solution:** Verify credentials and SQL Warehouse status
```bash
# Test connection
python -c "from databricks import sql; import os; from dotenv import load_dotenv; load_dotenv(); conn = sql.connect(server_hostname=os.getenv('DATABRICKS_HOST'), http_path=os.getenv('DATABRICKS_HTTP_PATH'), access_token=os.getenv('DATABRICKS_TOKEN')); print('✓ Connected'); conn.close()"
```

### Issue: DuckDB file not found
**Solution:** Use absolute path in DUCKDB_PATH
```bash
# Wrong
DUCKDB_PATH=data/duckdb/banking.duckdb

# Correct
DUCKDB_PATH=/Users/username/project/banking-data-pipeline/data/duckdb/banking.duckdb
```

---

## 📚 Additional Resources

- **Full Documentation:** `PIPELINE_EXECUTION_GUIDE.md`
- **Quick Start:** `QUICK_START.md`
- **Configuration Guide:** `docs/guides/configuration.md`
- **Databricks Setup:** `docs/guides/databricks-setup.md`

---

## 💡 Best Practices

1. **Always test in dev first** before running in production
2. **Use separate data** for dev and prod environments
3. **Document any environment-specific configurations**
4. **Keep credentials secure** - never commit to Git
5. **Monitor costs** when running in production
6. **Set up alerts** for production pipeline failures
7. **Use version control** for configuration templates
8. **Automate environment switching** in CI/CD pipelines

---

**Last Updated:** December 21, 2024
