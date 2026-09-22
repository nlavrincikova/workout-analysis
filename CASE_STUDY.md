# Finding My Own System's Blind Spots — A Case Study in Data Quality

I built [workout-tracker](https://github.com/nlavrincikova/workout-tracker), a self-hosted n8n + Google
Sheets AI agent that logs my workouts through chat and suggests new ones from training history. Once it had
a few months of real data, I turned the same analytical instincts I'd use on a client dataset back on my own
system — not just "what does my training look like," but "does the system that generated this data actually
work the way I designed it to." It didn't, in two ways I hadn't noticed while building it.

## The setup

Two analysis passes, five months apart: **v2** on 37 sessions through 2026-08-20, **v3** on 41 sessions
through 2026-09-05. Same pipeline (`analysis.py` — pandas, matplotlib) run twice against a growing dataset,
which is the point: a finding that only shows up once isn't a finding, it's noise. Full numbers and methodology
in [`README.md`](./README.md); the run-by-run record of what changed and why is in [`INSIGHTS_LOG.md`](./INSIGHTS_LOG.md).

## What the training data actually says

Two things held up, essentially unchanged, across both passes:

- **Progressive overload isn't happening.** Of 53 exercises logged three or more times, 75.5% showed zero
  change in reps or rounds between their first and last logged instance (v2: 74% of 50). The generator
  defaults `volume_logic` to `"same"` and progressive mode has to be explicitly requested — this data says
  that's exactly what happens in practice, regardless of intent.
- **Training is consistent, but not evenly spread across the body.** Median gap between sessions: 4 days,
  both passes — a real, sustained habit, not sporadic. But every one of the 8 sessions logged since v2 was
  full-body. Three weeks with zero lower-body, upper-body, or core sessions.

Individually these are useful training signals. Neither is the interesting part.

## What the training data says about the system

**The catalog can silently drift from what was actually logged, and once did.** Cross-checking the two
exercises added to the catalog since v2 against their actual row counts in `workout_exercise` turned up two
integrity problems neither the app nor a casual read of the sheet would have caught: one exercise's stored
frequency was off by one against its real log count, and a second exercise existed in the catalog —
with a frequency of 1 — despite having **zero** logged instances anywhere. The likely mechanism: this has happened because of writing and deleting testing data was conducted in live document without noticing this data integrity gap.

## And two bugs in the analysis pipeline itself

Refreshing the dataset for v3 broke my own script in ways v2 never hit — a useful reminder that a pipeline
that works once isn't validated, it's untested against the next input. One exercise description contained a
Windows-style curly apostrophe that isn't valid UTF-8, which `pandas.read_csv` refused to parse. The other
was worse: the fresh Sheets export carried thousands of trailing blank rows, which silently upcast an integer
ID column to float — no crash, no error, just an empty chart where 403 data points should have been. Both are
now explicit, one-line fixes with a comment explaining why, not silent workarounds.

## Why this is the actual finding

The training insights are what the dashboard is for. The interesting result is that auditing my own system's
output caught a data-integrity gap that building and manually testing it never would
have — because both are invisible until you look at the data at volume and ask whether it's internally
consistent, not just whether the chat replies look right. That's the same question I'd ask of any client
dataset. I asked it of my own, and it held up to scrutiny in two places and failed in two others. Both are
now tracked as open issues instead of unknown unknowns.

---

**Reproduce:** `pip install pandas matplotlib && python analysis.py` — see [`README.md`](./README.md).
**System design and the n8n workflow this data comes from:** [workout-tracker](https://github.com/nlavrincikova/workout-tracker).
