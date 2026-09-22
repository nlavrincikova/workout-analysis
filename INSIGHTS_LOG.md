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

## 2026-09-22 — v3: dataset refresh, two pipeline bugs found and fixed

**Dataset scope:** 41 sessions, 2026-01-31 to 2026-09-05. 99 exercises in the
catalog (up from 97 in v2). Up from v2's 37 sessions / 2026-08-20 cutoff.

**What changed since v2:** Pulled the current `workout_exercise` and
`exercise_list` tabs directly from Sheets (not the Drive connector — it
reproduced the same silent truncation the v2 entry already flagged, this time
cutting off at `workout_id` 28; abandoned in favor of a manual export).
Two real pipeline bugs surfaced against the fresh export, neither present in
the v2 run, both fixed in `analysis.py`:
- `exercise_list.csv` isn't valid UTF-8 — an AI-generated exercise description
  contains a Windows curly-apostrophe (`0x92`), which the default `pd.read_csv`
  call can't decode. Fixed by reading it with `encoding="cp1252"`.
- The fresh `workout_exercise.csv` export carries ~4,580 trailing all-blank
  rows below the real data (from calculated columns spanning a fixed sheet
  range). Left in place, the stray `NaN`s silently upcast `exercise_id` to
  `float64`, which broke the movement-pattern join against the catalog's
  `int64` IDs — every row went unmatched and the chart came back empty, with
  no error. Fixed by dropping rows with a blank `workout_id` and casting
  `workout_id`/`exercise_id` back to `int` immediately after load. Worth
  watching on every future export, not just this one.
Also restored the `data/` subfolder for the two source CSVs — it had been
flattened to the repo root at some point, out of sync with both this repo's
own `README.md` and `analysis.py`, which both expected `data/`.

**Key findings:**
- Both v2 headline findings hold up on 4 more sessions and 3 more weeks, not
  just a smaller sample: progressive overload is still flat (75.5% unchanged,
  40 of 53 qualifying exercises, up from 74%/37-of-50), and the squat/rotation
  skew is essentially unchanged (squat 29.3% vs rotation 12.4%, versus
  29.1%/13.4% in v2). `carry` is still absent from the catalog.
- **All 8 new sessions since v2 are full body** (`workout_type_id` 1) — no
  lower body, upper body, or core session in three weeks. September's
  new-exercise ratio is 0% (0 of 15 logged instances), down from August's
  already-low 2.7%.
- **Catalog `exercise_frequency` can drift from actual logged history.**
  Plank (`exercise_id` 98) shows `exercise_frequency` 3 in the catalog but
  only 2 real rows in `workout_exercise`. Off by one; cause not investigated.
- **`needs_new_exercise` can leave a phantom catalog entry.** Kettlebell Swing
  (`exercise_id` 99) is in the catalog with `exercise_frequency` 1 but has
  zero rows in `workout_exercise` — it has never actually been logged. Reads
  as a MODIFY `add` that created the catalog row and was then never confirmed
  into a session; the catalog write and the log write aren't atomic. Same
  class of risk as the already-tracked `staged_workout` cleanup gap, but on
  the catalog itself, and not yet tracked anywhere. Found by spot-checking
  the two exercises added since v2, not by an automated check — worth adding
  a "frequency vs. actual row count" pass to `analysis.py`'s data quality
  section in a future run if this keeps happening, but not built this round.

**Open question for next run:** the Plank frequency drift and the Kettlebell
Swing phantom entry were both found by hand-checking the two newest catalog
rows. As the catalog grows, that stops being a viable per-run check — decide
whether a frequency-vs-actual-count reconciliation belongs in `analysis.py`'s
automated quality pass before the next refresh.

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
