# Setup Guide

## Prerequisites

Before setting up the LendingClub Data Pipeline, ensure you have the following installed:

### Required Software

- **Docker**: Version 20.10 or higher
- **Docker Compose**: Version 2.0 or higher
- **Git**: For cloning the repository
- **Python**: Version 3.9 or higher (for local development without Docker)

### Optional Software

- **Make**: For using Makefile commands (recommended)
- **VS Code**: Recommended IDE with Python and Docker extensions

### System Requirements

- **RAM**: Minimum 4GB, recommended 8GB
- **Disk Space**: Minimum 5GB free space
- **OS**: macOS, Linux, or Windows with WSL2

## Installation Steps

### 1. Clone the Repository

```bash
git clone <repository-url>
cd lending-club-pipeline
```

### 2. Configure Environment Variables

Copy the example environment file and configure it:

```bash
cp .env.example .env
```

Edit `.env` file with your configuration:

```bash
# Environment (dev, staging, prod)
ENVIRONMENT=dev

# Database Configuration
DATABASE_TYPE=duckdb
DUCKDB_PATH=data/duckdb/lending_club.duckdb

# DBT Configuration
DBT_TARGET=dev
DBT_PROFILES_DIR=dbt_project

# Output Configuration
OUTPUT_PATH=data/outputs

# Dagster Configuration
DAGSTER_HOME=/opt/dagster/dagster_home
```


### 3. Prepare Sample Data

Ensure you have sample CSV files in the `data/inputs/` directory:

```bash
# Check if sample data exists
ls -la data/inputs/

# Expected files:
# - Customer.csv
# - accounts.csv
```

If sample data doesn't exist, you can create it using the provided script:

```bash
python scripts/create_sample_data.py
```

### 4. Build Docker Images

Build the Docker images for the pipeline:

```bash
# Using Docker Compose
docker-compose build

# Or using Make
make build
```

This will:
- Build the Dagster user code image
- Pull required images (PostgreSQL, Dagster webserver, daemon)
- Install Python dependencies
- Set up DBT packages

### 5. Start the Services

Start all services using Docker Compose:

```bash
# Start in detached mode
docker-compose up -d

# Or using Make
make up

# View logs
docker-compose logs -f
```

This will start:
- **Dagster Webserver**: UI on http://localhost:3000
- **Dagster Daemon**: Background scheduler
- **Dagster User Code**: Your pipeline code
- **PostgreSQL**: Metadata storage

### 6. Verify Installation

Check that all services are running:

```bash
# Check service status
docker-compose ps

# Expected output:
# NAME                    STATUS
# dagster-webserver       Up
# dagster-daemon          Up
# dagster-user-code       Up
# postgres                Up
```

Access the Dagster UI:
- Open browser to http://localhost:3000
- You should see the Dagster UI with your assets

### 7. Run Initial Pipeline

Execute the pipeline for the first time:

**Option 1: Via Dagster UI**
1. Navigate to http://localhost:3000
2. Click on "Assets" in the left sidebar
3. Select all assets
4. Click "Materialize selected"

**Option 2: Via Command Line**
```bash
# Execute inside the user code container
docker-compose exec dagster-user-code dagster asset materialize --select "*"

# Or using Make
make run-pipeline
```

### 8. Verify Outputs

Check that outputs were generated:

```bash
# List output files
ls -la data/outputs/

# Expected files:
# - account_summary.csv
# - account_summary.parquet

# View CSV output
head data/outputs/account_summary.csv
```

## Troubleshooting

### Docker Issues

**Problem**: Docker daemon not running
```bash
# Solution: Start Docker Desktop or Docker service
# macOS: Open Docker Desktop
# Linux: sudo systemctl start docker
```

**Problem**: Port 3000 already in use
```bash
# Solution: Change port in docker-compose.yml
# Edit ports section: "3001:3000" instead of "3000:3000"
```

**Problem**: Permission denied errors
```bash
# Solution: Fix file permissions
sudo chown -R $USER:$USER data/
chmod -R 755 data/
```

### Database Issues

**Problem**: DuckDB file locked
```bash
# Solution: Stop all services and remove lock
docker-compose down
rm data/duckdb/*.lock
docker-compose up -d
```

**Problem**: Database connection errors
```bash
# Solution: Verify environment variables
cat .env | grep DATABASE

# Ensure DUCKDB_PATH points to correct location
```

### DBT Issues

**Problem**: DBT models not found
```bash
# Solution: Verify DBT project structure
ls -la dbt_project/models/

# Reinstall DBT packages
docker-compose exec dagster-user-code dbt deps --project-dir dbt_project
```

**Problem**: DBT tests failing
```bash
# Solution: Run DBT tests manually to see details
docker-compose exec dagster-user-code dbt test --project-dir dbt_project

# Check test results in logs
```

### Pipeline Issues

**Problem**: Assets not appearing in UI
```bash
# Solution: Reload workspace
# In Dagster UI: Click "Reload definitions" button
# Or restart user code service
docker-compose restart dagster-user-code
```

**Problem**: Asset materialization fails
```bash
# Solution: Check logs for specific error
docker-compose logs dagster-user-code

# Common issues:
# - Missing input files
# - Invalid data format
# - Database connection errors
```

### Data Issues

**Problem**: Input CSV files not found
```bash
# Solution: Verify files exist and have correct names
ls -la data/inputs/

# Files must be named exactly:
# - Customer.csv (capital C)
# - accounts.csv (lowercase a)
```

**Problem**: Empty output files
```bash
# Solution: Check input data quality
# Verify CSV files have data
wc -l data/inputs/*.csv

# Check for data quality issues in staging layer
docker-compose exec dagster-user-code dbt test --select staging
```

## Validation Script

Run the validation script to check your setup:

```bash
# Make script executable
chmod +x scripts/validate-setup.sh

# Run validation
./scripts/validate-setup.sh
```

This will check:
- Docker and Docker Compose installation
- Required files and directories
- Environment configuration
- Service health
- Sample data availability

## Next Steps

After successful setup:

1. **Explore the UI**: Navigate through assets, runs, and lineage
2. **Review Documentation**: Read the development guide
3. **Run Tests**: Execute the test suite
4. **Customize Pipeline**: Modify assets and transformations
5. **Set Up Schedules**: Configure automated runs

## Cleanup

To stop and remove all services:

```bash
# Stop services
docker-compose down

# Remove volumes (WARNING: deletes all data)
docker-compose down -v

# Remove generated files
rm -rf data/outputs/*
rm -rf data/duckdb/*
rm -rf dbt_project/target/
rm -rf dbt_project/logs/
```
