-- Question: is my training balanced across movement patterns, month by month?
-- Grain: one row per month x movement pattern.
-- A compound exercise ("squat/push/pull") splits its one slot evenly across its
-- patterns (1/3 each), so every logged exercise counts exactly once per month.

with logged as (
    select * from {{ ref('stg_workout_exercise') }}
),

exercises as (
    select exercise_id, movement_patterns from {{ ref('stg_exercise_list') }}
),

split as (
    select
        cast(date_trunc('month', l.workout_date) as date)              as month,
        trim(p.pattern)                                               as movement_pattern,
        l.rounds,
        1.0 / cardinality(string_to_array(e.movement_patterns, '/'))  as slot_weight
    from logged l
    join exercises e using (exercise_id)
    cross join lateral unnest(string_to_array(e.movement_patterns, '/')) as p(pattern)
)

select
    month,
    movement_pattern,
    round(sum(slot_weight)::numeric, 2)          as exercise_slots,
    round(sum(slot_weight * rounds)::numeric, 2) as weighted_rounds,
    round(
        (100 * sum(slot_weight) / sum(sum(slot_weight)) over (partition by month))::numeric,
        1
    )                                            as pct_of_month
from split
group by month, movement_pattern
