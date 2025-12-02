/*
    Intermediate model: Savings Accounts Only
    
    Purpose: Filter accounts to include only savings accounts for interest
    rate calculations and analysis. Uses incremental materialization to
    process only new or changed records.
    
    Layer: Intermediate (Layer 4)
    Materialization: incremental (merge strategy)
    Unique Key: account_id
    
    Business Logic:
    - Filters to account_type = 'Savings' only
    - Excludes checking accounts from downstream processing
    - Processes only changed records in incremental runs
    - Preserves all fields from the joined account-customer data
    
    Incremental Strategy:
    - On first run: Process all savings accounts
    - On subsequent runs: Process only records changed since last run
    - Uses merge strategy to update existing records and insert new ones
    - Filters based on valid_from_at timestamp from upstream model
    
    Error Handling:
    - Uses COALESCE to handle NULL max values (empty table scenario)
    - Fallback to '1900-01-01' ensures all records are processed if table is empty
    - Prevents incremental load failures due to missing data
*/

{{
    config(
        materialized='incremental',
        unique_key='account_id',
        on_schema_change='fail'
    )
}}

with accounts_with_customer as (
    select
        account_id,
        customer_id,
        customer_name,
        balance_amount,
        account_type,
        has_loan_flag,
        valid_from_at,
        valid_to_at
    from {{ ref('int_account_with_customer') }}
    
    {% if is_incremental() %}
    -- Process only new or changed records since last run
    -- Error handling: If max(valid_from_at) returns NULL (empty table),
    -- fallback to processing all records
    where valid_from_at > coalesce(
        (
            select max(valid_from_at)
            from {{ this }}
        ),
        '1900-01-01'::timestamp  -- Fallback to process all if table is empty
    )
    {% endif %}
),

savings_only as (
    select
        account_id,
        customer_id,
        customer_name,
        balance_amount,
        has_loan_flag,
        valid_from_at,
        valid_to_at
    from accounts_with_customer
    where account_type = 'savings'
)

select * from savings_only
