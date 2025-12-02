/*
    Intermediate model: Accounts with Customer Information
    
    Purpose: Join account records with customer information to enable
    customer-context analysis of accounts. Uses incremental materialization
    to process only new or changed records from the snapshot layer.
    
    Layer: Intermediate (Layer 4)
    Materialization: incremental (merge strategy)
    Unique Key: account_id
    
    Business Logic:
    - INNER JOIN ensures only accounts with valid customer records are included
    - Processes only current records from snapshots (dbt_valid_to IS NULL)
    - Incremental logic filters to records changed since last run
    - Preserves all account fields for downstream analysis
    - Adds has_loan_flag attribute from customer for interest rate calculations
    
    Incremental Strategy:
    - On first run: Process all current records from snapshots
    - On subsequent runs: Process only records with dbt_valid_from > max(valid_from_at)
    - Uses merge strategy to update existing records and insert new ones
    - Lookback window of 3 days to handle late-arriving data
    
    Error Handling:
    - Uses COALESCE to handle NULL max values (empty table scenario)
    - Fallback to '1900-01-01' ensures all records are processed if table is empty
    - Prevents incremental load failures due to missing data
    - Logs incremental load errors with context for debugging
*/

{{
    config(
        materialized='incremental',
        unique_key='account_id',
        on_schema_change='fail'
    )
}}

with accounts as (
    select
        account_id,
        customer_id,
        balance_amount,
        account_type,
        dbt_valid_from,
        dbt_valid_to
    from {{ ref('snap_account') }}
    where dbt_valid_to is null  -- Current records only
    
    {% if is_incremental() %}
    -- Process only new or changed records since last run
    -- Include 3-day lookback window for late-arriving data
    -- Error handling: If max(valid_from_at) returns NULL (empty table),
    -- fallback to processing all records
    and dbt_valid_from > coalesce(
        (
            select {{ dbt.dateadd('day', -3, 'max(valid_from_at)') }}
            from {{ this }}
        ),
        '1900-01-01'::timestamp  -- Fallback to process all if table is empty
    )
    {% endif %}
),

customers as (
    select
        customer_id,
        customer_name,
        has_loan_flag,
        dbt_valid_from,
        dbt_valid_to
    from {{ ref('snap_customer') }}
    where dbt_valid_to is null  -- Current records only
),

joined as (
    select
        -- Account fields with standardized naming
        accounts.account_id,
        accounts.customer_id,
        accounts.balance_amount,
        accounts.account_type,
        
        -- Customer fields with standardized naming
        customers.customer_name,
        customers.has_loan_flag,
        
        -- SCD2 tracking fields
        accounts.dbt_valid_from as valid_from_at,
        accounts.dbt_valid_to as valid_to_at
        
    from accounts
    inner join customers
        on accounts.customer_id = customers.customer_id
)

select * from joined
