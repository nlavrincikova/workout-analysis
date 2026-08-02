"""
Workout AI Agent - Analysis 1 (Volume over time) & Analysis 4 (Consistency / gaps)
Data source: Google Sheets export (workout_exercise fact table), 28 logged sessions,
2026-01-31 through 2026-06-29.
"""

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import re

pd.set_option("display.max_rows", 200)

# ---------------------------------------------------------------------------
# LOAD
# ---------------------------------------------------------------------------
df = pd.read_csv("data/workout_exercise.csv")
df["workout_date"] = pd.to_datetime(df["workout_date"])

# ---------------------------------------------------------------------------
# DATA QUALITY PASS (documented, not silently dropped)
# ---------------------------------------------------------------------------
quality_notes = []

# 1) Session-level date should be a single value per workout_id. Find sessions
#    where rows disagree on the date (copy/paste or manual entry error).
date_mode = df.groupby("workout_id")["workout_date"].agg(lambda s: s.mode().iloc[0])
df["session_date"] = df["workout_id"].map(date_mode)
mismatches = df[df["workout_date"] != df["session_date"]]
for _, r in mismatches.iterrows():
    quality_notes.append(
        f"workout_id {r['workout_id']}: row date {r['workout_date'].date()} does not match "
        f"session date {r['session_date'].date()} (exercise: {r['workout_exercise_name']}) -> "
        f"row date treated as a data entry error, session_date used instead."
    )

# 2) Exact duplicate rows within a session (same workout_id + exercise_id + all values)
dupe_mask = df.duplicated(subset=["workout_id", "exercise_id", "workout_rounds",
                                   "workout_repetition_type", "workout_repetition_amount"], keep="first")
if dupe_mask.any():
    for _, r in df[dupe_mask].iterrows():
        quality_notes.append(
            f"workout_id {r['workout_id']}: duplicate row for exercise_id {r['exercise_id']} "
            f"({r['workout_exercise_name']}) -> removed for volume calculations."
        )
df_clean = df[~dupe_mask].copy()

# 3) Sessions split across two workout_type_id values (e.g. 16, 17) -> log as a modeling
#    limitation of the source system (one workout_id should be one workout_type).
mixed_type = df_clean.groupby("workout_id")["workout_type_id"].nunique()
mixed_ids = mixed_type[mixed_type > 1].index.tolist()
if mixed_ids:
    quality_notes.append(
        f"workout_id(s) {mixed_ids}: rows within the same session carry more than one "
        f"workout_type_id. Source workflow allows this; for aggregation each session is "
        f"assigned its majority workout_type_id."
    )
type_mode = df_clean.groupby("workout_id")["workout_type_id"].agg(lambda s: s.mode().iloc[0])
df_clean["session_type_id"] = df_clean["workout_id"].map(type_mode)

# ---------------------------------------------------------------------------
# VOLUME PARSING
# ---------------------------------------------------------------------------
def parse_time_to_seconds(val):
    val = str(val).lower().strip()
    m = re.match(r"([\d.]+)\s*(sec|second|seconds|min|minute|minutes)?", val)
    if not m:
        return None
    num = float(m.group(1))
    unit = m.group(2) or "sec"
    return num * 60 if unit.startswith("min") else num

def row_volume(row):
    """Returns (reps_volume, time_volume_sec). AMRAP rows are counted as a set
    performed but excluded from numeric volume (no bounded rep count exists)."""
    rtype = row["workout_repetition_type"]
    rounds = row["workout_rounds"]
    amt = row["workout_repetition_amount"]
    if rtype == "reps":
        try:
            return rounds * float(amt), 0.0
        except ValueError:
            return 0.0, 0.0
    if rtype == "time":
        sec = parse_time_to_seconds(amt)
        return 0.0, rounds * sec if sec is not None else 0.0
    return 0.0, 0.0  # amrap

df_clean[["reps_volume", "time_volume_sec"]] = df_clean.apply(
    lambda r: pd.Series(row_volume(r)), axis=1
)
amrap_sets = (df_clean["workout_repetition_type"] == "amrap").sum()
quality_notes.append(
    f"{amrap_sets} AMRAP set(s) logged with repetition_amount='amrap' -> excluded from "
    f"numeric volume sums (no fixed rep count to sum); counted separately as 'AMRAP sets'."
)

# ---------------------------------------------------------------------------
# ANALYSIS 1 — VOLUME OVER TIME (session-level, then weekly/monthly rollup)
# ---------------------------------------------------------------------------
session_agg = df_clean.groupby(["workout_id", "session_date"]).agg(
    num_exercises=("exercise_id", "count"),
    total_rounds=("workout_rounds", "sum"),
    reps_volume=("reps_volume", "sum"),
    time_volume_sec=("time_volume_sec", "sum"),
    amrap_sets=("workout_repetition_type", lambda s: (s == "amrap").sum()),
).reset_index().sort_values("session_date")

session_agg["time_volume_min"] = session_agg["time_volume_sec"] / 60

weekly = session_agg.set_index("session_date").resample("W-MON").agg(
    sessions=("workout_id", "count"),
    total_rounds=("total_rounds", "sum"),
    reps_volume=("reps_volume", "sum"),
    time_volume_min=("time_volume_min", "sum"),
).reset_index()

monthly = session_agg.set_index("session_date").resample("MS").agg(
    sessions=("workout_id", "count"),
    total_rounds=("total_rounds", "sum"),
    reps_volume=("reps_volume", "sum"),
    time_volume_min=("time_volume_min", "sum"),
    avg_exercises_per_session=("num_exercises", "mean"),
).reset_index()

# ---------------------------------------------------------------------------
# ANALYSIS 4 — CONSISTENCY / GAPS
# ---------------------------------------------------------------------------
unique_dates = sorted(session_agg["session_date"].unique())
gaps = pd.Series(unique_dates).diff().dt.days.dropna()

gap_summary = {
    "n_sessions": len(unique_dates),
    "date_range_days": (unique_dates[-1] - unique_dates[0]).days,
    "mean_gap_days": round(gaps.mean(), 1),
    "median_gap_days": round(gaps.median(), 1),
    "max_gap_days": int(gaps.max()),
    "min_gap_days": int(gaps.min()),
    "gaps_over_14_days": int((gaps > 14).sum()),
}

# ---------------------------------------------------------------------------
# CHARTS
# ---------------------------------------------------------------------------
plt.style.use("seaborn-v0_8-whitegrid")

# Chart 1: sessions per month + reps volume per month
fig, ax1 = plt.subplots(figsize=(10, 5))
ax1.bar(monthly["session_date"], monthly["sessions"], width=15, color="#4C72B0", alpha=0.7, label="Sessions")
ax1.set_ylabel("Sessions per month", color="#4C72B0")
ax1.set_xlabel("Month")
ax2 = ax1.twinx()
ax2.plot(monthly["session_date"], monthly["reps_volume"], color="#DD8452", marker="o", label="Reps volume (rounds x reps)")
ax2.set_ylabel("Total reps volume", color="#DD8452")
ax1.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
fig.suptitle("Training frequency and reps volume by month")
fig.tight_layout()
fig.savefig("chart_1_volume_by_month.png", dpi=150)
plt.close(fig)

# Chart 2: total rounds per session over time (session-level granularity)
fig, ax = plt.subplots(figsize=(10, 5))
ax.plot(session_agg["session_date"], session_agg["total_rounds"], marker="o", color="#55A868")
ax.set_title("Total rounds logged per session, over time")
ax.set_xlabel("Session date")
ax.set_ylabel("Total rounds")
ax.xaxis.set_major_formatter(mdates.DateFormatter("%d %b"))
fig.autofmt_xdate()
fig.tight_layout()
fig.savefig("chart_2_rounds_per_session.png", dpi=150)
plt.close(fig)

# Chart 3: gap between consecutive sessions (consistency)
fig, ax = plt.subplots(figsize=(10, 5))
gap_dates = unique_dates[1:]
colors = ["#C44E52" if g > 14 else "#4C72B0" for g in gaps]
ax.bar(gap_dates, gaps, width=3, color=colors)
ax.axhline(7, color="gray", linestyle="--", linewidth=1, label="7-day reference")
ax.set_title("Days since previous session (red = gap over 14 days)")
ax.set_xlabel("Session date")
ax.set_ylabel("Gap (days)")
ax.xaxis.set_major_formatter(mdates.DateFormatter("%d %b"))
fig.autofmt_xdate()
ax.legend()
fig.tight_layout()
fig.savefig("chart_3_consistency_gaps.png", dpi=150)
plt.close(fig)

# Chart 4: exercises per session trend (proxy for session length/complexity)
fig, ax = plt.subplots(figsize=(10, 5))
ax.plot(session_agg["session_date"], session_agg["num_exercises"], marker="o", color="#8172B2")
ax.set_title("Exercises logged per session, over time")
ax.set_xlabel("Session date")
ax.set_ylabel("Number of exercises")
ax.xaxis.set_major_formatter(mdates.DateFormatter("%d %b"))
fig.autofmt_xdate()
fig.tight_layout()
fig.savefig("chart_4_exercises_per_session.png", dpi=150)
plt.close(fig)

# ---------------------------------------------------------------------------
# OUTPUT
# ---------------------------------------------------------------------------
session_agg.to_csv("session_level_summary.csv", index=False)
monthly.to_csv("monthly_summary.csv", index=False)

print("=== DATA QUALITY NOTES ===")
for n in quality_notes:
    print("-", n)

print("\n=== SESSION-LEVEL SUMMARY (head) ===")
print(session_agg.head(10).to_string(index=False))

print("\n=== MONTHLY SUMMARY ===")
print(monthly.to_string(index=False))

print("\n=== CONSISTENCY / GAP SUMMARY ===")
for k, v in gap_summary.items():
    print(f"{k}: {v}")

print("\nCharts written: chart_1_volume_by_month.png, chart_2_rounds_per_session.png, "
      "chart_3_consistency_gaps.png, chart_4_exercises_per_session.png")
