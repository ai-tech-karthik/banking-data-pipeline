/*
    Quarantine model for account data validation failures
    
    Purpose: Capture and log account records that fail validation rules
    for review and remediation. This model identifies records with data
    quality issues that prevent them from being processed in the main pipeline.
    
    Layer: Staging (Layer 2) - Quarantine
    Materialization: table (configured in dbt_project.yml)
    
    Validation Rules:
    - account_id must not be null or empty
    - customer_id must be a valid integer (not null, not empty)
    - balance must be a valid decimal number (not null, not negative)
    - account_type must not be null or empty
    
    Quarantine Reasons:
    - Invalid account_id (null or empty)
    - Invalid customer_id (null, empty, or non-numeric)
    - Invalid balance (null, empty, non-numeric, or negative)
    - Missing or empty account_type
    
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
        cast(account_id as string) as account_id,
        cast(customer_id as string) as customer_id,
        cast(balance as string) as balance,
        cast(account_type as string) as account_type,
        loaded_at
    from {{ ref('src_account') }}
),

validation_failures as (
    select
        account_id,
        customer_id,
        balance,
        account_type,
        loaded_at,
        
        -- Identify specific validation failures
        case
            when account_id is null or trim(account_id) = ''
            then 'Invalid account_id: null or empty'
            when customer_id is null or trim(customer_id) = ''
            then 'Invalid customer_id: null or empty'
            when try_cast(customer_id as integer) is null
            then 'Invalid customer_id: non-numeric value (' || customer_id || ')'
            when balance is null or trim(balance) = ''
            then 'Invalid balance: null or empty'
            when lower(trim(balance)) in ('null', 'n/a', 'none')
            then 'Invalid balance: null representation (' || balance || ')'
            when try_cast(balance as decimal(18,2)) is null
            then 'Invalid balance: non-numeric value (' || balance || ')'
            when cast(balance as decimal(18,2)) < 0
            then 'Invalid balance: negative value (' || balance || ')'
            when account_type is null or trim(account_type) = ''
            then 'Invalid account_type: null or empty'
            when lower(trim(account_type)) not in ('savings', 'checking')
            then 'Invalid account_type: must be Savings or Checking (' || account_type || ')'
            else 'Unknown validation failure'
        end as failure_reason,
        
        current_timestamp() as quarantined_at
        
    from source
    
    -- Apply validation rules (records that fail any rule are quarantined)
    where account_id is null
       or trim(account_id) = ''
       or customer_id is null
       or trim(customer_id) = ''
       or try_cast(customer_id as integer) is null  -- Non-numeric customer_id
       or balance is null
       or trim(balance) = ''
       or lower(trim(balance)) in ('null', 'n/a', 'none')
       or try_cast(balance as decimal(18,2)) is null
       or cast(balance as decimal(18,2)) < 0
       or account_type is null
       or trim(account_type) = ''
       or lower(trim(account_type)) not in ('savings', 'checking')  -- Invalid account type
)

select * from validation_failures
