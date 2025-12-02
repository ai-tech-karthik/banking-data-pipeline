{% test positive_value(model, column_name) %}

-- Test that a numeric column contains only positive values (> 0)
-- This is useful for validating amounts, balances, counts, etc.

select
    {{ column_name }} as value,
    count(*) as violation_count
from {{ model }}
where {{ column_name }} <= 0
   or {{ column_name }} is null
group by {{ column_name }}

{% endtest %}
