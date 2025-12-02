/*
    Marts model: Account Summary with Interest Calculation
    
    Purpose: Generate final account summary with calculated interest rates
    and projected balances based on business rules.
    
    Layer: Marts (Layer 5)
    Materialization: incremental (merge strategy)
    Unique Key: account_id
    
    Business Logic:
    - Base interest rate by balance tier:
        * < $10,000: 1.0% (0.01)
        * $10,000 - $19,999: 1.5% (0.015)
        * >= $20,000: 2.0% (0.02)
    - Bonus rate: +0.5% (0.005) if customer has_loan_flag = true
    - Annual interest: balance * interest_rate, rounded to 2 decimals
    - New balance: original_balance + annual_interest, rounded to 2 decimals
    
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

with savings_accounts as (
    select
        customer_id,
        account_id,
        balance_amount as balance,
        has_loan_flag as has_loan,
        valid_from_at
    from {{ ref('int_savings_account_only') }}
    
    {% if is_incremental() %}
    -- Process only new or changed records since last run
    -- Error handling: If max(calculated_at) returns NULL (empty table),
    -- fallback to processing all records
    where valid_from_at > coalesce(
        (
            select max(calculated_at)
            from {{ this }}
        ),
        '1900-01-01'::timestamp  -- Fallback to process all if table is empty
    )
    {% endif %}
),

interest_calculation as (
    select
        customer_id,
        account_id,
        balance as original_balance,
        
        -- Calculate base interest rate based on balance tiers
        case
            when balance < 10000 then 0.01
            when balance >= 10000 and balance < 20000 then 0.015
            when balance >= 20000 then 0.02
        end as base_rate,
        
        -- Add bonus rate if customer has a loan
        case
            when has_loan = true then 0.005
            else 0.0
        end as bonus_rate
        
    from savings_accounts
),

final_calculation as (
    select
        customer_id,
        account_id,
        original_balance,
        
        -- Total interest rate (base + bonus)
        base_rate + bonus_rate as interest_rate,
        
        -- Calculate annual interest (rounded to 2 decimals)
        round(original_balance * (base_rate + bonus_rate), 2) as annual_interest
        
    from interest_calculation
)

select
    account_id,
    customer_id,
    original_balance as original_balance_amount,
    interest_rate as interest_rate_pct,
    annual_interest as annual_interest_amount,
    
    -- Calculate new balance (rounded to 2 decimals)
    round(original_balance + annual_interest, 2) as new_balance_amount,
    
    -- Add calculated timestamp
    current_timestamp() as calculated_at
    
from final_calculation
