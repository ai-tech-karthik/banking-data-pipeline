/*
    Snapshot model for customer data with SCD2 tracking
    
    Purpose: Track historical changes to customer data over time using
    Slowly Changing Dimension Type 2 (SCD2) methodology. This allows
    point-in-time analysis and historical reporting.
    
    Layer: Snapshots (Layer 3)
    Materialization: snapshot (DBT snapshot type)
    Strategy: timestamp (detects changes based on loaded_at column)
    Unique Key: customer_id
    
    SCD2 Behavior:
    - On first run: All records inserted with dbt_valid_from = current_timestamp
    - On subsequent runs:
      * Changed records: New version created with new dbt_valid_from
      * Previous version: dbt_valid_to set to current_timestamp
      * Unchanged records: No action taken
      * Deleted records: dbt_valid_to set (if invalidate_hard_deletes=true)
    
    Generated SCD2 Columns:
    - dbt_scd_id: Unique identifier for each record version
    - dbt_updated_at: Timestamp when the snapshot was last updated
    - dbt_valid_from: Timestamp when this version became active
    - dbt_valid_to: Timestamp when this version became inactive (NULL for current)
*/

{% snapshot snap_customer %}

{{
    config(
        target_schema='snapshots',
        unique_key='customer_id',
        strategy='timestamp',
        updated_at='loaded_at',
        invalidate_hard_deletes=true
    )
}}

select
    customer_id,
    customer_name,
    has_loan_flag,
    loaded_at
from {{ ref('stg_customer') }}

{% endsnapshot %}
