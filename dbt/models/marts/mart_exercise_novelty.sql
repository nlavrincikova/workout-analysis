-- Question: how much of each workout is new versus repeated?
-- Grain: one row per workout.
-- "New" = the exercise appears for the first time in the whole log in this workout.

with workout_exercises as (
    select distinct workout_id, workout_date, exercise_id
    from {{ ref('stg_workout_exercise') }}
),

first_seen as (
    select
        exercise_id,
        (array_agg(workout_id order by workout_date, workout_id))[1] as first_workout_id
    from workout_exercises
    group by exercise_id
),

per_workout as (
    select
        w.workout_id,
        w.workout_date,
        count(*)                                                  as n_exercises,
        count(*) filter (where w.workout_id = f.first_workout_id) as n_new_exercises
    from workout_exercises w
    join first_seen f using (exercise_id)
    group by w.workout_id, w.workout_date
)

select
    workout_id,
    workout_date,
    n_exercises,
    n_new_exercises,
    n_exercises - n_new_exercises                                as n_repeated_exercises,
    round((100.0 * n_new_exercises / n_exercises)::numeric, 1)   as pct_new,
    sum(n_new_exercises) over (order by workout_date, workout_id) as cumulative_distinct_exercises
from per_workout
