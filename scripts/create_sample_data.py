#!/usr/bin/env python3
"""
Script to create sample input data for testing the pipeline locally.
"""
from pathlib import Path
import pandas as pd


def main():
    """Create sample CSV files for pipeline testing."""
    print("Creating sample input data...")
    print()
    
    # Create data directory
    input_dir = Path("data/inputs")
    input_dir.mkdir(parents=True, exist_ok=True)
    
    # Create sample Customer.csv
    customers_df = pd.DataFrame({
        "CustomerID": ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10"],
        "Name": [
            "Alice Smith",
            "Bob Jones",
            "Charlie Brown",
            "Diana Prince",
            "Eve Adams",
            "Frank Miller",
            "Grace Lee",
            "Henry Wilson",
            "Iris Chen",
            "Jack Taylor"
        ],
        "HasLoan": ["Yes", "No", "None", "Yes", "No", "Yes", "None", "No", "Yes", "None"]
    })
    
    customer_file = input_dir / "Customer.csv"
    customers_df.to_csv(customer_file, index=False)
    print(f"✓ Created {customer_file}")
    print(f"  Rows: {len(customers_df)}")
    print()
    
    # Create sample accounts.csv with different balance tiers
    accounts_df = pd.DataFrame({
        "AccountID": ["A001", "A002", "A003", "A004", "A005", "A006", "A007", "A008", "A009", "A010"],
        "CustomerID": ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10"],
        "Balance": [
            "5000.00",    # < 10k
            "15000.00",   # 10k-20k
            "25000.00",   # >= 20k
            "8000.00",    # < 10k
            "22000.00",   # >= 20k
            "12000.00",   # 10k-20k
            "30000.00",   # >= 20k
            "7500.00",    # < 10k
            "18000.00",   # 10k-20k
            "50000.00"    # >= 20k
        ],
        "AccountType": [
            "Savings",
            "Savings",
            "Savings",
            "Savings",
            "Savings",
            "Checking",  # Will be filtered out
            "Savings",
            "Savings",
            "Checking",  # Will be filtered out
            "Savings"
        ]
    })
    
    accounts_file = input_dir / "accounts.csv"
    accounts_df.to_csv(accounts_file, index=False)
    print(f"✓ Created {accounts_file}")
    print(f"  Rows: {len(accounts_df)}")
    print(f"  Savings accounts: {len(accounts_df[accounts_df['AccountType'] == 'Savings'])}")
    print(f"  Checking accounts: {len(accounts_df[accounts_df['AccountType'] == 'Checking'])}")
    print()
    
    print("Sample data created successfully!")
    print()
    print("You can now run the pipeline with:")
    print("  python scripts/run_pipeline_locally.py")


if __name__ == "__main__":
    main()
