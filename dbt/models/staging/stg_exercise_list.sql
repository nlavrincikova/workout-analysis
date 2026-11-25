-- One row per exercise in the catalog, typed and normalised.
-- movement_patterns keeps the compound pattern ("squat/push/pull") without the
-- modifier; movement_modifier holds what was in brackets ("stability", "explosive").

with source as (
    select * from {{ source('raw', 'exercise_list') }}
)

select
    cast(exercise_id as integer)                                   as exercise_id,
    exercise_name,
    exercise_name_normalized,
    lower(exercise_body_part_focus)                                as body_part_focus,
    exercise_primary_equipment                                     as primary_equipment,
    exercise_movement_pattern                                      as movement_pattern_raw,
    lower(regexp_replace(
        trim(split_part(exercise_movement_pattern, '(', 1)),
        '\s*/\s*', '/', 'g'
    ))                                                             as movement_patterns,
    lower(nullif(trim(substring(exercise_movement_pattern from '\(([^)]*)\)')), ''))
                                                                   as movement_modifier,
    lower(exercise_intensity_type)                                 as intensity_type,
    cast(nullif(exercise_frequency, '') as integer)                as exercise_frequency,
    _source_row                                                    as source_row
from source
