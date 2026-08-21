# Workout Data Analysis — Volume, Consistency, Variety, Overload & Movement Balance

Analysis of 37 logged workout sessions (2026-01-31 to 2026-08-20) from a self-hosted
n8n + Google Sheets workout tracking agent. Data extracted directly from the
`workout_exercise` fact table, joined against the `exercise_list` catalog (97
exercises) for the movement-pattern analysis. Five analyses: **(1) training
frequency & session complexity**, **(2) movement pattern balance**, **(3) session
consistency / gaps**, **(4) new vs repeated exercise ratio**, and **(5) progressive
overload effectiveness** — the full original plan, all shipped.

Note: August 2026 is a partial month (data through the 20th) — its 4 sessions
are not directly comparable to a full month's count in chart 1.

## Data quality notes

Issues found and handled explicitly rather than silently dropped (see
`analysis.py` for exact logic):

- Three exact duplicate exercise rows (same workout_id + exercise_id + values)
  removed before volume calculations (`workout_id` 11, 16, 17).
- `workout_id` 16 mixes two `workout_type_id` values within one session — the
  source workflow currently allows this; each session was assigned its majority
  type for aggregation purposes.
- 3 AMRAP sets excluded from numeric volume totals (no fixed rep count exists to sum).
- Two catalog exercises have a non-standard `exercise_movement_pattern` value
  that isn't in the generator's own rotation set (squat/hinge/push/pull/rotation/carry):
  **Skaters** is tagged `"power"` (a duplicate of its intensity_type, not a movement
  pattern) and **weighted box step up transfer** is tagged `"step"`. Both excluded
  from the movement-pattern chart rather than force-mapped to a guessed pattern.
- **`carry` is unreachable in the generator.** `code_workout_generator`'s
  movement-pattern rotation explicitly includes `carry`, but zero exercises in
  the 97-exercise catalog are tagged with that pattern — that branch of the
  rotation logic can never actually place an exercise.

An earlier version of this dataset had development artifacts (sessions sharing
one date, one misdated row) from testing the GENERATE/MODIFY flow, corrected
at the source in Google Sheets before this analysis was run. All 37 sessions
now have distinct dates.

## Findings

**Frequency and complexity move independently.** March had the most sessions
of any month (10) but the lowest average exercise count per session (8.8) —
the opposite of February and May, which had fewer, denser sessions (~10.5
exercises each). A month that "trains a lot" isn't necessarily a month with
harder individual sessions. (Reps volume — rounds x reps — was considered as
a chart metric but dropped: it silently excludes every time-based exercise,
a meaningful share of what's logged here, and reads as a load metric while
only covering part of the load. It's still available per-session in
`session_level_summary.csv` with that caveat in mind.)

**Consistency:** median gap between sessions is **4 days**, mean 5.6 days
across 37 sessions over 201 days — noticeably more frequent than once a week.
Two gaps exceed two weeks (max 22 days), so the pattern has real
interruptions rather than being a metronomic routine.

**Exercise variety front-loaded, then flattened.** 91% of exercises logged in
February were new to the catalog; by April that had dropped under 10%, and it
stays there (1–7%) through August. Of 97 unique exercises ever logged, only
26% of all logged instances were a first-time exercise overall. Early months
were catalog-building; recent months draw almost entirely on exercises
already known to the system.

**Progressive overload isn't visibly happening.** Of 50 exercises logged 3+
times, **37 (74%) showed no change** in reps or rounds between their first
and last logged instance — only 7 increased, 6 decreased. The workout
generator's `volume_logic` defaults to `"same"` and progressive mode has to
be explicitly requested; this data is consistent with "same" being what
happens in practice almost regardless of intent. Scope: reps-type sets only
(3+ logged instances) — time-based amounts use inconsistent free-text units
("30 sec", "1 min") and AMRAP has no fixed count, so neither is a reliable
basis for a first-vs-last comparison.

**Movement pattern balance skews squat-heavy, and `carry` is structurally
absent.** Of 358 logged exercise instances with a valid catalog match, squat
patterns account for 29.1% versus rotation's 13.4% — more than double.
More notable: the generator's own selection logic rotates through
`['squat', 'hinge', 'push', 'pull', 'rotation', 'carry']`, but no exercise in
the 97-exercise catalog is tagged `carry` — meaning that part of the rotation
logic has been dead code since the catalog was built. This is a system design
finding as much as a training-pattern one: the intended balancing mechanism
can't do what it's designed to do for one full pattern category.

## Files

| File | Contents |
|---|---|
| `data/workout_exercise.csv` | Raw fact table export (authoritative, full) |
| `data/exercise_list.csv` | Exercise catalog dimension table, all 97 exercise IDs |
| `analysis.py` | Full pipeline: load -> data quality pass -> volume parsing -> aggregation -> charts |
| `session_level_summary.csv` | One row per session: rounds, reps volume, time volume, exercise count |
| `monthly_summary.csv` | Monthly rollup |
| `new_vs_repeated_monthly.csv` | New vs repeated exercise counts, by month |
| `progressive_overload_by_exercise.csv` | First-vs-last reps/rounds trend per exercise (3+ logs, reps-type) |
| `movement_pattern_balance.csv` | Logged exercise instance count and % by primary movement pattern |
| `chart_1_volume_by_month.png` | Sessions/month + avg exercises per session/month |
| `chart_2_rounds_per_session.png` | Total rounds per session, chronological |
| `chart_3_consistency_gaps.png` | Days-since-last-session per session (red = >14 day gap) |
| `chart_4_exercises_per_session.png` | Exercise count per session, chronological (per-session view; chart 1 shows the monthly average of this) |
| `chart_5_new_vs_repeated.png` | New vs repeated exercise instances, by month |
| `chart_6_progressive_overload.png` | Reps trend outcome (increased/unchanged/decreased) for repeated exercises |
| `chart_7_movement_pattern_balance.png` | Logged exercise instances by primary movement pattern |

## Reproduce

```
pip install pandas matplotlib
python3 analysis.py
```

## Simplifications worth knowing about

- **Primary movement pattern only.** Many catalog exercises have compound
  patterns (e.g. `"push/squat"`, `"rotation/pull"`). This analysis uses only
  the first-listed pattern per exercise for a clean single-count breakdown —
  a real simplification, not a hidden one. A finer-grained version would
  split credit across all listed patterns per exercise.
- **Reps-only overload analysis.** See the progressive overload finding above.
