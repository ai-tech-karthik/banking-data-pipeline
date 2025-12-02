# ADR 001: Dagster for Orchestration

## Status

Accepted

## Context

We need an orchestration framework to manage the data pipeline that:
- Handles dependencies between data transformations
- Provides visibility into data lineage
- Supports local development and production deployment
- Integrates well with DBT for SQL transformations
- Offers modern development experience with Python

### Alternatives Considered

1. **Apache Airflow**
   - Most popular orchestration tool
   - Task-centric model (DAGs)
   - Large community and ecosystem
   - Mature and battle-tested

2. **Prefect**
   - Modern Python-first orchestration
   - Hybrid execution model
   - Good developer experience
   - Growing community

3. **Dagster**
   - Asset-centric model (focus on data products)
   - Excellent DBT integration
   - Built-in data quality checks
   - Modern Python API with type hints

4. **Custom Scripts**
   - Simple bash/Python scripts
   - No external dependencies
   - Full control over execution

## Decision

We will use **Dagster** as the orchestration framework for the LendingClub Data Pipeline.

## Rationale

### Asset-Centric Model

Dagster's asset-centric approach aligns perfectly with our data pipeline needs:

```python
@asset
def customers_cleaned(customers_raw):
    """Focus on the data product, not the task"""
    return clean_customers(customers_raw)
```

Benefits:
- Think in terms of data products, not tasks
- Automatic dependency resolution based on data flow
- Clear lineage visualization
- Better mental model for data pipelines

### Superior DBT Integration

Dagster provides first-class DBT integration via `@dbt_assets`:

```python
@dbt_assets(manifest=dbt_manifest)
def dbt_transformations(context):
    """Automatically maps DBT models to Dagster assets"""
    yield from dbt.run(context=context)
```

Benefits:
- Automatic asset creation from DBT models
- Dependency tracking via DBT ref() calls
- Unified lineage across Dagster and DBT
- Single UI for all data assets

### Excellent Local Development Experience

```bash
dagster dev
```

Benefits:
- Hot-reload for code changes
- Interactive UI at localhost:3000
- Easy debugging with Python debugger
- No complex setup required

### Built-in Data Quality

```python
@asset_check(asset=customers_cleaned)
def check_no_null_ids(asset_value):
    """Built-in data quality checks"""
    assert asset_value['customer_id'].notna().all()
```

Benefits:
- Asset checks as first-class citizens
- Quality gates in the pipeline
- Visibility into data quality issues
- Integration with monitoring

### Modern Python API

```python
@asset(
    group_name="ingestion",
    compute_kind="python",
    metadata={"owner": "data-team"}
)
def my_asset(context, upstream: pd.DataFrame) -> pd.DataFrame:
    """Type hints, decorators, modern Python"""
    context.log.info("Processing...")
    return process(upstream)
```

Benefits:
- Type hints for better IDE support
- Pythonic API design
- Easy to learn for Python developers
- Good documentation

### Comparison with Airflow

| Feature | Dagster | Airflow |
|---------|---------|---------|
| Mental Model | Assets (data products) | Tasks (operations) |
| DBT Integration | Native `@dbt_assets` | Via operators |
| Local Development | `dagster dev` | Complex setup |
| Type Safety | Full type hints | Limited |
| Data Lineage | Built-in, automatic | Manual configuration |
| Learning Curve | Moderate | Steep |
| Community | Growing | Large |

### Trade-offs

**Advantages**:
- Better fit for data pipelines (vs. general workflow orchestration)
- Superior DBT integration
- Modern development experience
- Built-in data quality features
- Clear data lineage

**Disadvantages**:
- Smaller community than Airflow
- Fewer third-party integrations
- Steeper learning curve for non-Python developers
- Less mature (but rapidly evolving)

## Consequences

### Positive

1. **Better Developer Experience**: Hot-reload, type hints, modern API
2. **Unified Lineage**: Single view of Dagster assets and DBT models
3. **Data Quality**: Built-in checks and validation
4. **Maintainability**: Asset-centric model easier to understand and modify
5. **Testing**: Easy to test assets in isolation

### Negative

1. **Learning Curve**: Team needs to learn Dagster concepts
2. **Community**: Smaller community means fewer resources
3. **Integrations**: May need to build custom integrations
4. **Migration**: Harder to migrate to other orchestrators later

### Neutral

1. **Documentation**: Need to document Dagster patterns for team
2. **Training**: Team training required
3. **Monitoring**: Need to set up Dagster-specific monitoring

## Implementation

### Phase 1: Setup (Completed)
- Install Dagster and dependencies
- Configure Docker Compose for local development
- Set up Dagster workspace

### Phase 2: Asset Development (Completed)
- Create ingestion assets
- Integrate DBT models as assets
- Create output assets

### Phase 3: Production Deployment (Future)
- Deploy to Kubernetes using Dagster Helm chart
- Configure production resources (Databricks)
- Set up monitoring and alerting

## Validation

Success criteria:
- ✅ All assets visible in Dagster UI
- ✅ Lineage graph shows complete data flow
- ✅ DBT models automatically mapped to assets
- ✅ Local development with hot-reload works
- ✅ Asset materialization succeeds end-to-end

## References

- [Dagster Documentation](https://docs.dagster.io)
- [Dagster vs Airflow](https://dagster.io/blog/dagster-airflow)
- [Asset-Centric Orchestration](https://dagster.io/blog/software-defined-assets)
- [DBT Integration Guide](https://docs.dagster.io/integrations/dbt)

## Notes

- Decision made: 2024-10-15
- Last updated: 2024-10-30
- Reviewers: Data Engineering Team
- Status: Implemented and validated
