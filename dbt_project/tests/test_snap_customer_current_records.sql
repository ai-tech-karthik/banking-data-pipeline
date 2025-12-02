-- Test that current customer records have null dbt_valid_to
-- Current records should always have dbt_valid_to IS NULL

select
    customer_id,
    dbt_scd_id,
    dbt_valid_from,
    dbt_valid_to
from {{ ref('snap_customer') }}
where dbt_valid_to is null
  and dbt_valid_from > current_timestamp
