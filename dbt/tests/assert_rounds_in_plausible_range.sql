-- Fails for rounds outside 1-10: almost certainly a typo in the sheet.

select source_row, workout_id, exercise_id, rounds
from {{ ref('stg_workout_exercise') }}
where rounds is null or rounds not between 1 and 10
