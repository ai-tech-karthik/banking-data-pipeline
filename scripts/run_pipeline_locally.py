#!/usr/bin/env python3
"""
Script to run the full LendingClub pipeline locally.

This script materializes all assets in the pipeline from ingestion through
transformations to outputs.
"""
import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from dagster import materialize, AssetSelection
from lending_club_pipeline.definitions import defs


def main():
    """Run the full pipeline locally."""
    print("=" * 60)
    print("Running LendingClub Data Pipeline Locally")
    print("=" * 60)
    print()
    
    # Set environment variables for local execution
    # Use absolute paths to avoid issues with DBT working directory
    workspace_root = Path(__file__).parent.parent
    os.environ.setdefault("DATABASE_TYPE", "duckdb")
    os.environ.setdefault("DBT_TARGET", "dev")
    os.environ.setdefault("DUCKDB_PATH", str(workspace_root / "data/duckdb/lending_club.duckdb"))
    os.environ.setdefault("OUTPUT_PATH", str(workspace_root / "data/outputs"))
    
    print("Environment Configuration:")
    print(f"  DATABASE_TYPE: {os.environ['DATABASE_TYPE']}")
    print(f"  DBT_TARGET: {os.environ['DBT_TARGET']}")
    print(f"  DUCKDB_PATH: {os.environ['DUCKDB_PATH']}")
    print(f"  OUTPUT_PATH: {os.environ['OUTPUT_PATH']}")
    print()
    
    # Ensure data directories exist
    Path("data/duckdb").mkdir(parents=True, exist_ok=True)
    Path("data/outputs").mkdir(parents=True, exist_ok=True)
    
    # Check if input files exist
    input_files = [
        "data/inputs/Customer.csv",
        "data/inputs/accounts.csv"
    ]
    
    print("Checking input files...")
    missing_files = []
    for file_path in input_files:
        if Path(file_path).exists():
            print(f"  ✓ {file_path}")
        else:
            print(f"  ✗ {file_path} (MISSING)")
            missing_files.append(file_path)
    print()
    
    if missing_files:
        print("ERROR: Missing input files. Please ensure the following files exist:")
        for file_path in missing_files:
            print(f"  - {file_path}")
        print()
        print("You can create sample files by running:")
        print("  python scripts/create_sample_data.py")
        sys.exit(1)
    
    # Get all assets (excluding Databricks output for local execution)
    print("Materializing all assets...")
    print()
    
    try:
        # Get all assets from definitions and filter out Databricks output
        from lending_club_pipeline.assets.ingestion import customers_raw, accounts_raw
        from lending_club_pipeline.assets.dbt_assets import dbt_transformations
        from lending_club_pipeline.assets.outputs import account_summary_csv, account_summary_parquet
        
        all_assets = [
            customers_raw,
            accounts_raw,
            dbt_transformations,
            account_summary_csv,
            account_summary_parquet,
        ]
        
        # Materialize all assets except Databricks output
        result = materialize(
            all_assets,
            resources=defs.resources,
        )
        
        print()
        print("=" * 60)
        if result.success:
            print("✓ Pipeline execution completed successfully!")
            print("=" * 60)
            print()
            print("Output files created:")
            print(f"  - data/outputs/account_summary.csv")
            print(f"  - data/outputs/account_summary.parquet")
            print()
            # Count materialized assets from events
            materialization_count = sum(1 for event in result.all_events if event.event_type_value == "ASSET_MATERIALIZATION")
            print(f"Total assets materialized: {materialization_count}")
            print()
            return 0
        else:
            print("✗ Pipeline execution failed!")
            print("=" * 60)
            return 1
            
    except Exception as e:
        print()
        print("=" * 60)
        print("✗ Pipeline execution failed with error:")
        print("=" * 60)
        print(f"{type(e).__name__}: {str(e)}")
        print()
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
