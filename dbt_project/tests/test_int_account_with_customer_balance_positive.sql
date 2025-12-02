-- Test that all account balances in the intermediate layer are positive
-- Business rule: Accounts with zero or negative balances should be filtered out

select
    account_id,
    customer_id,
    balance_amount
from {{ ref('int_account_with_customer') }}
where balance_amount <= 0
