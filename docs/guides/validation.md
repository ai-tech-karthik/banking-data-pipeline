# Pipeline Validation Guide

This guide explains how to validate your LendingClub Pipeline setup and execution.

## Overview

The pipeline includes comprehensive validation scripts to ensure:
- Environment is properly configured
- Docker services are running correctly
- Input data is valid
- Pipeline executes successfully
- Output data meets quality standards

## Validation Scripts

### 1. Environment Validation

**Script:** `scripts/validate_environment.py`

Validates your local development environment before running the pipeline.

**Checks performed:**
- Python version (>= 3.8 required)
- Docker installation and daemon status
- Docker Compose installation
- Required project files exist
- .env configuration is valid
- Data directories exist and are writable
- Input CSV files are present
- Python dependencies (core packages)
- Available disk space

**Usage:**
```bash
python3 scripts/validate_environment.py
```

**Expected output:**
```
✓ Environment validation successful!

Next steps:
  1. Review .env file and update if needed
  2. Run: docker-compose up -d
  3. Access Dagster UI at http://localhost:3000
  4. Run validation script: python scripts/validate_pipeline.py
```

### 2. Pipeline Validation

**Script:** `scripts/validate_pipeline.py`

Validates pipeline execution and output data quality.

**Checks performed:**
- Input CSV structure and content
- Docker Compose services status
- Dagster UI accessibility
- DuckDB database state
- Output files exist (CSV and Parquet)
- Output schema matches expected structure
- Data quality checks:
  - No nulls in required fields
  - Interest rates in valid range (1%-2.5%)
  - Calculations are correct
- Consistency between CSV and Parquet formats
- Sample queries on output data

**Usage:**
```bash
python3 scripts/validate_pipeline.py
```

**Expected output:**
```
✓ Pipeline validation successful!

Your pipeline is working correctly.
```

### 3. Docker Pipeline Test

**Script:** `scripts/test_pipeline_docker.sh`

End-to-end test of the complete pipeline in Docker Compose.

**What it does:**
1. Validates environment using validate_environment.py
2. Starts Docker Compose services if not running
3. Waits for Dagster UI to be accessible
4. Verifies input data files
5. Cleans previous outputs
6. Optionally triggers pipeline execution
7. Validates outputs using validate_pipeline.py
8. Shows summary and next steps

**Usage:**
```bash
./scripts/test_pipeline_docker.sh
```

## Validation Workflow

### Initial Setup Validation

Run these commands after cloning the repository:

```bash
# 1. Validate environment
python3 scripts/validate_environment.py

# 2. Check Docker setup
./scripts/validate-setup.sh

# 3. Verify .env configuration
cat .env
```

### Pre-Execution Validation

Before running the pipeline:

```bash
# 1. Ensure Docker is running
docker info

# 2. Verify input files
ls -lh data/inputs/

# 3. Start Docker services
docker-compose up -d

# 4. Check services are running
docker-compose ps
```

### Post-Execution Validation

After materializing assets:

```bash
# 1. Validate outputs
python3 scripts/validate_pipeline.py

# 2. Check output files
ls -lh data/outputs/

# 3. View sample data
head data/outputs/account_summary.csv
```

## Data Quality Checks

The validation scripts perform these data quality checks:

### Input Data
- Files exist and are readable
- Required columns present
- No empty files
- Valid CSV format

### Output Data
- All expected columns present
- No nulls in required fields (customer_id, account_id, original_balance)
- Interest rates between 1% and 2.5%
- Annual interest = original_balance × interest_rate (within rounding)
- New balance = original_balance + annual_interest
- CSV and Parquet formats are consistent

### Calculations
- Base rate by balance tier:
  - < $10,000: 1.0%
  - $10,000 - $19,999: 1.5%
  - >= $20,000: 2.0%
- Bonus rate: +0.5% if has_loan = 'Yes'
- All calculations rounded to 2 decimal places

## Troubleshooting

### Environment Validation Fails

**Issue:** Python version too old
```bash
# Solution: Install Python >= 3.8
brew install python@3.11  # macOS
```

**Issue:** Docker not running
```bash
# Solution: Start Docker Desktop
open -a Docker  # macOS
```

**Issue:** Missing .env file
```bash
# Solution: Create from example
cp .env.example .env
```

### Pipeline Validation Fails

**Issue:** Input files not found
```bash
# Solution: Create sample data
python3 scripts/create_sample_data.py
```

**Issue:** Output files not found
```
Solution:
1. Open Dagster UI: http://localhost:3000
2. Go to Assets tab
3. Click "Materialize all"
4. Wait for completion
5. Re-run validation
```

**Issue:** Data quality checks fail
```
Solution:
1. Check Dagster logs: docker-compose logs
2. Review DBT test results in UI
3. Verify input data quality
4. Check transformation logic
```

### Docker Issues

**Issue:** Services not starting
```bash
# Check logs
docker-compose logs

# Restart services
docker-compose down
docker-compose up -d
```

**Issue:** Port 3000 already in use
```bash
# Find process using port
lsof -i :3000

# Kill process or change port in docker-compose.yml
```

## Sample Data

### Creating Sample Data

Use the provided script to create test data:

```bash
# Basic sample data
python3 scripts/create_sample_data.py

# Enhanced sample data with edge cases
python3 scripts/create_enhanced_sample_data.py
```

### Sample Data Characteristics

The enhanced sample data includes:
- Multiple balance tiers (< 10k, 10k-20k, >= 20k)
- Various loan statuses (Yes, No, None)
- Both account types (Savings, Checking)
- Edge cases:
  - Whitespace in fields
  - Casing variations
  - Boundary values
  - Multiple accounts per customer

## Continuous Validation

### During Development

```bash
# After making changes
docker-compose restart

# Materialize affected assets in UI

# Validate outputs
python3 scripts/validate_pipeline.py
```

### Before Committing

```bash
# Run full validation
./scripts/test_pipeline_docker.sh

# Run tests
pytest tests/

# Check code quality
black src/
flake8 src/
```

### In CI/CD

```yaml
# Example GitHub Actions workflow
- name: Validate Environment
  run: python3 scripts/validate_environment.py

- name: Start Services
  run: docker-compose up -d

- name: Run Pipeline
  run: # Materialize assets via CLI

- name: Validate Outputs
  run: python3 scripts/validate_pipeline.py
```

## Best Practices

1. **Always validate environment first** before running the pipeline
2. **Check Docker logs** if services fail to start
3. **Verify input data** before materializing assets
4. **Run validation after changes** to catch issues early
5. **Use sample data** for testing and development
6. **Monitor Dagster UI** during execution
7. **Review validation output** carefully for warnings
8. **Keep validation scripts updated** as pipeline evolves

## Next Steps

After successful validation:
1. Explore the Dagster UI asset lineage
2. Review DBT models in `dbt_project/models/`
3. Query output data for analysis
4. Run the test suite: `pytest tests/`
5. Review documentation in `docs/`
6. Make changes and re-validate

## Additional Resources

- [Setup Guide](setup.md) - Initial setup instructions
- [Development Guide](development.md) - Development workflow
- [Scripts README](../../scripts/README.md) - Detailed script documentation
