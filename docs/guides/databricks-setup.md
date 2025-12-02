# Databricks Setup Guide

This guide walks you through setting up Databricks integration for the LendingClub Pipeline.

## Prerequisites

- Databricks account (Community Edition or paid tier)
- SQL Warehouse created in Databricks
- Access to generate personal access tokens

## Step 1: Generate Personal Access Token

1. Log into your Databricks workspace
2. Click on your **username** in the top right corner
3. Select **User Settings**
4. Navigate to **Developer** → **Access tokens**
5. Click **Generate new token**
6. Provide a comment (e.g., "dagster-pipeline")
7. Set lifetime (optional - leave blank for no expiration)
8. Click **Generate**
9. **Copy the token immediately** (you won't be able to see it again!)

## Step 2: Get SQL Warehouse HTTP Path

1. In Databricks, click **SQL Warehouses** in the left sidebar
2. If you don't have a warehouse:
   - Click **Create SQL Warehouse**
   - Choose the smallest size for testing
   - Click **Create**
3. Click on your SQL Warehouse name
4. Go to the **Connection Details** tab
5. Copy the **HTTP Path** (format: `/sql/1.0/warehouses/xxxxx`)

## Step 3: Determine Catalog and Schema

### For Databricks Community Edition:
- **Catalog**: `hive_metastore` (default, no Unity Catalog support)
- **Schema**: `default` or create a custom schema like `lending_club`

### For Databricks Paid Tiers with Unity Catalog:
- **Catalog**: Your Unity Catalog name (e.g., `main`, `dev`, `prod`)
- **Schema**: Your schema name (e.g., `lending_club`, `analytics`)

## Step 4: Update .env File

Edit your `.env` file and update the Databricks section:

```bash
# Databricks Configuration
DATABRICKS_HOST=dbc-4125f268-cbe4.cloud.databricks.com
DATABRICKS_TOKEN=dapi1234567890abcdef...  # Your generated token
DATABRICKS_CATALOG=hive_metastore          # Or your Unity Catalog name
DATABRICKS_SCHEMA=default                  # Or your custom schema
DATABRICKS_HTTP_PATH=/sql/1.0/warehouses/abc123def456  # Your warehouse HTTP path
```

## Step 5: Test Connection

Run the connection test script:

```bash
python3 scripts/test_databricks_connection.py
```

This script will:
- Validate your credentials
- Test the connection
- Check if the schema exists
- Create the schema if needed
- Run a test query

Expected output:
```
✅ Successfully connected to Databricks!
✅ Query successful!
✅ Schema 'hive_metastore.default' exists
✅ Databricks connection test PASSED
```

## Step 6: Switch to Databricks Mode

Once the connection test passes, update your `.env` file to use Databricks:

```bash
# Change these values:
DATABASE_TYPE=databricks
DBT_TARGET=prod
```

## Step 7: Update DBT Profiles

The pipeline automatically configures DBT based on the `DBT_TARGET` setting:
- `dev` → Uses DuckDB locally
- `prod` → Uses Databricks

No manual DBT configuration needed!

## Step 8: Restart Docker Services

```bash
docker-compose restart
```

Wait for services to be healthy:
```bash
docker-compose ps
```

## Step 9: Test the Pipeline

1. Open Dagster UI: http://localhost:3000
2. Go to **Assets** tab
3. Click **Materialize all**

The pipeline will now:
1. ✅ Ingest data to DuckDB (local staging)
2. ✅ Run DBT transformations
3. ✅ Export to CSV and Parquet
4. ✅ Load data to Databricks Delta table

## Step 10: Verify in Databricks

1. Go to your Databricks workspace
2. Click **SQL Editor** or **Data Explorer**
3. Navigate to your catalog and schema
4. You should see the `account_summary` table
5. Run a query to verify:

```sql
SELECT * FROM hive_metastore.default.account_summary LIMIT 10;
```

## Troubleshooting

### Connection Fails

**Issue**: "Could not connect to Databricks"

**Solutions**:
- Verify your token is correct and not expired
- Check that the HTTP path matches your SQL Warehouse
- Ensure your SQL Warehouse is **running** (not stopped)
- Check network connectivity

### Schema Not Found

**Issue**: "Schema does not exist"

**Solutions**:
- For Community Edition, use `hive_metastore.default`
- Create the schema manually in Databricks:
  ```sql
  CREATE SCHEMA IF NOT EXISTS hive_metastore.lending_club;
  ```
- Update `.env` with the correct schema name

### Permission Denied

**Issue**: "User does not have permission"

**Solutions**:
- Ensure your token has the necessary permissions
- In Databricks, go to **Admin Console** → **Users**
- Verify your user has **Can Use** permission on the SQL Warehouse
- Verify your user has **Can Create** permission on the schema

### Table Already Exists

**Issue**: "Table already exists" error

**Solutions**:
- The pipeline uses `TRUNCATE` and `INSERT` to overwrite data
- If you get errors, manually drop the table:
  ```sql
  DROP TABLE IF EXISTS hive_metastore.default.account_summary;
  ```
- Re-run the pipeline

### Community Edition Limitations

**Note**: Databricks Community Edition has some limitations:
- No Unity Catalog (use `hive_metastore`)
- Single user access
- Limited compute resources
- No job scheduling
- Tables are stored in DBFS

For production use, consider upgrading to a paid tier.

## Architecture Notes

### Hybrid Approach

The pipeline uses a hybrid architecture:
1. **Ingestion**: Data is loaded into DuckDB (fast local storage)
2. **Transformation**: DBT runs transformations in DuckDB
3. **Output**: Final results are exported to:
   - Local files (CSV, Parquet)
   - Databricks (for enterprise consumption)

### Why This Approach?

- **Fast Development**: DuckDB is fast for local development
- **Cost Effective**: Minimize Databricks compute usage
- **Flexible**: Can run entirely locally or push to Databricks
- **Scalable**: Easy to switch between environments

### Data Flow

```
CSV Files → DuckDB → DBT Transformations → DuckDB → Outputs
                                                      ├─ CSV
                                                      ├─ Parquet
                                                      └─ Databricks
```

## Next Steps

After successful Databricks integration:

1. **Schedule Pipeline**: Set up Dagster schedules for automated runs
2. **Monitor**: Use Dagster UI to monitor pipeline execution
3. **BI Tools**: Connect Tableau, Power BI, or other tools to Databricks
4. **Expand**: Add more data sources and transformations
5. **Production**: Deploy to a production Databricks workspace

## Additional Resources

- [Databricks SQL Connector Documentation](https://docs.databricks.com/dev-tools/python-sql-connector.html)
- [DBT Databricks Adapter](https://docs.getdbt.com/reference/warehouse-setups/databricks-setup)
- [Dagster Databricks Integration](https://docs.dagster.io/integrations/databricks)
- [Unity Catalog Documentation](https://docs.databricks.com/data-governance/unity-catalog/index.html)

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Review Dagster logs: `docker-compose logs`
3. Check Databricks query history for errors
4. Review the validation scripts output
