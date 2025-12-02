# Data Flow Documentation

## Overview

This document provides detailed data flow diagrams and explanations for the LendingClub Data Pipeline. It traces data from raw CSV files through transformations to final outputs.

## High-Level Data Flow

```
┌─────────────┐
│   CSV Files │
│  (Inputs)   │
└──────┬──────┘
       │
       ▼
┌─────────────────────────────────────┐
│     INGESTION LAYER (Dagster)       │
│  • customers_raw                    │
│  • accounts_raw                     │
│  Validation: Schema, Empty Files    │
└──────┬──────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────┐
│     STAGING LAYER (DBT Views)       │
│  • stg_customers__cleaned           │
│  • stg_accounts__cleaned            │
│  Transform: Clean, Normalize, Cast  │
│  Tests: Unique, Not Null, Values    │
└──────┬──────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────┐
│  INTERMEDIATE LAYER (DBT Ephemeral) │
│  • int_accounts__with_customer      │
│  • int_savings_accounts_only        │
│  Transform: Join, Filter            │
└──────┬──────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────┐
│     MARTS LAYER (DBT Tables)        │
│  • account_summary                  │
│  Transform: Calculate Interest      │
│  Tests: Business Logic Validation   │
└──────┬──────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────┐
│     OUTPUT LAYER (Dagster)          │
│  • CSV Export                       │
│  • Parquet Export                   │
│  • Databricks Load (prod)           │
└─────────────────────────────────────┘
```

## Detailed Layer-by-Layer Flow

### 1. Ingestion Layer

**Input**: Raw CSV files in `data/inputs/`

#### Customer Data Flow

```
Customer.csv
├── Columns: CustomerID, Name, HasLoan
├── Issues: Whitespace, inconsistent casing
│
▼ customers_raw asset
├── Read CSV with pandas
├── Validate: File exists, not empty
├── Validate: Required columns present
├── Metadata: Row count, timestamp
│
▼ Output: Pandas DataFrame
└── Stored in DuckDB/Databricks
```

**Example Data Transformation**:
```
Input:
  CustomerID: " 123 ", Name: "JOHN DOE  ", HasLoan: "yes"

After Ingestion:
  CustomerID: " 123 ", Name: "JOHN DOE  ", HasLoan: "yes"
  (No transformation, just validation)
```

#### Account Data Flow

```
accounts.csv
├── Columns: AccountID, CustomerID, Balance, AccountType
├── Issues: Whitespace, null balances, inconsistent casing
│
▼ accounts_raw asset
├── Read CSV with pandas
├── Validate: File exists, not empty
├── Validate: Required columns present
├── Metadata: Row count, timestamp
│
▼ Output: Pandas DataFrame
└── Stored in DuckDB/Databricks
```

### 2. Staging Layer

**Purpose**: Clean and normalize raw data

#### stg_customers__cleaned Flow

```sql
-- Input: customers_raw
SELECT
    CAST(TRIM(CustomerID) AS INTEGER) as customer_id,
    LOWER(TRIM(Name)) as name,
    CASE
        WHEN LOWER(TRIM(HasLoan)) = 'yes' THEN 'Yes'
        WHEN LOWER(TRIM(HasLoan)) = 'no' THEN 'No'
        ELSE 'None'
    END as has_loan
FROM customers_raw
```

**Example Transformation**:
```
Input:
  CustomerID: " 123 ", Name: "JOHN DOE  ", HasLoan: "yes"

Output:
  customer_id: 123, name: "john doe", has_loan: "Yes"
```

**Data Quality Tests**:
- ✓ customer_id is unique
- ✓ customer_id is not null
- ✓ name is not null
- ✓ has_loan in ('Yes', 'No', 'None')

#### stg_accounts__cleaned Flow

```sql
-- Input: accounts_raw
SELECT
    TRIM(AccountID) as account_id,
    CAST(TRIM(CustomerID) AS INTEGER) as customer_id,
    CAST(Balance AS DECIMAL(10,2)) as balance,
    INITCAP(TRIM(AccountType)) as account_type
FROM accounts_raw
WHERE Balance IS NOT NULL AND Balance != ''
```

**Example Transformation**:
```
Input:
  AccountID: "A001 ", CustomerID: " 123 ", Balance: "5000.50", AccountType: "savings"

Output:
  account_id: "A001", customer_id: 123, balance: 5000.50, account_type: "Savings"
```

**Data Quality Tests**:
- ✓ account_id is unique
- ✓ account_id is not null
- ✓ customer_id is not null
- ✓ balance is not null
- ✓ account_type in ('Savings', 'Checking')

### 3. Intermediate Layer

**Purpose**: Join and filter data for specific business needs

#### int_accounts__with_customer Flow

```sql
-- Join accounts with customer information
SELECT
    a.account_id,
    a.customer_id,
    a.balance,
    a.account_type,
    c.has_loan
FROM {{ ref('stg_accounts__cleaned') }} a
INNER JOIN {{ ref('stg_customers__cleaned') }} c
    ON a.customer_id = c.customer_id
```

**Example Transformation**:
```
Input (stg_accounts__cleaned):
  account_id: "A001", customer_id: 123, balance: 5000.50, account_type: "Savings"

Input (stg_customers__cleaned):
  customer_id: 123, name: "john doe", has_loan: "Yes"

Output:
  account_id: "A001", customer_id: 123, balance: 5000.50, 
  account_type: "Savings", has_loan: "Yes"
```

**Join Logic**:
- INNER JOIN ensures only accounts with matching customers
- Orphaned accounts (no customer) are excluded
- Multiple accounts per customer are preserved

#### int_savings_accounts_only Flow

```sql
-- Filter to savings accounts only
SELECT
    account_id,
    customer_id,
    balance,
    has_loan
FROM {{ ref('int_accounts__with_customer') }}
WHERE account_type = 'Savings'
```

**Example Transformation**:
```
Input:
  account_id: "A001", customer_id: 123, balance: 5000.50, 
  account_type: "Savings", has_loan: "Yes"
  
  account_id: "A002", customer_id: 123, balance: 2000.00, 
  account_type: "Checking", has_loan: "Yes"

Output (Checking account filtered out):
  account_id: "A001", customer_id: 123, balance: 5000.50, has_loan: "Yes"
```

### 4. Marts Layer

**Purpose**: Apply business logic and generate analytical outputs

#### account_summary Flow

```sql
-- Calculate interest rates and projections
WITH interest_calculation AS (
    SELECT
        customer_id,
        account_id,
        balance as original_balance,
        -- Base rate by balance tier
        CASE
            WHEN balance < 10000 THEN 0.01
            WHEN balance >= 10000 AND balance < 20000 THEN 0.015
            ELSE 0.02
        END +
        -- Bonus rate for customers with loans
        CASE
            WHEN has_loan = 'Yes' THEN 0.005
            ELSE 0.0
        END as interest_rate
    FROM {{ ref('int_savings_accounts_only') }}
)
SELECT
    customer_id,
    account_id,
    original_balance,
    interest_rate,
    ROUND(original_balance * interest_rate, 2) as annual_interest,
    ROUND(original_balance + (original_balance * interest_rate), 2) as new_balance
FROM interest_calculation
```

**Example Transformation**:

**Scenario 1: Low balance, no loan**
```
Input:
  customer_id: 123, account_id: "A001", balance: 5000.00, has_loan: "No"

Calculation:
  Base rate: 0.01 (< 10000)
  Bonus rate: 0.0 (no loan)
  Interest rate: 0.01
  Annual interest: 5000.00 * 0.01 = 50.00
  New balance: 5000.00 + 50.00 = 5050.00

Output:
  customer_id: 123, account_id: "A001", original_balance: 5000.00,
  interest_rate: 0.01, annual_interest: 50.00, new_balance: 5050.00
```

**Scenario 2: Medium balance, has loan**
```
Input:
  customer_id: 456, account_id: "A002", balance: 15000.00, has_loan: "Yes"

Calculation:
  Base rate: 0.015 (10000 <= balance < 20000)
  Bonus rate: 0.005 (has loan)
  Interest rate: 0.02
  Annual interest: 15000.00 * 0.02 = 300.00
  New balance: 15000.00 + 300.00 = 15300.00

Output:
  customer_id: 456, account_id: "A002", original_balance: 15000.00,
  interest_rate: 0.02, annual_interest: 300.00, new_balance: 15300.00
```

**Scenario 3: High balance, has loan**
```
Input:
  customer_id: 789, account_id: "A003", balance: 25000.00, has_loan: "Yes"

Calculation:
  Base rate: 0.02 (>= 20000)
  Bonus rate: 0.005 (has loan)
  Interest rate: 0.025
  Annual interest: 25000.00 * 0.025 = 625.00
  New balance: 25000.00 + 625.00 = 25625.00

Output:
  customer_id: 789, account_id: "A003", original_balance: 25000.00,
  interest_rate: 0.025, annual_interest: 625.00, new_balance: 25625.00
```

**Business Logic Tests**:
- ✓ Interest rate between 0.01 and 0.025
- ✓ Annual interest = original_balance * interest_rate
- ✓ New balance = original_balance + annual_interest

### 5. Output Layer

**Purpose**: Export results in multiple formats

#### CSV Export Flow

```
account_summary (DBT table)
│
▼ account_summary_csv asset
├── Query: SELECT * FROM account_summary
├── Convert to Pandas DataFrame
├── Write to data/outputs/account_summary.csv
└── Format: UTF-8, headers included
```

#### Parquet Export Flow

```
account_summary (DBT table)
│
▼ account_summary_parquet asset
├── Query: SELECT * FROM account_summary
├── Convert to Pandas DataFrame
├── Write to data/outputs/account_summary.parquet
└── Format: Snappy compression
```

#### Databricks Load Flow (Production Only)

```
account_summary (DBT table)
│
▼ account_summary_to_databricks asset
├── Condition: DATABASE_TYPE == 'databricks'
├── Query: SELECT * FROM account_summary
├── Convert to Pandas DataFrame
├── Write to Databricks Delta table
├── Retry logic: 3 attempts, exponential backoff
└── Table: {catalog}.{schema}.account_summary
```

## Data Lineage Graph

```
Customer.csv ──┐
               ├──> customers_raw ──> stg_customers__cleaned ──┐
               │                                                │
               │                                                ├──> int_accounts__with_customer ──> int_savings_accounts_only ──> account_summary ──┬──> account_summary_csv
               │                                                │                                                                                    │
accounts.csv ──┘                                                │                                                                                    ├──> account_summary_parquet
               └──> accounts_raw ──> stg_accounts__cleaned ────┘                                                                                    │
                                                                                                                                                     └──> account_summary_to_databricks
```

## Data Volume Flow

**Example Pipeline Execution**:

```
Ingestion:
  customers_raw: 1,000 rows
  accounts_raw: 2,500 rows

Staging:
  stg_customers__cleaned: 1,000 rows (no filtering)
  stg_accounts__cleaned: 2,450 rows (50 rows with null balance filtered)

Intermediate:
  int_accounts__with_customer: 2,400 rows (50 orphaned accounts excluded)
  int_savings_accounts_only: 1,200 rows (1,200 checking accounts filtered)

Marts:
  account_summary: 1,200 rows (final output)

Outputs:
  account_summary.csv: 1,200 rows
  account_summary.parquet: 1,200 rows
  Databricks table: 1,200 rows (prod only)
```

## Error Handling Flow

### Ingestion Errors

```
CSV File Read
│
├─ File Not Found ──> Raise FileNotFoundError ──> Pipeline Fails
│
├─ Empty File ──> Raise ValueError ──> Pipeline Fails
│
└─ Missing Columns ──> Raise ValueError ──> Pipeline Fails
```

### Transformation Errors

```
DBT Model Execution
│
├─ SQL Error ──> DBT Fails ──> Dagster Asset Fails
│
├─ Test Failure ──> DBT Fails ──> Dagster Asset Fails
│
└─ Success ──> Continue to Next Layer
```

### Output Errors

```
Output Export
│
├─ Disk Space Error ──> Raise OSError ──> Pipeline Fails
│
├─ Databricks Connection Error ──> Retry (3x) ──> Success or Fail
│
└─ Success ──> Pipeline Complete
```

## Performance Characteristics

### Execution Times (Typical)

```
Ingestion Layer:     5-10 seconds
Staging Layer:       10-15 seconds
Intermediate Layer:  5-10 seconds
Marts Layer:         10-20 seconds
Output Layer:        5-10 seconds
─────────────────────────────────
Total Pipeline:      35-65 seconds
```

### Data Processing Rates

- **DuckDB (Local)**: ~100,000 rows/second
- **Databricks (Production)**: ~1,000,000 rows/second

### Bottlenecks

1. **CSV Parsing**: Slowest part of ingestion
2. **JOIN Operations**: Most compute-intensive transformation
3. **File I/O**: Output layer bottleneck for large datasets

## Optimization Strategies

### Current Optimizations

1. **Ephemeral Intermediate Models**: No unnecessary storage
2. **View Staging Models**: Always fresh, no storage overhead
3. **Table Marts**: Persistent for fast querying

### Future Optimizations

1. **Partitioning**: Process data by date/region partitions
2. **Incremental Models**: Only process changed records
3. **Parallel Execution**: Run independent assets concurrently
4. **Columnar Storage**: Use Parquet for intermediate storage
