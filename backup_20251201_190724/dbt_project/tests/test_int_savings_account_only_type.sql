-- Test that int_savings_account_only contains only Savings accounts
-- Business rule: This model should filter to account_type = 'Savings' only

select
    account_id,
    customer_id,
    balance_amount
from {{ ref('int_account_with_customer') }}
where account_type = 'Savings'
  and account_id not in (
    select account_id from {{ ref('int_savings_account_only') }}
  )
