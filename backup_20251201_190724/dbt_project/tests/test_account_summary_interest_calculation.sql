-- Test that interest calculations in account_summary are accurate
-- Verify: annual_interest_amount = original_balance_amount * interest_rate_pct
-- Allow for small rounding differences (< 0.01)

with calculation_check as (
    select
        account_id,
        original_balance_amount,
        interest_rate_pct,
        annual_interest_amount,
        round(original_balance_amount * interest_rate_pct, 2) as expected_interest,
        abs(annual_interest_amount - round(original_balance_amount * interest_rate_pct, 2)) as difference
    from {{ ref('account_summary') }}
)

select
    account_id,
    original_balance_amount,
    interest_rate_pct,
    annual_interest_amount,
    expected_interest,
    difference
from calculation_check
where difference >= 0.01
