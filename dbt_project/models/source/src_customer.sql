/*
    Source model for customer data
    
    Purpose: Persist raw customer data without transformation.
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
    cast(CustomerID as string) as customer_id,
    cast(Name as string) as name,
    cast(HasLoan as string) as has_loan,
    current_timestamp() as loaded_at
from {{ source('raw', 'customers_raw') }}
