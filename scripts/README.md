# Scripts Directory

This directory contains utility scripts for validating and testing the LendingClub Pipeline.

## Available Scripts

### 1. validate_environment.py

**Purpose:** Validates the local development environment setup.

**What it checks:**
- Python version (>= 3.8)
- Docker installation and daemon status
- Docker Compose installation
- Required project files
- .env configuration
- Data directories and permissions
- Input data files
- Python dependencies (optional)
- Available disk space

**Usage:**
```bash
python3 scripts/validate_environment.py
```

**When to use:**
- Before starting development
- After cloning the repository
- When troubleshooting setup issues
- Before running the pipeline for the first time

---

### 2. validate_pipeline.py

**Purpose:** Validates pipeline execution and output data quality.

**What it checks:**
- Input CSV files structure and content
- Docker Compose services status
- Dagster UI accessibility
- DuckDB database state
- Output files (CSV and Parquet)
- Output schema validation
- Data quality checks (nulls, ranges, calculations)
- Consistency between output formats
- Sample queries on output data

**Usage:**
```bash
python3 scripts/validate_pipeline.py
```

**When to use:**
- After running the pipeline
- To verify output data quality
- When troubleshooting pipeline issues
- As part of CI/CD validation

---

### 3. validate-setup.sh

**Purpose:** Shell script for basic Docker and file system validation.

**What it checks:**
- Docker and Docker Compose installation
- Docker daemon status
- Required project files
- .env file (creates from .env.example if missing)
- Input data files
- Directory permissions
- Available disk space

**Usage:**
```bash
./scripts/validate-setup.sh
```

**When to use:**
- Quick environment check
- In CI/CD pipelines
- When you prefer shell scripts over Python

---

### 4. test_pipeline_docker.sh

**Purpose:** Comprehensive test script for full pipeline execution in Docker Compose.

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

**When to use:**
- End-to-end testing of the pipeline
- After making changes to the pipeline
- Before deploying to production
- As part of integration testing

---

### 5. create_sample_data.py

**Purpose:** Creates sample CSV data files for testing.

**Usage:**
```bash
python3 scripts/create_sample_data.py
```

**When to use:**
- When input files are missing
- For testing with different data
- To reset to known good data

---

### 6. run_pipeline_locally.py

**Purpose:** Runs the pipeline locally without Docker.

**Usage:**
```bash
python3 scripts/run_pipeline_locally.py
```

**When to use:**
- Local development without Docker
- Debugging specific assets
- Quick testing of changes

---

### 7. setup_local_env.sh

**Purpose:** Sets up the local development environment.

**Usage:**
```bash
./scripts/setup_local_env.sh
```

**When to use:**
- First-time setup
- After cloning the repository
- To reset the environment

---

### 8. validate_asset_metadata.py

**Purpose:** Validates Dagster asset metadata and lineage.

**Usage:**
```bash
python3 scripts/validate_asset_metadata.py
```

**When to use:**
- To verify asset definitions
- To check asset lineage
- When troubleshooting asset issues

---

## Recommended Workflow

### Initial Setup
```bash
# 1. Validate environment
python3 scripts/validate_environment.py

# 2. Set up local environment (if needed)
./scripts/setup_local_env.sh

# 3. Validate Docker setup
./scripts/validate-setup.sh
```

### Running the Pipeline
```bash
# 1. Start Docker Compose
docker-compose up -d

# 2. Run full pipeline test
./scripts/test_pipeline_docker.sh

# 3. Validate outputs
python3 scripts/validate_pipeline.py
```

### Development Workflow
```bash
# 1. Make code changes

# 2. Run pipeline locally (optional)
python3 scripts/run_pipeline_locally.py

# 3. Test in Docker
./scripts/test_pipeline_docker.sh

# 4. Validate outputs
python3 scripts/validate_pipeline.py
```

### Troubleshooting
```bash
# Check environment
python3 scripts/validate_environment.py

# Check Docker services
docker-compose ps
docker-compose logs

# Validate pipeline state
python3 scripts/validate_pipeline.py

# Check asset metadata
python3 scripts/validate_asset_metadata.py
```

---

## Exit Codes

All scripts follow standard exit code conventions:
- `0`: Success
- `1`: Failure or validation errors

This allows scripts to be used in CI/CD pipelines and automated workflows.

---

## Dependencies

### Python Scripts
- Python >= 3.8
- pandas
- pyarrow (for Parquet support)
- duckdb (optional, for database checks)
- requests (optional, for UI checks)

### Shell Scripts
- bash
- docker
- docker-compose
- curl (for HTTP checks)
- Standard Unix utilities (wc, du, chmod, etc.)

---

## Environment Variables

Scripts respect the following environment variables from `.env`:
- `ENVIRONMENT`: dev, staging, or prod
- `DATABASE_TYPE`: duckdb or databricks
- `DUCKDB_PATH`: Path to DuckDB database file
- `DBT_TARGET`: dev or prod
- `OUTPUT_PATH`: Path for output files

---

## Notes

- All scripts should be run from the project root directory
- Scripts are designed to be idempotent (safe to run multiple times)
- Scripts provide colored output for better readability
- Scripts include detailed error messages and suggestions
- Scripts can be used in CI/CD pipelines

---

## Contributing

When adding new scripts:
1. Follow the naming convention: `verb_noun.py` or `verb-noun.sh`
2. Add execute permissions: `chmod +x scripts/your_script.sh`
3. Include a docstring or header comment explaining the purpose
4. Add colored output for better UX
5. Return appropriate exit codes
6. Update this README with script documentation
