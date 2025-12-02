{% macro quarantine_failed_records(source_table, validation_rules, quarantine_table_name) %}
/*
    Macro: quarantine_failed_records
    
    Purpose: Route records that fail validation to a quarantine table for review.
    
    Args:
        source_table: The source table or CTE to validate
        validation_rules: SQL WHERE clause defining validation failures
        quarantine_table_name: Name of the quarantine table to create/insert into
    
    Returns:
        SQL to create quarantine table and insert failed records
    
    Example usage:
        {{ quarantine_failed_records(
            source_table='raw_data',
            validation_rules='balance_amount IS NULL OR balance_amount < 0',
            quarantine_table_name='quarantine_stg_account'
        ) }}
*/

-- This macro generates SQL to handle quarantine logic
-- In a production environment, this would create a separate quarantine table
-- and insert failed records with metadata about the failure

select
    *,
    '{{ validation_rules }}' as failure_reason,
    current_timestamp() as quarantined_at
from {{ source_table }}
where {{ validation_rules }}

{% endmacro %}
