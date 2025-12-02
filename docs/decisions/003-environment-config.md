# ADR 003: Environment-Driven Configuration

## Status

Accepted

## Context

We need a configuration strategy that:
- Supports multiple environments (dev, staging, prod)
- Keeps secrets out of source code
- Enables the same code to run in different environments
- Is easy to understand and maintain
- Follows security best practices
- Works with containerized deployments

### Requirements

1. **Environment Flexibility**: Run locally with DuckDB or in production with Databricks
2. **Security**: Never commit secrets to version control
3. **Simplicity**: Easy for developers to configure locally
4. **Production-Ready**: Works with Kubernetes secrets and cloud secret managers
5. **Type Safety**: Catch configuration errors early
6. **Validation**: Ensure required configuration is present

### Alternatives Considered

1. **Environment Variables**
   - Standard approach
   - Supported everywhere
   - Easy to inject in containers
   - No file management

2. **Configuration Files (YAML/JSON)**
   - Structured configuration
   - Easy to read and edit
   - Risk of committing secrets
   - Need file management

3. **Hardcoded Configuration**
   - Simplest approach
   - No external dependencies
   - Secrets in code (security risk)
   - Different code per environment

4. **Configuration Service (e.g., Consul)**
   - Centralized configuration
   - Dynamic updates
   - Additional infrastructure
   - Complexity overhead

## Decision

We will use **environment variables** as the primary configuration mechanism, with a Python dataclass wrapper for type safety and validation.

## Rationale

### Environment Variables as Source of Truth


Environment variables are the standard for configuration because:

1. **Universal Support**: Every platform supports them
2. **Container-Friendly**: Easy to inject in Docker/Kubernetes
3. **Secret Management**: Integrate with secret managers
4. **No Files**: No risk of committing secrets
5. **12-Factor App**: Follows industry best practices

### Python Dataclass Wrapper

We wrap environment variables in a typed dataclass:

```python
from dataclasses import dataclass
import os

@dataclass
class DataPlatformConfig:
    """Configuration loaded from environment variables"""
    
    environment: str
    database_type: str
    output_path: str
    duckdb_path: str
    databricks_host: str | None
    databricks_token: str | None
    
    @classmethod
    def from_env(cls) -> "DataPlatformConfig":
        """Load configuration from environment variables"""
        return cls(
            environment=os.getenv("ENVIRONMENT", "dev"),
            database_type=os.getenv("DATABASE_TYPE", "duckdb"),
            output_path=os.getenv("OUTPUT_PATH", "data/outputs"),
            duckdb_path=os.getenv("DUCKDB_PATH", "data/duckdb/lending_club.duckdb"),
            databricks_host=os.getenv("DATABRICKS_HOST"),
            databricks_token=os.getenv("DATABRICKS_TOKEN"),
        )
    
    def validate(self):
        """Validate configuration"""
        if self.database_type == "databricks":
            if not self.databricks_host or not self.databricks_token:
                raise ValueError("Databricks credentials required")
```

**Benefits**:
- Type hints for IDE support
- Validation at startup
- Default values for development
- Easy to test (mock the dataclass)
- Self-documenting

### .env File for Local Development

For local development, we use a `.env` file:

```bash
# .env (not committed to Git)
ENVIRONMENT=dev
DATABASE_TYPE=duckdb
DUCKDB_PATH=data/duckdb/lending_club.duckdb
OUTPUT_PATH=data/outputs
```

With `.env.example` committed to Git:

```bash
# .env.example (committed to Git)
ENVIRONMENT=dev
DATABASE_TYPE=duckdb
DUCKDB_PATH=data/duckdb/lending_club.duckdb
OUTPUT_PATH=data/outputs

# Production settings (uncomment and configure)
# DATABASE_TYPE=databricks
# DATABRICKS_HOST=your-workspace.cloud.databricks.com
# DATABRICKS_TOKEN=your-token-here
```

**Benefits**:
- Easy local setup (copy .env.example to .env)
- No secrets in Git (.env in .gitignore)
- Clear documentation of required variables
- Works with Docker Compose

### Environment-Specific Behavior

The same code adapts to different environments:

```python
# Resource factory pattern
def get_database_resource(config: DataPlatformConfig):
    """Return appropriate database resource based on config"""
    if config.database_type == "duckdb":
        return DuckDBResource(path=config.duckdb_path)
    elif config.database_type == "databricks":
        return DatabricksResource(
            host=config.databricks_host,
            token=config.databricks_token
        )
    else:
        raise ValueError(f"Unknown database type: {config.database_type}")
```

**Benefits**:
- Zero code changes between environments
- Single codebase for all environments
- Easy to add new environments
- Testable with different configs

### Production Deployment

In production (Kubernetes), secrets come from secret managers:

```yaml
# Kubernetes deployment
apiVersion: apps/v1
kind: Deployment
spec:
  containers:
  - name: dagster-user-code
    env:
    - name: ENVIRONMENT
      value: "prod"
    - name: DATABASE_TYPE
      value: "databricks"
    - name: DATABRICKS_HOST
      valueFrom:
        secretKeyRef:
          name: databricks-credentials
          key: host
    - name: DATABRICKS_TOKEN
      valueFrom:
        secretKeyRef:
          name: databricks-credentials
          key: token
```

**Benefits**:
- Secrets managed by Kubernetes
- No secrets in container images
- Easy rotation of credentials
- Audit logging of secret access

## Implementation

### Configuration Structure

```python
# src/lending_club_pipeline/resources/config.py

from dataclasses import dataclass
import os
from typing import Optional

@dataclass
class DataPlatformConfig:
    """
    Configuration for the data platform.
    
    All values loaded from environment variables.
    """
    
    # Environment
    environment: str  # dev, staging, prod
    
    # Database
    database_type: str  # duckdb, databricks
    duckdb_path: Optional[str] = None
    
    # Databricks
    databricks_host: Optional[str] = None
    databricks_token: Optional[str] = None
    databricks_catalog: Optional[str] = None
    databricks_schema: Optional[str] = None
    
    # DBT
    dbt_target: str = "dev"
    dbt_profiles_dir: str = "dbt_project"
    
    # Paths
    output_path: str = "data/outputs"
    input_path: str = "data/inputs"
    
    @classmethod
    def from_env(cls) -> "DataPlatformConfig":
        """Load configuration from environment variables"""
        config = cls(
            environment=os.getenv("ENVIRONMENT", "dev"),
            database_type=os.getenv("DATABASE_TYPE", "duckdb"),
            duckdb_path=os.getenv("DUCKDB_PATH"),
            databricks_host=os.getenv("DATABRICKS_HOST"),
            databricks_token=os.getenv("DATABRICKS_TOKEN"),
            databricks_catalog=os.getenv("DATABRICKS_CATALOG"),
            databricks_schema=os.getenv("DATABRICKS_SCHEMA"),
            dbt_target=os.getenv("DBT_TARGET", "dev"),
            dbt_profiles_dir=os.getenv("DBT_PROFILES_DIR", "dbt_project"),
            output_path=os.getenv("OUTPUT_PATH", "data/outputs"),
            input_path=os.getenv("INPUT_PATH", "data/inputs"),
        )
        
        config.validate()
        return config
    
    def validate(self):
        """Validate configuration"""
        # Validate environment
        valid_environments = ["dev", "staging", "prod"]
        if self.environment not in valid_environments:
            raise ValueError(
                f"Invalid environment: {self.environment}. "
                f"Must be one of {valid_environments}"
            )
        
        # Validate database type
        valid_db_types = ["duckdb", "databricks"]
        if self.database_type not in valid_db_types:
            raise ValueError(
                f"Invalid database type: {self.database_type}. "
                f"Must be one of {valid_db_types}"
            )
        
        # Validate database-specific config
        if self.database_type == "duckdb":
            if not self.duckdb_path:
                raise ValueError("DUCKDB_PATH required when DATABASE_TYPE=duckdb")
        
        if self.database_type == "databricks":
            required = ["databricks_host", "databricks_token", 
                       "databricks_catalog", "databricks_schema"]
            missing = [f for f in required if not getattr(self, f)]
            if missing:
                raise ValueError(
                    f"Missing required Databricks config: {missing}"
                )
    
    def is_production(self) -> bool:
        """Check if running in production"""
        return self.environment == "prod"
    
    def is_local(self) -> bool:
        """Check if running locally"""
        return self.database_type == "duckdb"
```

### Usage in Dagster

```python
# src/lending_club_pipeline/definitions.py

from dagster import Definitions
from .resources.config import DataPlatformConfig
from .resources.database_factory import get_database_resource

# Load configuration
config = DataPlatformConfig.from_env()

# Create resources based on config
database = get_database_resource(config)

# Define Dagster definitions
defs = Definitions(
    assets=[...],
    resources={
        "config": config,
        "database": database,
    }
)
```

### Environment Files

**.env.example** (committed to Git):
```bash
# Environment Configuration
ENVIRONMENT=dev

# Database Configuration
DATABASE_TYPE=duckdb
DUCKDB_PATH=data/duckdb/lending_club.duckdb

# DBT Configuration
DBT_TARGET=dev
DBT_PROFILES_DIR=dbt_project

# Path Configuration
INPUT_PATH=data/inputs
OUTPUT_PATH=data/outputs

# Dagster Configuration
DAGSTER_HOME=/opt/dagster/dagster_home

# Production Databricks Configuration (uncomment for prod)
# DATABASE_TYPE=databricks
# DATABRICKS_HOST=your-workspace.cloud.databricks.com
# DATABRICKS_TOKEN=your-token-here
# DATABRICKS_CATALOG=main
# DATABRICKS_SCHEMA=lending_club
# DBT_TARGET=prod
```

**.gitignore**:
```
# Environment files
.env
.env.local
.env.*.local

# Never commit these
*.key
*.pem
credentials.json
```

## Consequences

### Positive

1. **Security**: Secrets never in source code
2. **Flexibility**: Same code runs everywhere
3. **Simplicity**: Standard approach, easy to understand
4. **Type Safety**: Dataclass provides type hints
5. **Validation**: Catch config errors at startup
6. **Documentation**: .env.example documents required variables
7. **Testing**: Easy to mock configuration
8. **Production-Ready**: Works with Kubernetes secrets

### Negative

1. **Environment Variables**: Can be verbose for complex config
2. **No Hierarchy**: Flat structure, no nested configuration
3. **String Types**: All env vars are strings (need parsing)
4. **Discovery**: Need to know variable names

### Neutral

1. **Validation**: Need to write validation logic
2. **Defaults**: Need to decide appropriate defaults
3. **Documentation**: Need to maintain .env.example

## Validation

Success criteria:
- ✅ Configuration loads from environment variables
- ✅ Validation catches missing required variables
- ✅ Same code runs with DuckDB and Databricks
- ✅ No secrets in Git repository
- ✅ .env.example documents all variables
- ✅ Type hints work in IDE

## Security Considerations

### What Goes in .env.example

✅ **Safe to commit**:
- Variable names
- Default values for development
- Example values (not real credentials)
- Documentation comments

❌ **Never commit**:
- Real credentials
- API tokens
- Database passwords
- Private keys

### Secret Rotation

When rotating secrets:
1. Update secret in secret manager (Kubernetes/AWS/etc.)
2. Restart services to pick up new values
3. No code changes required

### Audit Trail

- Environment variables logged at startup (excluding secrets)
- Configuration validation errors logged
- Secret access logged by secret manager

## Testing Strategy

### Unit Tests

```python
def test_config_validation():
    """Test configuration validation"""
    # Valid config
    config = DataPlatformConfig(
        environment="dev",
        database_type="duckdb",
        duckdb_path="test.db"
    )
    config.validate()  # Should not raise
    
    # Invalid environment
    config = DataPlatformConfig(
        environment="invalid",
        database_type="duckdb"
    )
    with pytest.raises(ValueError):
        config.validate()
```

### Integration Tests

```python
def test_config_from_env(monkeypatch):
    """Test loading config from environment"""
    monkeypatch.setenv("ENVIRONMENT", "dev")
    monkeypatch.setenv("DATABASE_TYPE", "duckdb")
    monkeypatch.setenv("DUCKDB_PATH", "test.db")
    
    config = DataPlatformConfig.from_env()
    assert config.environment == "dev"
    assert config.database_type == "duckdb"
```

## Migration Path

### From Hardcoded Config

1. Extract hardcoded values to environment variables
2. Create DataPlatformConfig class
3. Update code to use config object
4. Create .env.example
5. Update documentation

### From Config Files

1. Read config file values into environment variables
2. Gradually migrate to environment-only
3. Remove config files
4. Update deployment scripts

## Future Enhancements

1. **Config Validation Library**: Use Pydantic for advanced validation
2. **Config Reloading**: Support dynamic config updates
3. **Config Versioning**: Track config changes over time
4. **Config Templates**: Environment-specific templates
5. **Config UI**: Web interface for config management

## References

- [12-Factor App: Config](https://12factor.net/config)
- [Kubernetes Secrets](https://kubernetes.io/docs/concepts/configuration/secret/)
- [Python Dataclasses](https://docs.python.org/3/library/dataclasses.html)
- [Environment Variables Best Practices](https://blog.doppler.com/environment-variables-best-practices)

## Notes

- Decision made: 2024-10-15
- Last updated: 2024-10-30
- Reviewers: Data Engineering Team, Security Team
- Status: Implemented and validated
- Related ADRs: ADR-001 (Dagster), ADR-002 (DBT)
