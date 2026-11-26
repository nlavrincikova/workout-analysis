-- A workout is one session on one day. Fails if a workout_id carries more than one date,
-- e.g. two sessions accidentally logged under the same id.

select workout_id, count(distinct workout_date) as dates
from {{ ref('stg_workout_exercise') }}
group by workout_id
having count(distinct workout_date) > 1