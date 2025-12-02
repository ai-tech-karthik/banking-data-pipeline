/*
    Staging model for account data
    
    Purpose: Clean and normalize account data from the source layer.
    This is the second layer in the five-layer architecture, applying
    standardization and cleaning transformations.
    
    Layer: Staging (Layer 2)
    Materialization: view (configured in dbt_project.yml)
    Contract: Enforced (defined in _staging.yml)
    
    Transformations:
    - Trim whitespace from string fields
    - Cast customer_id to integer and balance to decimal(18,2)
    - Normalize account_type to lowercase
    - Handle null values in balance (filter out)
    - Replace null string representations with actual NULL
    - Preserve loaded_at timestamp from source layer
    
    Naming Conventions:
    - account_id: Primary key (string)
    - customer_id: Foreign key (integer)
    - balance_amount: Amount field with _amount suffix (decimal)
    - account_type: Type field (lowercase string)
    - loaded_at: Timestamp with _at suffix
*/

with source as (
    select
        account_id,
        customer_id,
        balance,
        account_type,
        loaded_at
    from {{ ref('src_account') }}
),

-- Exclude records that failed validation (in quarantine)
-- Use NOT EXISTS to handle NULLs properly
valid_source as (
    select
        s.account_id,
        s.customer_id,
        s.balance,
        s.account_type,
        s.loaded_at
    from source s
    where not exists (
        select 1
        from {{ ref('quarantine_stg_account') }} q
        where coalesce(s.account_id, '') = coalesce(q.account_id, '')
          and coalesce(s.customer_id, '') = coalesce(q.customer_id, '')
          and coalesce(s.balance, '') = coalesce(q.balance, '')
          and coalesce(s.account_type, '') = coalesce(q.account_type, '')
    )
),

cleaned as (
    select
        -- Trim whitespace from account_id (keep as string)
        trim(cast(account_id as string)) as account_id,
        
        -- Cast customer_id to integer
        cast(customer_id as integer) as customer_id,
        
        -- Cast balance to decimal(18,2) with standardized precision
        -- Handle null string representations
        case
            when lower(trim(cast(balance as string))) in ('null', 'n/a', '', 'none')
            then null
            else cast(balance as decimal(18,2))
        end as balance_amount,
        
        -- Normalize account_type to lowercase and trim
        lower(trim(cast(account_type as string))) as account_type,
        
        -- Preserve loaded_at timestamp
        loaded_at
        
    from valid_source
    
    -- Filter out records where balance is null or empty
    where balance is not null
      and trim(cast(balance as string)) != ''
      and lower(trim(cast(balance as string))) not in ('null', 'n/a', 'none')
)

select * from cleaned
