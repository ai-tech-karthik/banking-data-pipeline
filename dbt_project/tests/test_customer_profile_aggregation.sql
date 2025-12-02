-- Test that customer_profile aggregations match account_summary totals
-- Verify that the sum of accounts per customer matches the aggregated values

with customer_totals_from_accounts as (
    select
        customer_id,
        count(*) as expected_account_count,
        sum(original_balance_amount) as expected_total_balance,
        sum(annual_interest_amount) as expected_total_interest
    from {{ ref('account_summary') }}
    group by customer_id
),

profile_comparison as (
    select
        p.customer_id,
        p.total_accounts_count,
        a.expected_account_count,
        p.total_balance_amount,
        a.expected_total_balance,
        p.total_annual_interest_amount,
        a.expected_total_interest
    from {{ ref('customer_profile') }} p
    left join customer_totals_from_accounts a
        on p.customer_id = a.customer_id
)

select
    customer_id,
    total_accounts_count,
    expected_account_count,
    total_balance_amount,
    expected_total_balance,
    total_annual_interest_amount,
    expected_total_interest
from profile_comparison
where 
    total_accounts_count != expected_account_count
    or abs(total_balance_amount - expected_total_balance) >= 0.01
    or abs(total_annual_interest_amount - expected_total_interest) >= 0.01
