{% macro clean_string(column_name) %}
{#
    Clean and standardize string values.
    
    This macro trims whitespace, converts to lowercase, and handles various
    null representations by converting them to actual NULL values.
    
    Args:
        column_name (string): The column name or expression to clean
        
    Returns:
        SQL expression: Cleaned string value or NULL
        
    Example:
        {{ clean_string('name') }} -> trim(lower(name)) with null handling
        
    Null representations handled:
        - 'null' (case insensitive)
        - 'N/A'
        - 'n/a'
        - '' (empty string)
        - 'none' (case insensitive)
#}
    case
        when {{ column_name }} is null then null
        when lower(trim({{ column_name }})) in ('null', 'n/a', '', 'none') then null
        else trim(lower({{ column_name }}))
    end
{% endmacro %}
