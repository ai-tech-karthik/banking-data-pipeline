/*
    Snapshot model for account data with SCD2 tracking
    
    Purpose: Track historical changes to account data over time using
    Slowly Changing Dimension Type 2 (SCD2) methodology. This allows
    tracking balance changes, account type changes, and other modifications.
    
    Layer: Snapshots (Layer 3)
    Materialization: snapshot (DBT snapshot type)
    Strategy: check_cols (detects changes by comparing all column values)
    Unique Key: account_id
    
    Strategy Rationale:
    Using check_cols strategy instead of timestamp because we want to detect
    any changes to account data (balance, type, etc.) even if they occur
    within the same loaded_at timestamp. This provides more granular change
    detection for account records.
    
    SCD2 Behavior:
    - On first run: All records inserted with dbt_valid_from = current_timestamp
    - On subsequent runs:
      * Changed records: New version created when any column value changes
      * Previous version: dbt_valid_to set to current_timestamp
      * Unchanged records: No action taken
      * Deleted records: dbt_valid_to set (if invalidate_hard_deletes=true)
    
    Generated SCD2 Columns:
    - dbt_scd_id: Unique identifier for each record version
    - dbt_updated_at: Timestamp when the snapshot was last updated
    - dbt_valid_from: Timestamp when this version became active
    - dbt_valid_to: Timestamp when this version became inactive (NULL for current)
*/

{% snapshot snap_account %}

{{
    config(
        target_schema='snapshots',
        unique_key='account_id',
        strategy='check',
        check_cols='all',
        invalidate_hard_deletes=true
    )
}}

select
    account_id,
    customer_id,
    balance_amount,
    account_type,
    loaded_at
from {{ ref('stg_account') }}

{% endsnapshot %}
