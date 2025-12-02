# Configuration Guide

## Overview

The LendingClub Data Pipeline uses environment-driven configuration to support multiple deployment environments (dev, staging, prod) without code changes.

## Environment Variables

### Required Variables

| Variable | Description | Valid Values | Default |
|----------|-------------|--------------|---------|
| `ENVIRONMENT` | Deployment environment | `dev`, `staging`, `prod` | `dev` |
| `DATABASE_TYPE` | Database backend | `duckdb`, `databricks` | `duckdb` |
| `DBT_TARGET` | DBT profile target | `dev`, `prod` | `dev` |
| `OUTPUT_PATH` | Directory for output files | Any valid path | `data/outputs` |
| `DUCKDB_PATH` | Path to DuckDB file | Any valid path | `data/duckdb/lending_club.duckdb` |

### Databricks Variables (Required when DATABASE_TYPE=databricks)

| Variable | Description | Example |
|----------|-------------|---------|
| `DATABRICKS_HOST` | Databricks workspace URL | `your-workspace.cloud.databricks.com` |
| `DATABRICKS_TOKEN` | Personal access token | `dapi...` |
| `DATABRICKS_CATALOG` | Unity Catalog name | `main` |
| `DATABRICKS_SCHEMA` | Schema/database name | `lending_club` |
| `DATABRICKS_HTTP_PATH` | SQL warehouse HTTP path | `/sql/1.0/warehouses/abc123` |

## Configuration Profiles

### Development Profile (Local)

```bash
# .env
ENVIRONMENT=dev
DATABASE_TYPE=duckdb
DBT_TARGET=dev
OUTPUT_PATH=data/outputs
DUCKDB_PATH=data/duckdb/lending_club.duckdb
```

**Characteristics:**
- Uses local DuckDB database
- Outputs to local filesystem
- Fast iteration, no cloud costs
- Suitable for development and testing

### Production Profile (Databricks)

```bash
# .env
ENVIRONMENT=prod
DATABASE_TYPE=databricks
DBT_TARGET=prod
OUTPUT_PATH=s3://your-bucket/outputs

# Databricks credentials
DATABRICKS_HOST=your-workspace.cloud.databricks.com
DATABRICKS_TOKEN=dapi...
DATABRICKS_CATALOG=main
DATABRICKS_SCHEMA=lending_club
DATABRICKS_HTTP_PATH=/sql/1.0/warehouses/abc123
```

**Characteristics:**
- Uses Databricks SQL warehouse
- Outputs to cloud storage (S3/ADLS)
- Scalable for large datasets
- Production-grade reliability

## Usage in Code

### Loading Configuration

```python
from lending_club_pipeline.resources import DataPlatformConfig

# Load from environment variables
config = DataPlatformConfig.from_env()

# Access configuration values
print(f"Environment: {config.environment}")
print(f"Database: {config.database_type}")
print(f"Output path: {config.output_path}")
```

### Conditional Logic

```python
# Check if running locally
if config.is_local():
    print("Running in local development mode")

# Check if running in production
if config.is_production():
    print("Running in production mode")

# Get database connection string
conn_string = config.get_database_connection_string()
```

## Validation

The configuration system validates all inputs at startup:

### Environment Validation
- `ENVIRONMENT` must be one of: `dev`, `staging`, `prod`
- Invalid values raise `ValueError`

### Database Type Validation
- `DATABASE_TYPE` must be one of: `duckdb`, `databricks`
- Invalid values raise `ValueError`

### Databricks Validation
- When `DATABASE_TYPE=databricks`, all Databricks variables are required
- Missing variables raise `ValueError` with list of missing fields

## Best Practices

### 1. Never Commit Secrets

```bash
# Add to .gitignore
.env
.env.local
.env.production
```

### 2. Use .env.example as Template

```bash
# Copy template
cp .env.example .env

# Edit with your values
vim .env
```

### 3. Validate Configuration Early

```python
# At application startup
try:
    config = DataPlatformConfig.from_env()
    print("✓ Configuration loaded successfully")
except ValueError as e:
    print(f"✗ Configuration error: {e}")
    sys.exit(1)
```

### 4. Use Environment-Specific Files

```bash
# Development
.env.dev

# Staging
.env.staging

# Production
.env.prod
```

Load the appropriate file:
```bash
# Development
docker-compose --env-file .env.dev up

# Production
docker-compose --env-file .env.prod up
```

## Troubleshooting

### Error: "Invalid ENVIRONMENT"

**Cause:** ENVIRONMENT variable has invalid value

**Solution:** Set to one of: `dev`, `staging`, `prod`

```bash
export ENVIRONMENT=dev
```

### Error: "DATABASE_TYPE is 'databricks' but missing required fields"

**Cause:** Using Databricks but missing credentials

**Solution:** Set all required Databricks variables

```bash
export DATABRICKS_HOST=your-workspace.cloud.databricks.com
export DATABRICKS_TOKEN=dapi...
export DATABRICKS_CATALOG=main
export DATABRICKS_SCHEMA=lending_club
export DATABRICKS_HTTP_PATH=/sql/1.0/warehouses/abc123
```

### Error: "No module named 'lending_club_pipeline'"

**Cause:** Python can't find the package

**Solution:** Install the package or add to PYTHONPATH

```bash
# Install in development mode
pip install -e .

# Or add to PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"
```

## Security Considerations

### Secrets Management

**Development:**
- Use `.env` file (gitignored)
- Never commit secrets to version control

**Production:**
- Use Kubernetes secrets
- Use cloud secret managers (AWS Secrets Manager, Azure Key Vault)
- Use environment variables injected by orchestration platform

### Token Rotation

- Rotate Databricks tokens regularly (every 90 days)
- Use service principals instead of personal tokens in production
- Implement automated token rotation where possible

### Access Control

- Limit Databricks token permissions to minimum required
- Use separate tokens for dev/staging/prod
- Audit token usage regularly

## Examples

### Example 1: Local Development

```bash
# .env
ENVIRONMENT=dev
DATABASE_TYPE=duckdb
DBT_TARGET=dev
OUTPUT_PATH=data/outputs
DUCKDB_PATH=data/duckdb/lending_club.duckdb
```

```bash
# Start pipeline
docker-compose up
```

### Example 2: Production Deployment

```bash
# .env.prod
ENVIRONMENT=prod
DATABASE_TYPE=databricks
DBT_TARGET=prod
OUTPUT_PATH=s3://prod-bucket/lending-club/outputs

DATABRICKS_HOST=prod-workspace.cloud.databricks.com
DATABRICKS_TOKEN=${DATABRICKS_TOKEN}  # Injected by CI/CD
DATABRICKS_CATALOG=main
DATABRICKS_SCHEMA=lending_club
DATABRICKS_HTTP_PATH=/sql/1.0/warehouses/prod-warehouse
```

```bash
# Deploy with Kubernetes
kubectl create secret generic databricks-token \
  --from-literal=token=${DATABRICKS_TOKEN}

kubectl apply -f k8s/deployment.yaml
```

### Example 3: Testing Configuration

```python
import os
from lending_club_pipeline.resources import DataPlatformConfig

# Test development config
os.environ["ENVIRONMENT"] = "dev"
os.environ["DATABASE_TYPE"] = "duckdb"
config = DataPlatformConfig.from_env()
assert config.is_local()
assert not config.is_production()

# Test production config
os.environ["ENVIRONMENT"] = "prod"
os.environ["DATABASE_TYPE"] = "databricks"
os.environ["DATABRICKS_HOST"] = "test.databricks.com"
os.environ["DATABRICKS_TOKEN"] = "test-token"
os.environ["DATABRICKS_CATALOG"] = "test"
os.environ["DATABRICKS_SCHEMA"] = "test"
os.environ["DATABRICKS_HTTP_PATH"] = "/sql/1.0/warehouses/test"
config = DataPlatformConfig.from_env()
assert not config.is_local()
assert config.is_production()
```
