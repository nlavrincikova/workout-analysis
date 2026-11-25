with source as (
    select * from {{ source('raw', 'workout_type') }}
)

select
    cast(workout_type_id as integer) as workout_type_id,
    lower(trim(workout_type_name))   as workout_type_name
from source
