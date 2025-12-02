-- Test that all interest rates are within the expected range (0.01 to 0.025)
select
    account_id,
    interest_rate_pct
from {{ ref('account_summary') }}
where interest_rate_pct < 0.01 
   or interest_rate_pct > 0.025
