# workout-analysis v2: setup and run (Windows, PowerShell)

Pipeline: Google Sheet tabs (CSV) → `loader/load_raw.py` → Postgres `raw` schema (text) → dbt staging views → 3 dbt marts → dbt tests. GitHub Actions runs the same chain on synthetic fixtures on every push.

```
data/raw/*.csv ──► raw.* (text) ──► analytics.stg_* (typed, parsed) ──► analytics.mart_* ──► your README findings
                       ▲ pytest                    ▲ dbt tests                ▲ dbt tests
```

**Why dbt v1, not v2:** dbt v2 (the Rust rewrite, now the default for new installs) does not support Postgres yet, so `requirements.txt` pins dbt Core v1, which dbt Labs says remains fully supported. The project already uses v2-style syntax (`data_tests`, test `arguments`) and parses with zero deprecation warnings, so moving to v2 later is a small step. When you meet dbt at work, the SQL and YAML are the same.

## 1. Copy into your repo

Copy everything from this folder into the root of your local `workout-analysis` repo, next to your v1 notebook. Nothing in v1 is replaced.

## 2. One-time setup

```powershell
cd <your workout-analysis folder>
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Your Postgres runs on port 5433, which is the default here. Create the database once in pgAdmin, or:

```powershell
psql -h localhost -p 5433 -U postgres -c "create database workout;"
```

Set the password for this PowerShell session (it is never written to a file):

```powershell
$env:PGPASSWORD = "<your postgres password>"
```

## 3. Check it works on the test data first

```powershell
pytest -v
python loader/load_raw.py --data-dir tests/fixtures
dbt build --project-dir dbt --profiles-dir dbt
```

Expected: 7 pytest passes and `Done. PASS=30 ... ERROR=0`.

## 4. Run on your real data

1. Export the three tabs as CSV into `data/raw/` (see `data/raw/README.md`).
2. Run:

```powershell
python loader/load_raw.py
dbt build --project-dir dbt --profiles-dir dbt
```

If a dbt test fails on your real data, **that is a finding, not a bug in the pipeline**: it means the sheet contains something the tests consider wrong. Typical ones:
- `relationships_..._exercise_id` → an exercise was logged that is not in `exercise_list` (likely the n8n "new exercise" path).
- `assert_repetition_amount_parsed` → a repetition format the parser does not know yet; add it to `stg_workout_exercise.sql`.
- `assert_rounds_in_plausible_range` → a typo in rounds.

Write down what you found and how you fixed it. That becomes the best paragraph in your README.

## 5. Get your findings

```sql
-- Balance: which patterns dominate, which are missing?
select * from analytics.mart_movement_pattern_balance order by month, pct_of_month desc;

-- Progression: how many repeated exercises progress vs. stay flat?
select verdict, count(*) from analytics.mart_progressive_overload group by verdict;

-- Novelty: is the generator still introducing new exercises?
select * from analytics.mart_exercise_novelty order by workout_date;
```

## 6. Publish (by 30 Nov)

1. Add a **v2** section to the repo README: the pipeline diagram above, 3 findings (one per mart, with a number each), and one known limitation (weight is not logged, so progression = rounds × reps only).
2. Commit and push. Open the **Actions** tab on GitHub and check the `ci` run is green.
3. Add the CI badge at the top of the README:
   `![ci](https://github.com/nlavrincikova/workout-analysis/actions/workflows/ci.yml/badge.svg)`

## Guardrails (from your plan)

- The pipeline only **reads** your Sheet. No changes to n8n or the Sheet backend until v2 is public.
- No extra tools (Airflow, Docker, Streamlit, a direct Google API connection) before 30 Nov. CSV export is a deliberate choice.
