-- Question: do exercises I repeat actually progress?
-- Grain: one row per exercise and measure, for exercises done in at least two sessions.
-- Measure: total reps per session (rounds x reps) for rep-counted exercises, and
-- total seconds per session (rounds x seconds) for time-based exercises (planks, holds).
-- The sheet logs no weight, so progression through heavier load is invisible here: a known limit.

with sessions as (
    select
        exercise_id,
        workout_id,
        workout_date,
        case repetition_type
            when 'reps' then 'reps'
            when 'time' then 'seconds'
        end                                   as measure,
        sum(case repetition_type
                when 'reps' then total_reps
                when 'time' then total_seconds
            end)                              as session_value
    from {{ ref('stg_workout_exercise') }}
    where (repetition_type = 'reps' and total_reps is not null)
       or (repetition_type = 'time' and total_seconds is not null)
    group by exercise_id, workout_id, workout_date, repetition_type
),

ordered as (
    select
        *,
        lag(session_value) over w_asc                                   as prev_session_value,
        row_number() over w_asc                                         as n_from_first,
        row_number() over (partition by exercise_id, measure
                           order by workout_date desc, workout_id desc) as n_from_last
    from sessions
    window w_asc as (partition by exercise_id, measure order by workout_date, workout_id)
),

per_exercise as (
    select
        exercise_id,
        measure,
        count(*)                                                   as n_sessions,
        min(workout_date)                                          as first_date,
        max(workout_date)                                          as last_date,
        max(case when n_from_first = 1 then session_value end)     as first_session_value,
        max(case when n_from_last = 1 then session_value end)      as last_session_value,
        count(*) filter (where session_value > prev_session_value) as sessions_up,
        count(*) filter (where session_value = prev_session_value) as sessions_flat,
        count(*) filter (where session_value < prev_session_value) as sessions_down
    from ordered
    group by exercise_id, measure
    having count(*) >= 2
)

select
    p.exercise_id,
    e.exercise_name,
    e.movement_patterns,
    p.measure,
    p.n_sessions,
    p.first_date,
    p.last_date,
    p.first_session_value,
    p.last_session_value,
    round((100.0 * (p.last_session_value - p.first_session_value) / p.first_session_value)::numeric, 1)
                                                         as change_pct,
    p.sessions_up,
    p.sessions_flat,
    p.sessions_down,
    case
        when p.last_session_value > p.first_session_value then 'progressing'
        when p.last_session_value = p.first_session_value then 'flat'
        else 'regressing'
    end                                                  as verdict
from per_exercise p
join {{ ref('stg_exercise_list') }} e using (exercise_id)