# Development Guide

## Overview

This guide covers local development workflows for the LendingClub Data Pipeline. It includes instructions for adding new assets, modifying transformations, testing, and debugging.

## Development Environment

### Local Setup

The pipeline uses Docker Compose for local development with hot-reload capabilities:

```bash
# Start development environment
docker-compose up -d

# View logs
docker-compose logs -f dagster-user-code
```

### Directory Structure

```
lending-club-pipeline/
├── src/lending_club_pipeline/    # Dagster code
│   ├── assets/                   # Asset definitions
│   ├── resources/                # Resources and config
│   └── io_managers/              # I/O managers
├── dbt_project/                  # DBT transformations
│   ├── models/                   # DBT models
│   ├── tests/                    # DBT tests
│   └── macros/                   # DBT macros
├── data/                         # Data files
│   ├── inputs/                   # Source CSV files
│   └── outputs/                  # Generated outputs
└── tests/                        # Python tests
    ├── unit/                     # Unit tests
    ├── integration/              # Integration tests
    └── e2e/                      # End-to-end tests
```

## Development Workflows

### Adding a New Dagster Asset

1. **Create the asset file** (or add to existing file):

```python
# src/lending_club_pipeline/assets/my_new_asset.py
from dagster import asset
import pandas as pd

@asset(
    group_name="my_group",
    compute_kind="python"
)
def my_new_asset(context, upstream_asset) -> pd.DataFrame:
    """
    Description of what this asset does.
    
    Args:
        upstream_asset: Input from another asset
        
    Returns:
        Processed DataFrame
    """
    context.log.info("Processing my_new_asset")
    
    # Your transformation logic
    df = upstream_asset.copy()
    df['new_column'] = df['existing_column'] * 2
    
    # Add metadata
    context.add_output_metadata({
        "num_rows": len(df),
        "columns": df.columns.tolist()
    })
    
    return df
```

2. **Register the asset** in `definitions.py`:

```python
from .assets.my_new_asset import my_new_asset

defs = Definitions(
    assets=[
        # ... existing assets
        my_new_asset,
    ],
    resources={...}
)
```

3. **Reload the workspace** in Dagster UI or restart:

```bash
docker-compose restart dagster-user-code
```


### Adding a New DBT Model

1. **Create the model file**:

```bash
# Choose the appropriate layer
# Staging: dbt_project/models/staging/
# Intermediate: dbt_project/models/intermediate/
# Marts: dbt_project/models/marts/

# Example: Create intermediate model
touch dbt_project/models/intermediate/int_my_new_model.sql
```

2. **Write the SQL transformation**:

```sql
-- dbt_project/models/intermediate/int_my_new_model.sql

{{ config(
    materialized='ephemeral',
    tags=['intermediate']
) }}

SELECT
    customer_id,
    account_id,
    balance,
    -- Add your transformation logic
    balance * 1.05 as projected_balance
FROM {{ ref('stg_accounts__cleaned') }}
WHERE balance > 1000
```

3. **Add model documentation and tests**:

```yaml
# dbt_project/models/intermediate/_intermediate.yml

models:
  - name: int_my_new_model
    description: "Description of the model"
    columns:
      - name: customer_id
        description: "Customer identifier"
        tests:
          - not_null
      - name: projected_balance
        description: "Balance with 5% projection"
        tests:
          - not_null
```

4. **Test the model locally**:

```bash
# Run the specific model
docker-compose exec dagster-user-code dbt run --select int_my_new_model --project-dir dbt_project

# Run tests
docker-compose exec dagster-user-code dbt test --select int_my_new_model --project-dir dbt_project
```

### Modifying Existing Assets

1. **Edit the asset code** in `src/lending_club_pipeline/assets/`
2. **Save the file** (hot-reload will pick up changes)
3. **Reload workspace** in Dagster UI
4. **Test the changes** by materializing the asset

### Modifying DBT Models

1. **Edit the model SQL** in `dbt_project/models/`
2. **Save the file**
3. **Test locally**:

```bash
# Run the modified model
docker-compose exec dagster-user-code dbt run --select my_model --project-dir dbt_project

# Run tests
docker-compose exec dagster-user-code dbt test --select my_model --project-dir dbt_project
```

4. **Materialize in Dagster** to see changes in the pipeline

## Testing

### Running Python Tests

```bash
# Run all tests
docker-compose exec dagster-user-code pytest

# Run specific test file
docker-compose exec dagster-user-code pytest tests/unit/test_ingestion.py

# Run with coverage
docker-compose exec dagster-user-code pytest --cov=src/lending_club_pipeline

# Run with verbose output
docker-compose exec dagster-user-code pytest -v
```

### Running DBT Tests

```bash
# Run all DBT tests
docker-compose exec dagster-user-code dbt test --project-dir dbt_project

# Run tests for specific model
docker-compose exec dagster-user-code dbt test --select stg_customers__cleaned --project-dir dbt_project

# Run tests for specific layer
docker-compose exec dagster-user-code dbt test --select staging --project-dir dbt_project
```

### Writing Unit Tests

Create test files in `tests/unit/`:

```python
# tests/unit/test_my_asset.py
import pytest
import pandas as pd
from lending_club_pipeline.assets.my_new_asset import my_new_asset

def test_my_new_asset():
    """Test that my_new_asset processes data correctly"""
    # Arrange
    input_df = pd.DataFrame({
        'existing_column': [1, 2, 3]
    })
    
    # Act
    result = my_new_asset(input_df)
    
    # Assert
    assert 'new_column' in result.columns
    assert result['new_column'].tolist() == [2, 4, 6]
    assert len(result) == 3
```

### Writing Integration Tests

Create test files in `tests/integration/`:

```python
# tests/integration/test_pipeline.py
from dagster import materialize
from lending_club_pipeline.assets import customers_raw, accounts_raw

def test_ingestion_assets():
    """Test that ingestion assets execute successfully"""
    result = materialize([customers_raw, accounts_raw])
    assert result.success
```

## Debugging

### Viewing Logs

```bash
# View all logs
docker-compose logs -f

# View specific service logs
docker-compose logs -f dagster-user-code

# View last 100 lines
docker-compose logs --tail=100 dagster-user-code
```

### Debugging Asset Execution

1. **Add logging** to your asset:

```python
@asset
def my_asset(context):
    context.log.info("Starting processing")
    context.log.debug(f"Input data: {data}")
    context.log.warning("Potential issue detected")
    # ... your code
```

2. **View logs in Dagster UI**:
   - Navigate to the asset run
   - Click on "Logs" tab
   - Filter by log level

3. **Use breakpoints** (for local Python debugging):

```python
import pdb; pdb.set_trace()  # Add breakpoint
```

### Debugging DBT Models

1. **Compile the model** to see generated SQL:

```bash
docker-compose exec dagster-user-code dbt compile --select my_model --project-dir dbt_project

# View compiled SQL
cat dbt_project/target/compiled/dbt_project/models/my_model.sql
```

2. **Run with debug logging**:

```bash
docker-compose exec dagster-user-code dbt run --select my_model --project-dir dbt_project --debug
```

3. **Query the database directly**:

```bash
# Access DuckDB CLI
docker-compose exec dagster-user-code python -c "
import duckdb
conn = duckdb.connect('data/duckdb/lending_club.duckdb')
result = conn.execute('SELECT * FROM stg_customers__cleaned LIMIT 5').fetchdf()
print(result)
"
```

### Common Issues and Solutions

**Issue**: Asset not appearing in UI
```bash
# Solution: Reload workspace
# In UI: Click "Reload definitions"
# Or restart: docker-compose restart dagster-user-code
```

**Issue**: Import errors
```bash
# Solution: Rebuild container
docker-compose build dagster-user-code
docker-compose up -d
```

**Issue**: DBT model not found
```bash
# Solution: Check model path and ref() calls
# Verify model exists in correct directory
ls -la dbt_project/models/
```

## Code Quality

### Linting and Formatting

```bash
# Format Python code with black
docker-compose exec dagster-user-code black src/

# Lint with flake8
docker-compose exec dagster-user-code flake8 src/

# Type checking with mypy
docker-compose exec dagster-user-code mypy src/
```

### DBT Best Practices

1. **Use consistent naming**:
   - Staging: `stg_<source>__<entity>`
   - Intermediate: `int_<entity>__<description>`
   - Marts: `<business_concept>`

2. **Add documentation**:
   - Every model should have a description
   - Key columns should be documented
   - Business logic should be explained

3. **Write tests**:
   - Unique and not_null for primary keys
   - Accepted_values for categorical columns
   - Custom tests for business logic

4. **Use appropriate materializations**:
   - Staging: `view`
   - Intermediate: `ephemeral`
   - Marts: `table`

### Dagster Best Practices

1. **Use asset groups** for organization
2. **Add metadata** to assets (row counts, schemas)
3. **Use type hints** for inputs and outputs
4. **Write docstrings** for all assets
5. **Handle errors gracefully** with try-except
6. **Log important information** using context.log

## Performance Optimization

### Profiling Asset Execution

```python
@asset
def my_asset(context):
    import time
    start = time.time()
    
    # Your code
    result = process_data()
    
    duration = time.time() - start
    context.add_output_metadata({
        "execution_time_seconds": duration
    })
    
    return result
```

### Optimizing DBT Models

1. **Use incremental models** for large datasets:

```sql
{{ config(
    materialized='incremental',
    unique_key='id'
) }}

SELECT * FROM source
{% if is_incremental() %}
WHERE updated_at > (SELECT MAX(updated_at) FROM {{ this }})
{% endif %}
```

2. **Add indexes** for frequently queried columns
3. **Use CTEs** for readability and optimization
4. **Avoid SELECT *** when possible

### Monitoring Performance

```bash
# View DBT execution times
docker-compose exec dagster-user-code dbt run --project-dir dbt_project

# Check output for model timing:
# Completed successfully
# Done. PASS=5 WARN=0 ERROR=0 SKIP=0 TOTAL=5
```

## Git Workflow

### Branch Strategy

```bash
# Create feature branch
git checkout -b feature/my-new-feature

# Make changes and commit
git add .
git commit -m "Add new feature"

# Push to remote
git push origin feature/my-new-feature

# Create pull request
```

### Commit Message Format

```
<type>: <subject>

<body>

<footer>
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `test`: Adding tests
- `refactor`: Code refactoring
- `chore`: Maintenance tasks

Example:
```
feat: Add customer segmentation asset

- Create new asset for customer segmentation
- Add tests for segmentation logic
- Update documentation

Closes #123
```

## Continuous Integration

### Pre-commit Checks

Before committing, run:

```bash
# Format code
docker-compose exec dagster-user-code black src/

# Run linters
docker-compose exec dagster-user-code flake8 src/

# Run tests
docker-compose exec dagster-user-code pytest

# Run DBT tests
docker-compose exec dagster-user-code dbt test --project-dir dbt_project
```

### CI Pipeline

The CI pipeline runs automatically on pull requests:

1. **Lint**: Check code style
2. **Test**: Run all tests
3. **Build**: Build Docker images
4. **DBT**: Run DBT models and tests

## Deployment

### Local Testing Before Deployment

```bash
# Run full pipeline
docker-compose exec dagster-user-code dagster asset materialize --select "*"

# Verify outputs
ls -la data/outputs/

# Run all tests
docker-compose exec dagster-user-code pytest
docker-compose exec dagster-user-code dbt test --project-dir dbt_project
```

### Deployment Checklist

- [ ] All tests passing
- [ ] Code reviewed and approved
- [ ] Documentation updated
- [ ] Environment variables configured
- [ ] Database migrations applied (if any)
- [ ] Monitoring and alerts configured

## Resources

### Documentation

- [Dagster Documentation](https://docs.dagster.io)
- [DBT Documentation](https://docs.getdbt.com)
- [DuckDB Documentation](https://duckdb.org/docs)

### Internal Documentation

- [System Design](../architecture/system_design.md)
- [Data Flow](../architecture/data_flow.md)
- [Setup Guide](setup.md)

### Getting Help

- Check logs: `docker-compose logs -f`
- Review error messages in Dagster UI
- Consult team documentation
- Ask in team Slack channel
