{% macro standardize_column_name(column_name) %}
{#
    Standardize column names to follow snake_case convention.
    
    This macro converts column names to lowercase, replaces spaces and hyphens
    with underscores, and removes other special characters.
    
    Args:
        column_name (string): The column name to standardize
        
    Returns:
        string: Standardized column name in snake_case format
        
    Example:
        {{ standardize_column_name('Customer Name') }} -> 'customer_name'
        {{ standardize_column_name('Account-ID') }} -> 'account_id'
        {{ standardize_column_name('Has Loan?') }} -> 'has_loan'
#}
    {{- column_name | lower | replace(' ', '_') | replace('-', '_') | regex_replace('[^a-z0-9_]', '') -}}
{% endmacro %}
