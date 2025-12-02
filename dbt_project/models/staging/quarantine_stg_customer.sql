/*
    Quarantine model for customer data validation failures
    
    Purpose: Capture and log customer records that fail validation rules
    for review and remediation. This model identifies records with data
    quality issues that prevent them from being processed in the main pipeline.
    
    Layer: Staging (Layer 2) - Quarantine
    Materialization: table (configured in dbt_project.yml)
    
    Validation Rules:
    - customer_id must be a valid integer (not null, not empty)
    - name must not be null or empty after trimming
    - has_loan must be a recognized boolean value
    
    Quarantine Reasons:
    - Invalid customer_id (null, empty, or non-numeric)
    - Missing or empty customer name
    - Invalid has_loan value (not in recognized set)
    
    Usage:
    - Review quarantined records regularly
    - Fix data quality issues at the source
    - Reprocess corrected records through the pipeline
*/

{{
    config(
        materialized='table',
        tags=['quarantine', 'data_quality']
    )
}}

with source as (
    select
        cast(customer_id as string) as customer_id,
        cast(name as string) as name,
        cast(has_loan as string) as has_loan,
        loaded_at
    from {{ ref('src_customer') }}
),

validation_failures as (
    select
        customer_id,
        name,
        has_loan,
        loaded_at,
        
        -- Identify specific validation failures
        case
            when customer_id is null or trim(customer_id) = ''
            then 'Invalid customer_id: null or empty'
            when try_cast(customer_id as integer) is null
            then 'Invalid customer_id: non-numeric value (' || customer_id || ')'
            when name is null or trim(name) = ''
            then 'Invalid name: null or empty'
            when lower(trim(has_loan)) not in ('yes', 'y', 'true', '1', 'no', 'n', 'false', '0', 'none', '')
            then 'Invalid has_loan value: ' || has_loan
            else 'Unknown validation failure'
        end as failure_reason,
        
        current_timestamp() as quarantined_at
        
    from source
    
    -- Apply validation rules (records that fail any rule are quarantined)
    where customer_id is null
       or trim(customer_id) = ''
       or try_cast(customer_id as integer) is null  -- Non-numeric customer_id
       or name is null
       or trim(name) = ''
       or lower(trim(has_loan)) not in ('yes', 'y', 'true', '1', 'no', 'n', 'false', '0', 'none', '')
)

select * from validation_failures
