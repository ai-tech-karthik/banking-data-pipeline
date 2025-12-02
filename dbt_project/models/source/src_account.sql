/*
    Source model for account data
    
    Purpose: Persist raw account data without transformation.
    This is the first layer in the five-layer architecture, capturing data 
    exactly as received from CSV files.
    
    Layer: Source (Layer 1)
    Materialization: table (configured in dbt_project.yml)
    Contract: Enforced (defined in _source.yml)
    
    Transformations:
    - Add loaded_at timestamp to track when data was ingested
    - No other transformations - preserve raw data exactly as received
*/

select
    cast(AccountID as string) as account_id,
    cast(CustomerID as string) as customer_id,
    cast(Balance as string) as balance,
    cast(AccountType as string) as account_type,
    current_timestamp() as loaded_at
from {{ source('raw', 'accounts_raw') }}
