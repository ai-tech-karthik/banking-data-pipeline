#!/usr/bin/env python3
"""
Test Databricks connection and configuration.
This script validates that you can connect to Databricks with the provided credentials.
"""

import os
import sys
from pathlib import Path

# Add parent directory to path to import from src
sys.path.insert(0, str(Path(__file__).parent.parent))


def test_databricks_connection():
    """Test connection to Databricks."""
    print("=" * 60)
    print("Databricks Connection Test")
    print("=" * 60)
    print()
    
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()
    
    # Get Databricks configuration
    host = os.getenv("DATABRICKS_HOST")
    token = os.getenv("DATABRICKS_TOKEN")
    http_path = os.getenv("DATABRICKS_HTTP_PATH")
    catalog = os.getenv("DATABRICKS_CATALOG", "hive_metastore")
    schema = os.getenv("DATABRICKS_SCHEMA", "default")
    
    print("Configuration:")
    print(f"  Host: {host}")
    print(f"  Token: {'*' * 20 if token else 'NOT SET'}")
    print(f"  HTTP Path: {http_path}")
    print(f"  Catalog: {catalog}")
    print(f"  Schema: {schema}")
    print()
    
    # Check if required fields are set
    if not host:
        print("❌ DATABRICKS_HOST is not set in .env file")
        return False
    
    if not token:
        print("❌ DATABRICKS_TOKEN is not set in .env file")
        print()
        print("To generate a token:")
        print("  1. Log into Databricks")
        print("  2. Click your username → User Settings")
        print("  3. Go to Developer → Access tokens")
        print("  4. Click 'Generate new token'")
        print("  5. Copy the token and add it to .env file")
        return False
    
    if not http_path:
        print("❌ DATABRICKS_HTTP_PATH is not set in .env file")
        print()
        print("To get the HTTP path:")
        print("  1. Go to SQL Warehouses in Databricks")
        print("  2. Click on your warehouse")
        print("  3. Go to Connection Details tab")
        print("  4. Copy the HTTP Path")
        return False
    
    # Try to connect
    print("Testing connection...")
    try:
        from databricks import sql
        
        connection = sql.connect(
            server_hostname=host,
            http_path=http_path,
            access_token=token
        )
        
        print("✅ Successfully connected to Databricks!")
        print()
        
        # Test a simple query
        print("Running test query...")
        cursor = connection.cursor()
        
        try:
            cursor.execute("SELECT current_database(), current_user()")
            result = cursor.fetchone()
            print(f"✅ Query successful!")
            print(f"  Current database: {result[0]}")
            print(f"  Current user: {result[1]}")
            print()
        except Exception as e:
            print(f"⚠️  Query failed: {e}")
            print()
        
        # Check if schema exists
        print(f"Checking if schema '{catalog}.{schema}' exists...")
        try:
            cursor.execute(f"USE CATALOG {catalog}")
            cursor.execute(f"SHOW SCHEMAS LIKE '{schema}'")
            schemas = cursor.fetchall()
            
            if schemas:
                print(f"✅ Schema '{catalog}.{schema}' exists")
            else:
                print(f"⚠️  Schema '{catalog}.{schema}' does not exist")
                print(f"   Creating schema...")
                try:
                    cursor.execute(f"CREATE SCHEMA IF NOT EXISTS {catalog}.{schema}")
                    print(f"✅ Created schema '{catalog}.{schema}'")
                except Exception as e:
                    print(f"❌ Failed to create schema: {e}")
        except Exception as e:
            print(f"⚠️  Could not check schema: {e}")
            print(f"   Note: Community Edition uses 'hive_metastore' catalog")
        
        cursor.close()
        connection.close()
        
        print()
        print("=" * 60)
        print("✅ Databricks connection test PASSED")
        print("=" * 60)
        print()
        print("Next steps:")
        print("  1. Update .env file with DATABASE_TYPE=databricks")
        print("  2. Update .env file with DBT_TARGET=prod")
        print("  3. Restart Docker services: docker-compose restart")
        print("  4. Materialize assets in Dagster UI")
        return True
        
    except ImportError:
        print("❌ databricks-sql-connector not installed")
        print()
        print("Install it with:")
        print("  pip install databricks-sql-connector")
        return False
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        print()
        print("Common issues:")
        print("  - Check that your token is valid")
        print("  - Verify the HTTP path is correct")
        print("  - Ensure your SQL Warehouse is running")
        print("  - Check network connectivity")
        return False


if __name__ == "__main__":
    success = test_databricks_connection()
    sys.exit(0 if success else 1)
