-- One row per logged exercise in a workout (grain: one row of the workout_exercise tab).
-- Parses the mixed repetition amount ("12", "amrap", "30 sec", "1 min") into
-- separate numeric columns so the marts can do arithmetic on it.

with source as (
    select * from {{ source('raw', 'workout_exercise') }}
),

typed as (
    select
        _source_row                                   as source_row,
        cast(workout_id as integer)                   as workout_id,
        cast(workout_date as date)                    as workout_date,
        cast(workout_type_id as integer)              as workout_type_id,
        cast(exercise_id as integer)                  as exercise_id,
        cast(nullif(workout_rounds, '') as integer)   as rounds,
        lower(trim(workout_repetition_type))          as repetition_type,
        lower(trim(workout_repetition_amount))        as repetition_amount_raw,
        workout_exercise_name                         as exercise_name_logged
    from source
),

parsed as (
    select
        *,
        case
            when repetition_type = 'reps' and repetition_amount_raw ~ '^\d+$'
                then cast(repetition_amount_raw as integer)
        end as reps_per_round,
        case
            when repetition_amount_raw ~ '^\d+\s*(s|sec|secs|second|seconds)$'
                then cast(substring(repetition_amount_raw from '^(\d+)') as integer)
            when repetition_amount_raw ~ '^\d+(\.\d+)?\s*(m|min|mins|minute|minutes)$'
                then cast(round(cast(substring(repetition_amount_raw from '^(\d+(?:\.\d+)?)') as numeric) * 60) as integer)
        end as seconds_per_round,
        (repetition_type = 'amrap' or repetition_amount_raw = 'amrap') as is_amrap
    from typed
)

select
    source_row,
    workout_id,
    workout_date,
    workout_type_id,
    exercise_id,
    exercise_name_logged,
    rounds,
    repetition_type,
    repetition_amount_raw,
    reps_per_round,
    seconds_per_round,
    is_amrap,
    rounds * reps_per_round    as total_reps,
    rounds * seconds_per_round as total_seconds
from parsed
