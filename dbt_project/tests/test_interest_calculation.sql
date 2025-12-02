/*
    Custom DBT Test: Interest Calculation Logic Validation
    
    Purpose: Validate that interest rate calculations follow business rules
    and that derived fields (annual_interest, new_balance) are computed correctly.
    
    Test Criteria:
    1. Interest rate must be between 0.01 (1%) and 0.025 (2.5%)
    2. Annual interest must equal original_balance * interest_rate (within rounding tolerance)
    3. New balance must equal original_balance + annual_interest
    
    This test will fail if any records violate these rules.
*/

with account_summary as (
    select
        customer_id,
        account_id,
        original_balance_amount,
        interest_rate_pct,
        annual_interest_amount,
        new_balance_amount
    from {{ ref('account_summary') }}
),

validation_checks as (
    select
        account_id,
        
        -- Check 1: Interest rate is within valid range
        case
            when interest_rate_pct < 0.01 or interest_rate_pct > 0.025 then 1
            else 0
        end as invalid_interest_rate,
        
        -- Check 2: Annual interest calculation is correct (within 0.01 rounding tolerance)
        case
            when abs(annual_interest_amount - round(original_balance_amount * interest_rate_pct, 2)) > 0.01 then 1
            else 0
        end as invalid_annual_interest,
        
        -- Check 3: New balance calculation is correct (within 0.01 rounding tolerance)
        case
            when abs(new_balance_amount - round(original_balance_amount + annual_interest_amount, 2)) > 0.01 then 1
            else 0
        end as invalid_new_balance
        
    from account_summary
),

failed_validations as (
    select
        account_id,
        invalid_interest_rate,
        invalid_annual_interest,
        invalid_new_balance
    from validation_checks
    where invalid_interest_rate = 1
       or invalid_annual_interest = 1
       or invalid_new_balance = 1
)

-- This test passes if no records are returned (all validations passed)
select * from failed_validations
