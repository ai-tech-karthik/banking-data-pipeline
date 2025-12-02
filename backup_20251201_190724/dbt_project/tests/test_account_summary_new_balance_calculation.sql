-- Test that new balance calculations in account_summary are accurate
-- Verify: new_balance_amount = original_balance_amount + annual_interest_amount
-- Allow for small rounding differences (< 0.01)

with calculation_check as (
    select
        account_id,
        original_balance_amount,
        annual_interest_amount,
        new_balance_amount,
        round(original_balance_amount + annual_interest_amount, 2) as expected_new_balance,
        abs(new_balance_amount - round(original_balance_amount + annual_interest_amount, 2)) as difference
    from {{ ref('account_summary') }}
)

select
    account_id,
    original_balance_amount,
    annual_interest_amount,
    new_balance_amount,
    expected_new_balance,
    difference
from calculation_check
where difference >= 0.01
