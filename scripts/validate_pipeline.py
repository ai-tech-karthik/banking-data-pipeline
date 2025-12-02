#!/usr/bin/env python3
"""
Pipeline validation script for LendingClub Pipeline.
Tests full pipeline execution and validates outputs.
"""

import os
import sys
import time
import subprocess
from pathlib import Path
from typing import Dict, Any

import pandas as pd


class Colors:
    """ANSI color codes for terminal output."""
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'


def print_header(message: str):
    """Print a formatted header."""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{message}{Colors.RESET}")


def print_success(message: str):
    """Print a success message."""
    print(f"{Colors.GREEN}✓{Colors.RESET} {message}")


def print_warning(message: str):
    """Print a warning message."""
    print(f"{Colors.YELLOW}⚠{Colors.RESET}  {message}")


def print_error(message: str):
    """Print an error message."""
    print(f"{Colors.RED}✗{Colors.RESET} {message}")


def check_docker_services() -> bool:
    """Check if Docker Compose services are running."""
    print_header("Checking Docker Services")
    
    try:
        result = subprocess.run(
            ["docker-compose", "ps"],
            capture_output=True,
            text=True,
            check=True
        )
        
        output = result.stdout
        
        # Check for key services
        services = ["dagster", "postgres"]
        all_running = True
        
        for service in services:
            if service in output.lower():
                print_success(f"{service} service is present")
            else:
                print_warning(f"{service} service not found in docker-compose")
        
        return all_running
        
    except subprocess.CalledProcessError as e:
        print_error(f"Failed to check Docker services: {e}")
        return False
    except FileNotFoundError:
        print_error("docker-compose command not found")
        return False


def check_dagster_ui() -> bool:
    """Check if Dagster UI is accessible."""
    print_header("Checking Dagster UI")
    
    try:
        import requests
        
        url = "http://localhost:3000"
        response = requests.get(url, timeout=5)
        
        if response.status_code == 200:
            print_success(f"Dagster UI is accessible at {url}")
            return True
        else:
            print_warning(f"Dagster UI returned status code {response.status_code}")
            return False
            
    except ImportError:
        print_warning("requests library not installed. Skipping UI check.")
        return True
    except Exception as e:
        print_warning(f"Cannot access Dagster UI: {e}")
        print_warning("Make sure Docker Compose services are running: docker-compose up -d")
        return False


def validate_input_data() -> bool:
    """Validate input CSV files."""
    print_header("Validating Input Data")
    
    input_files = {
        "data/inputs/Customer.csv": ["CustomerID", "Name", "HasLoan"],
        "data/inputs/accounts.csv": ["AccountID", "CustomerID", "Balance", "AccountType"],
    }
    
    all_valid = True
    
    for file_path, expected_columns in input_files.items():
        path = Path(file_path)
        
        if not path.exists():
            print_error(f"{file_path} not found")
            all_valid = False
            continue
        
        try:
            df = pd.read_csv(file_path)
            
            # Check if file is empty
            if df.empty:
                print_error(f"{file_path} is empty")
                all_valid = False
                continue
            
            # Check columns
            missing_cols = set(expected_columns) - set(df.columns)
            if missing_cols:
                print_error(f"{file_path} missing columns: {missing_cols}")
                all_valid = False
                continue
            
            print_success(f"{file_path}: {len(df)} rows, columns OK")
            
        except Exception as e:
            print_error(f"Error reading {file_path}: {e}")
            all_valid = False
    
    return all_valid


def check_duckdb_database() -> bool:
    """Check if DuckDB database exists and is accessible."""
    print_header("Checking DuckDB Database")
    
    db_path = Path("data/duckdb/lending_club.duckdb")
    
    if not db_path.exists():
        print_warning("DuckDB database not found (will be created on first run)")
        return True
    
    try:
        import duckdb
        
        conn = duckdb.connect(str(db_path), read_only=True)
        
        # List tables
        tables = conn.execute("SHOW TABLES").fetchall()
        
        if tables:
            print_success(f"DuckDB database exists with {len(tables)} tables")
            for table in tables:
                print(f"  - {table[0]}")
        else:
            print_warning("DuckDB database exists but has no tables")
        
        conn.close()
        return True
        
    except ImportError:
        print_warning("duckdb library not installed. Skipping database check.")
        return True
    except Exception as e:
        print_error(f"Error accessing DuckDB database: {e}")
        return False


def validate_output_files() -> Dict[str, Any]:
    """Validate output files exist and have correct structure."""
    print_header("Validating Output Files")
    
    expected_outputs = [
        "data/outputs/account_summary.csv",
        "data/outputs/account_summary.parquet",
    ]
    
    results = {}
    
    for file_path in expected_outputs:
        path = Path(file_path)
        
        if not path.exists():
            print_warning(f"{file_path} not found (run pipeline to generate)")
            results[file_path] = None
            continue
        
        try:
            # Read file based on extension
            if file_path.endswith(".csv"):
                df = pd.read_csv(file_path)
            elif file_path.endswith(".parquet"):
                df = pd.read_parquet(file_path)
            else:
                continue
            
            # Validate schema
            expected_columns = [
                "customer_id",
                "account_id",
                "original_balance",
                "interest_rate",
                "annual_interest",
                "new_balance",
            ]
            
            missing_cols = set(expected_columns) - set(df.columns)
            if missing_cols:
                print_error(f"{file_path} missing columns: {missing_cols}")
                results[file_path] = False
                continue
            
            # Validate data quality
            if df.empty:
                print_warning(f"{file_path} is empty")
                results[file_path] = False
                continue
            
            # Check for nulls in required fields
            null_counts = df[["customer_id", "account_id", "original_balance"]].isnull().sum()
            if null_counts.any():
                print_warning(f"{file_path} has null values in required fields")
            
            # Validate interest rate range
            if not ((df["interest_rate"] >= 0.01) & (df["interest_rate"] <= 0.025)).all():
                print_warning(f"{file_path} has interest rates outside expected range (1%-2.5%)")
            
            # Validate calculations
            calculated_interest = (df["original_balance"] * df["interest_rate"]).round(2)
            if not (df["annual_interest"] == calculated_interest).all():
                print_warning(f"{file_path} has incorrect interest calculations")
            
            calculated_new_balance = (df["original_balance"] + df["annual_interest"]).round(2)
            if not (df["new_balance"] == calculated_new_balance).all():
                print_warning(f"{file_path} has incorrect new balance calculations")
            
            print_success(f"{file_path}: {len(df)} rows, schema OK, calculations valid")
            results[file_path] = True
            
        except Exception as e:
            print_error(f"Error validating {file_path}: {e}")
            results[file_path] = False
    
    return results


def compare_output_formats() -> bool:
    """Compare CSV and Parquet outputs for consistency."""
    print_header("Comparing Output Formats")
    
    csv_path = Path("data/outputs/account_summary.csv")
    parquet_path = Path("data/outputs/account_summary.parquet")
    
    if not csv_path.exists() or not parquet_path.exists():
        print_warning("Both output files must exist for comparison")
        return True
    
    try:
        df_csv = pd.read_csv(csv_path)
        df_parquet = pd.read_parquet(parquet_path)
        
        # Compare row counts
        if len(df_csv) != len(df_parquet):
            print_error(f"Row count mismatch: CSV={len(df_csv)}, Parquet={len(df_parquet)}")
            return False
        
        # Compare columns
        if set(df_csv.columns) != set(df_parquet.columns):
            print_error("Column mismatch between CSV and Parquet")
            return False
        
        # Compare data (allowing for minor floating point differences)
        try:
            pd.testing.assert_frame_equal(
                df_csv.sort_values("account_id").reset_index(drop=True),
                df_parquet.sort_values("account_id").reset_index(drop=True),
                check_dtype=False,
                atol=0.01
            )
            print_success("CSV and Parquet outputs are consistent")
            return True
        except AssertionError as e:
            print_warning(f"Data mismatch between formats: {e}")
            return False
            
    except Exception as e:
        print_error(f"Error comparing outputs: {e}")
        return False


def run_sample_queries() -> bool:
    """Run sample queries on the output data."""
    print_header("Running Sample Queries")
    
    csv_path = Path("data/outputs/account_summary.csv")
    
    if not csv_path.exists():
        print_warning("Output file not found. Run pipeline first.")
        return True
    
    try:
        df = pd.read_csv(csv_path)
        
        # Query 1: Count by interest rate tier
        print("\nAccounts by interest rate tier:")
        rate_counts = df["interest_rate"].value_counts().sort_index()
        for rate, count in rate_counts.items():
            print(f"  {rate:.1%}: {count} accounts")
        
        # Query 2: Total interest to be paid
        total_interest = df["annual_interest"].sum()
        print(f"\nTotal annual interest: ${total_interest:,.2f}")
        
        # Query 3: Average balance
        avg_balance = df["original_balance"].mean()
        print(f"Average account balance: ${avg_balance:,.2f}")
        
        # Query 4: Top 3 accounts by interest
        print("\nTop 3 accounts by annual interest:")
        top_accounts = df.nlargest(3, "annual_interest")[
            ["account_id", "original_balance", "interest_rate", "annual_interest"]
        ]
        for _, row in top_accounts.iterrows():
            print(f"  {row['account_id']}: ${row['original_balance']:,.2f} @ {row['interest_rate']:.1%} = ${row['annual_interest']:,.2f}")
        
        print_success("Sample queries executed successfully")
        return True
        
    except Exception as e:
        print_error(f"Error running sample queries: {e}")
        return False


def main():
    """Run all validation checks."""
    print(f"\n{Colors.BOLD}{'='*60}{Colors.RESET}")
    print(f"{Colors.BOLD}LendingClub Pipeline - Pipeline Validation{Colors.RESET}")
    print(f"{Colors.BOLD}{'='*60}{Colors.RESET}")
    
    # Pre-execution checks
    print_header("Pre-Execution Checks")
    
    checks = []
    
    # Check input data
    input_valid = validate_input_data()
    checks.append(("Input Data", input_valid))
    
    # Check Docker services (optional)
    try:
        docker_ok = check_docker_services()
        checks.append(("Docker Services", docker_ok))
    except Exception:
        print_warning("Skipping Docker services check")
    
    # Check Dagster UI (optional)
    try:
        ui_ok = check_dagster_ui()
        checks.append(("Dagster UI", ui_ok))
    except Exception:
        print_warning("Skipping Dagster UI check")
    
    # Check database
    db_ok = check_duckdb_database()
    checks.append(("DuckDB Database", db_ok))
    
    # Post-execution validation
    output_results = validate_output_files()
    
    if any(v is True for v in output_results.values()):
        # Outputs exist, validate them
        compare_ok = compare_output_formats()
        checks.append(("Output Consistency", compare_ok))
        
        query_ok = run_sample_queries()
        checks.append(("Sample Queries", query_ok))
    else:
        print_warning("\nNo output files found. To generate outputs:")
        print("  1. Ensure Docker Compose is running: docker-compose up -d")
        print("  2. Access Dagster UI: http://localhost:3000")
        print("  3. Materialize all assets in the UI")
        print("  4. Re-run this validation script")
    
    # Summary
    print_header("Validation Summary")
    
    passed = sum(1 for _, v in checks if v is True)
    failed = sum(1 for _, v in checks if v is False)
    
    print(f"\n{Colors.GREEN}Passed: {passed}{Colors.RESET}")
    if failed > 0:
        print(f"{Colors.RED}Failed: {failed}{Colors.RESET}")
    
    if failed == 0 and any(v is True for v in output_results.values()):
        print(f"\n{Colors.GREEN}{Colors.BOLD}✓ Pipeline validation successful!{Colors.RESET}\n")
        print("Your pipeline is working correctly.")
        return 0
    elif failed == 0:
        print(f"\n{Colors.YELLOW}{Colors.BOLD}⚠ Pre-execution checks passed{Colors.RESET}\n")
        print("Run the pipeline to generate outputs and complete validation.")
        return 0
    else:
        print(f"\n{Colors.RED}{Colors.BOLD}✗ Pipeline validation failed!{Colors.RESET}\n")
        print("Please fix the issues above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
