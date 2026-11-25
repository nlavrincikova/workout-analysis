-- Fails for any logged exercise whose repetition amount the parser did not understand,
-- e.g. a new format like "45s each side". Add the format to stg_workout_exercise.

select source_row, repetition_type, repetition_amount_raw
from {{ ref('stg_workout_exercise') }}
where (repetition_type = 'reps' and reps_per_round is null)
   or (repetition_type = 'time' and seconds_per_round is null)
