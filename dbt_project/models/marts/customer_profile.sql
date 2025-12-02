/*
    Marts model: Customer Profile
    
    Purpose: Aggregate customer-level analytics including total accounts,
    balances, and projected interest across all savings accounts.
    
    Layer: Marts (Layer 5)
    Materialization: incremental (merge strategy)
    Unique Key: customer_id
    
    Business Logic:
    - Aggregates data from account_summary by customer
    - Calculates total number of accounts per customer
    - Sums total balance across all customer accounts
    - Sums total annual interest across all customer accounts
    - Includes customer loan status flag
    
    Incremental Strategy:
    - On first run: Process all customers
    - On subsequent runs: Process only customers with changed accounts
    - Uses merge strategy to update existing records and insert new ones
    - Filters based on calculated_at timestamp from upstream model
    
    Error Handling:
    - Uses COALESCE to handle NULL max values (empty table scenario)
    - Fallback to '1900-01-01' ensures all records are processed if table is empty
    - Prevents incremental load failures due to missing data
*/

{{
    config(
        materialized='incremental',
        unique_key='customer_id',
        on_schema_change='fail'
    )
}}

with account_data as (
    select
        customer_id,
        account_id,
        original_balance_amount,
        annual_interest_amount,
        calculated_at
    from {{ ref('account_summary') }}
    
    {% if is_incremental() %}
    -- Process only customers with accounts changed since last run
    -- Error handling: If max(calculated_at) returns NULL (empty table),
    -- fallback to processing all records
    where calculated_at > coalesce(
        (
            select max(calculated_at)
            from {{ this }}
        ),
        '1900-01-01'::timestamp  -- Fallback to process all if table is empty
    )
    {% endif %}
),

customer_aggregation as (
    select
        customer_id,
        count(distinct account_id) as total_accounts_count,
        sum(original_balance_amount) as total_balance_amount,
        sum(annual_interest_amount) as total_annual_interest_amount,
        max(calculated_at) as calculated_at
    from account_data
    group by customer_id
),

customer_info as (
    select distinct
        customer_id,
        customer_name,
        has_loan_flag
    from {{ ref('int_savings_account_only') }}
)

select
    ca.customer_id,
    ci.customer_name,
    ci.has_loan_flag,
    ca.total_accounts_count,
    ca.total_balance_amount,
    ca.total_annual_interest_amount,
    ca.calculated_at
from customer_aggregation ca
left join customer_info ci
    on ca.customer_id = ci.customer_id
