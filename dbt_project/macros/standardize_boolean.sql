{% macro standardize_boolean(column_name, true_values=['yes', 'y', 'true', '1'], false_values=['no', 'n', 'false', '0', 'none']) %}
{#
    Standardize boolean values from various representations.
    
    This macro converts various string representations of boolean values
    to actual boolean types (true/false).
    
    Args:
        column_name (string): The column name or expression to standardize
        true_values (list): List of string values that represent true (default: ['yes', 'y', 'true', '1'])
        false_values (list): List of string values that represent false (default: ['no', 'n', 'false', '0', 'none'])
        
    Returns:
        SQL expression: Boolean value (true/false) or NULL
        
    Example:
        {{ standardize_boolean('has_loan') }}
        {{ standardize_boolean('is_active', true_values=['yes', '1']) }}
        
    Default true values: 'yes', 'y', 'true', '1'
    Default false values: 'no', 'n', 'false', '0', 'none'
#}
    case
        when {{ column_name }} is null then null
        when lower(trim({{ column_name }})) in ({{ "'" + true_values | join("', '") + "'" }}) then true
        when lower(trim({{ column_name }})) in ({{ "'" + false_values | join("', '") + "'" }}) then false
        else null
    end
{% endmacro %}
