-- Question: do exercises I repeat actually progress?
-- Grain: one row per exercise done in at least two sessions with a rep count.
-- Measure: total reps per session (rounds x reps). The sheet logs no weight,
-- so progression through heavier load is invisible here: a known limit.

with sessions as (
    select
        exercise_id,
        workout_id,
        workout_date,
        sum(total_reps) as session_reps
    from {{ ref('stg_workout_exercise') }}
    where repetition_type = 'reps'
      and total_reps is not null
    group by exercise_id, workout_id, workout_date
),

ordered as (
    select
        *,
        lag(session_reps) over w_asc                                    as prev_session_reps,
        row_number() over w_asc                                         as n_from_first,
        row_number() over (partition by exercise_id
                           order by workout_date desc, workout_id desc) as n_from_last
    from sessions
    window w_asc as (partition by exercise_id order by workout_date, workout_id)
),

per_exercise as (
    select
        exercise_id,
        count(*)                                                 as n_sessions,
        min(workout_date)                                        as first_date,
        max(workout_date)                                        as last_date,
        max(case when n_from_first = 1 then session_reps end)    as first_session_reps,
        max(case when n_from_last = 1 then session_reps end)     as last_session_reps,
        count(*) filter (where session_reps > prev_session_reps) as sessions_up,
        count(*) filter (where session_reps = prev_session_reps) as sessions_flat,
        count(*) filter (where session_reps < prev_session_reps) as sessions_down
    from ordered
    group by exercise_id
    having count(*) >= 2
)

select
    p.exercise_id,
    e.exercise_name,
    e.movement_patterns,
    p.n_sessions,
    p.first_date,
    p.last_date,
    p.first_session_reps,
    p.last_session_reps,
    round((100.0 * (p.last_session_reps - p.first_session_reps) / p.first_session_reps)::numeric, 1)
                                                         as change_pct,
    p.sessions_up,
    p.sessions_flat,
    p.sessions_down,
    case
        when p.last_session_reps > p.first_session_reps then 'progressing'
        when p.last_session_reps = p.first_session_reps then 'flat'
        else 'regressing'
    end                                                  as verdict
from per_exercise p
join {{ ref('stg_exercise_list') }} e using (exercise_id)
