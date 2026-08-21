# Analysis Insights Log

Running record of what each analysis run found, kept separate from the README
(which describes the current state of the project) so past findings aren't
overwritten as the dataset grows. New entry each time `analysis.py` is run
against a meaningfully updated dataset — not every minor chart tweak.

---

## 2026-08-21 — v2: all 5 original analyses complete

**Dataset scope:** 37 sessions, 2026-01-31 to 2026-08-20. 97 exercises in the
catalog. Up from the v1 scope of 28 sessions / 2 analyses.

**What changed since v1:** Added the three originally-deferred analyses
(movement pattern balance, new vs repeated exercise ratio, progressive
overload effectiveness). Pulled the full authoritative `workout_exercise` and
`exercise_list` exports directly from Google Sheets (earlier pulls via the
Drive connector were silently truncated around row ~230, which had been
masking part of the dataset without any error — worth remembering as a
standing risk for future pulls, not just a one-time fix). Revised chart 1 to
pair session count with average session complexity per month instead of a
reps-volume line, which was misleading (excluded all time-based exercises).

**Key findings:**
- Session frequency and session complexity move independently — March had
  the most sessions (10) but the least complex ones on average (8.8
  exercises); February/May had fewer, denser sessions (~10.5 exercises).
- Median gap between sessions: 4 days. Two gaps exceeded two weeks
  (max 22 days) — real interruptions, not a strict weekly routine.
- Exercise variety was front-loaded: 91% new exercises in Feb, under 10% from
  April onward. 26% of all logged instances overall were a first-time
  exercise.
- **Progressive overload is not visibly happening.** 74% of repeated
  exercises (37 of 50, reps-type, logged 3+ times) showed zero change in
  reps or rounds between first and last log.
- **`carry` movement pattern is unreachable in the generator** — the
  rotation logic references it, but zero catalog exercises are tagged
  `carry`. Squat (29.1%) is logged roughly 2x as often as rotation (13.4%).
  Two catalog rows also had malformed movement-pattern values (Skaters:
  `"power"`, weighted box step up transfer: `"step"`) — excluded from the
  chart rather than guessed.

**Open question for next run:** none of the analyses currently account for
`workout_id` 31/32 originally sharing a date before being corrected in
Sheets — worth a quick sanity check next time new sessions are pulled, in
case similar same-day duplicates recur during future agent testing.

---

## Template for future entries

```
## YYYY-MM-DD — <short label for what changed>

**Dataset scope:** N sessions, date range. N exercises in catalog.

**What changed since last entry:** ...

**Key findings:** (only what's new or materially different from last entry —
don't restate unchanged findings)

**Open question for next run:** ...
```
