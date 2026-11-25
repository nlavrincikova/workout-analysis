-- Each month's pattern shares must add up to 100% (allowing for rounding).

select month, sum(pct_of_month) as total_pct
from {{ ref('mart_movement_pattern_balance') }}
group by month
having abs(sum(pct_of_month) - 100) > 1
