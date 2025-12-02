#!/usr/bin/env python3
"""
Create enhanced sample data files with edge cases for testing.
This script generates more comprehensive test data including edge cases.
"""

import csv
from pathlib import Path


def create_customer_data():
    """Create customer data with various edge cases."""
    customers = [
        # Standard cases
        {"CustomerID": "1", "Name": "Alice Smith", "HasLoan": "Yes"},
        {"CustomerID": "2", "Name": "Bob Jones", "HasLoan": "No"},
        {"CustomerID": "3", "Name": "Charlie Brown", "HasLoan": "None"},
        
        # Edge cases - whitespace
        {"CustomerID": " 4 ", "Name": "  Diana Prince  ", "HasLoan": "Yes"},
        {"CustomerID": "5  ", "Name": "Eve Adams", "HasLoan": "No"},
        
        # Edge cases - casing
        {"CustomerID": "6", "Name": "FRANK MILLER", "HasLoan": "yes"},
        {"CustomerID": "7", "Name": "grace lee", "HasLoan": "YES"},
        {"CustomerID": "8", "Name": "Henry Wilson", "HasLoan": "no"},
        
        # Edge cases - loan status variations
        {"CustomerID": "9", "Name": "Iris Chen", "HasLoan": "none"},
        {"CustomerID": "10", "Name": "Jack Taylor", "HasLoan": "None"},
        
        # Additional customers for balance tier testing
        {"CustomerID": "11", "Name": "Karen White", "HasLoan": "Yes"},
        {"CustomerID": "12", "Name": "Leo Martinez", "HasLoan": "No"},
        {"CustomerID": "13", "Name": "Maya Patel", "HasLoan": "Yes"},
        {"CustomerID": "14", "Name": "Noah Kim", "HasLoan": "None"},
        {"CustomerID": "15", "Name": "Olivia Garcia", "HasLoan": "Yes"},
    ]
    
    return customers


def create_account_data():
    """Create account data with various edge cases."""
    accounts = [
        # Balance tier: < 10,000 (1% base rate)
        {"AccountID": "A001", "CustomerID": "1", "Balance": "5000.00", "AccountType": "Savings"},
        {"AccountID": "A002", "CustomerID": "4", "Balance": "8000.50", "AccountType": "Savings"},
        {"AccountID": "A003", "CustomerID": "8", "Balance": "9999.99", "AccountType": "Savings"},
        
        # Balance tier: 10,000 - 19,999 (1.5% base rate)
        {"AccountID": "A004", "CustomerID": "2", "Balance": "10000.00", "AccountType": "Savings"},
        {"AccountID": "A005", "CustomerID": "5", "Balance": "15000.00", "AccountType": "Savings"},
        {"AccountID": "A006", "CustomerID": "9", "Balance": "19999.99", "AccountType": "Savings"},
        
        # Balance tier: >= 20,000 (2% base rate)
        {"AccountID": "A007", "CustomerID": "3", "Balance": "20000.00", "AccountType": "Savings"},
        {"AccountID": "A008", "CustomerID": "7", "Balance": "25000.00", "AccountType": "Savings"},
        {"AccountID": "A009", "CustomerID": "10", "Balance": "50000.00", "AccountType": "Savings"},
        
        # Checking accounts (should be filtered out)
        {"AccountID": "A010", "CustomerID": "6", "Balance": "12000.00", "AccountType": "Checking"},
        {"AccountID": "A011", "CustomerID": "11", "Balance": "18000.00", "AccountType": "checking"},
        
        # Edge cases - whitespace in fields
        {"AccountID": "A012", "CustomerID": " 12 ", "Balance": "22000.00", "AccountType": " Savings "},
        
        # Edge cases - casing variations
        {"AccountID": "A013", "CustomerID": "13", "Balance": "30000.00", "AccountType": "savings"},
        {"AccountID": "A014", "CustomerID": "14", "Balance": "40000.00", "AccountType": "SAVINGS"},
        
        # Customers with loans (should get bonus rate)
        {"AccountID": "A015", "CustomerID": "15", "Balance": "35000.00", "AccountType": "Savings"},
        
        # Edge case - exact boundary values
        {"AccountID": "A016", "CustomerID": "1", "Balance": "10000.01", "AccountType": "Savings"},
        {"AccountID": "A017", "CustomerID": "6", "Balance": "19999.00", "AccountType": "Savings"},
    ]
    
    return accounts


def write_csv(filename: str, data: list, fieldnames: list):
    """Write data to CSV file."""
    filepath = Path(filename)
    filepath.parent.mkdir(parents=True, exist_ok=True)
    
    with open(filepath, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data)
    
    print(f"✓ Created {filename} with {len(data)} rows")


def main():
    """Create enhanced sample data files."""
    print("Creating enhanced sample data files...")
    print()
    
    # Create customer data
    customers = create_customer_data()
    write_csv(
        "data/inputs/Customer.csv",
        customers,
        ["CustomerID", "Name", "HasLoan"]
    )
    
    # Create account data
    accounts = create_account_data()
    write_csv(
        "data/inputs/accounts.csv",
        accounts,
        ["AccountID", "CustomerID", "Balance", "AccountType"]
    )
    
    print()
    print("Sample data created successfully!")
    print()
    print("Data characteristics:")
    print(f"  • {len(customers)} customers")
    print(f"  • {len(accounts)} accounts")
    print(f"  • Balance tiers: < 10k, 10k-20k, >= 20k")
    print(f"  • Loan statuses: Yes, No, None (with casing variations)")
    print(f"  • Account types: Savings, Checking (with casing variations)")
    print(f"  • Edge cases: whitespace, casing, boundary values")
    print()
    print("Next steps:")
    print("  1. Run: docker-compose up -d")
    print("  2. Materialize assets in Dagster UI")
    print("  3. Run: python3 scripts/validate_pipeline.py")


if __name__ == "__main__":
    main()
