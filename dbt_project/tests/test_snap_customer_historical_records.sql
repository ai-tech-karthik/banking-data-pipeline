-- Test that historical customer records have non-null dbt_valid_to
-- Historical records should always have dbt_valid_to IS NOT NULL
-- and dbt_valid_to should be greater than dbt_valid_from

select
    customer_id,
    dbt_scd_id,
    dbt_valid_from,
    dbt_valid_to
from {{ ref('snap_customer') }}
where dbt_valid_to is not null
  and dbt_valid_to <= dbt_valid_from
