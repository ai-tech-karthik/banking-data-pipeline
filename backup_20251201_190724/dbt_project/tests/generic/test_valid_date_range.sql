{% test valid_date_range(model, column_name, min_date=None, max_date=None) %}

-- Test that a date/timestamp column falls within a valid range
-- Useful for validating loaded_at, created_at, and other temporal columns

with validation as (
    select
        {{ column_name }} as date_value,
        count(*) as violation_count
    from {{ model }}
    where 
        {{ column_name }} is null
        {% if min_date %}
        or {{ column_name }} < cast('{{ min_date }}' as timestamp)
        {% endif %}
        {% if max_date %}
        or {{ column_name }} > cast('{{ max_date }}' as timestamp)
        {% endif %}
    group by {{ column_name }}
)

select * from validation

{% endtest %}
