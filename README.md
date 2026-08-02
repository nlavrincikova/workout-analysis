# Workout Data Analysis — Volume & Consistency

Analysis of 33 logged workout sessions (2026-01-31 to 2026-07-31) from a self-hosted
n8n + Google Sheets workout tracking agent. Data extracted directly from the
`workout_exercise` fact table. Two analyses, chosen deliberately over a larger
planned set to ship something complete rather than partial: **(1) training volume
over time** and **(2) session consistency / gaps between workouts**.

## Data quality notes

A handful of source-data issues were found and handled explicitly rather than
silently dropped (see `analysis.py` for exact logic):

- Three exact duplicate exercise rows (same workout_id + exercise_id + values)
  removed before volume calculations (`workout_id` 11, 16, 17).
- `workout_id` 16 mixes two `workout_type_id` values within one session — the
  source workflow currently allows this; each session was assigned its majority
  type for aggregation purposes.
- 3 AMRAP sets excluded from numeric volume totals (no fixed rep count exists to sum).

Two earlier versions of this dataset had, respectively, six sessions sharing
one date plus one row misdated to 2024, and later two July sessions sharing
one date — all development artifacts from testing the GENERATE/MODIFY flow,
corrected at the source in Google Sheets before this analysis was run. Noted
here for transparency, not because they still affect the numbers below: all
33 sessions now have distinct dates.

## Findings

Monthly volume (rounds x reps) grew steadily from January through March
(259 -> 1,674 -> 2,911), settled into a lower, more stable range of roughly
850–1,250 from April through June, then picked back up in July (1,521) with
5 sessions — the highest monthly session count since March.

Consistency: median gap between sessions is **4 days**, mean 5.7 days across
33 sessions over 181 days — noticeably more frequent than once a week. There
are two gaps over two weeks (max 22 days), so the pattern has real
interruptions rather than being a metronomic routine. Session complexity
(exercises per session) stayed in the 9–11 range throughout, so structure was
consistent even during the higher- and lower-frequency stretches.

## Files

| File | Contents |
|---|---|
| `data/workout_exercise.csv` | Raw fact table export |
| `analysis.py` | Full pipeline: load -> data quality pass -> volume parsing -> aggregation -> charts |
| `session_level_summary.csv` | One row per session: rounds, reps volume, time volume, exercise count |
| `monthly_summary.csv` | Monthly rollup |
| `chart_1_volume_by_month.png` | Sessions/month + reps volume/month |
| `chart_2_rounds_per_session.png` | Total rounds per session, chronological |
| `chart_3_consistency_gaps.png` | Days-since-last-session per session (red = >14 day gap) |
| `chart_4_exercises_per_session.png` | Exercise count per session, chronological |

## Reproduce

```
pip install pandas matplotlib
python3 analysis.py
```

## Not in this version (deliberately deferred)

Movement pattern balance, progressive-overload effectiveness, and
new-vs-repeated exercise ratio were part of the original 5-analysis plan.
Cut here to ship a complete, honest v1 rather than a partial v2. Progressive
overload in particular needs cleaner handling of the mixed reps/time
repetition-amount format before it's worth doing.
