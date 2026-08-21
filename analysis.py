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
# ANALYSIS 5 — NEW VS REPEATED EXERCISE RATIO
# ---------------------------------------------------------------------------
# Sort chronologically (by session date, then workout_id as tiebreaker for
# same-date sessions) so "first occurrence" reflects true chronological order.
df_sorted = df_clean.sort_values(["session_date", "workout_id"]).reset_index(drop=True)
df_sorted["occurrence_rank"] = df_sorted.groupby("exercise_id").cumcount()
df_sorted["is_new_exercise"] = df_sorted["occurrence_rank"] == 0

new_vs_repeat_monthly = df_sorted.set_index("session_date").resample("MS").agg(
    new_exercises=("is_new_exercise", "sum"),
    total_exercises=("is_new_exercise", "count"),
).reset_index()
new_vs_repeat_monthly["repeated_exercises"] = (
    new_vs_repeat_monthly["total_exercises"] - new_vs_repeat_monthly["new_exercises"]
)
new_vs_repeat_monthly["new_ratio"] = (
    new_vs_repeat_monthly["new_exercises"] / new_vs_repeat_monthly["total_exercises"]
).round(3)

total_unique_exercises = df_sorted["exercise_id"].nunique()
total_exercise_instances = len(df_sorted)
new_vs_repeat_summary = {
    "unique_exercises_ever_logged": total_unique_exercises,
    "total_exercise_instances": total_exercise_instances,
    "overall_new_ratio": round(df_sorted["is_new_exercise"].sum() / total_exercise_instances, 3),
}

# ---------------------------------------------------------------------------
# ANALYSIS 3 — PROGRESSIVE OVERLOAD EFFECTIVENESS
# ---------------------------------------------------------------------------
# Scope: reps-type sets only. Time-based amounts are stored as free text
# ("30 sec", "1 min") with inconsistent units, and AMRAP has no fixed count -
# neither is a reliable basis for a "did it increase" comparison. This
# narrows the analysis but keeps every number in it honest.
reps_df = df_sorted[df_sorted["workout_repetition_type"] == "reps"].copy()
reps_df["workout_repetition_amount"] = pd.to_numeric(
    reps_df["workout_repetition_amount"], errors="coerce"
)
reps_df = reps_df.dropna(subset=["workout_repetition_amount"])

overload_rows = []
for ex_id, grp in reps_df.groupby("exercise_id"):
    grp = grp.sort_values(["session_date", "workout_id"])
    if len(grp) < 3:
        continue  # need at least 3 logged instances to call it a trend
    first_amt = grp["workout_repetition_amount"].iloc[0]
    last_amt = grp["workout_repetition_amount"].iloc[-1]
    first_rounds = grp["workout_rounds"].iloc[0]
    last_rounds = grp["workout_rounds"].iloc[-1]
    delta_amt = last_amt - first_amt
    delta_rounds = last_rounds - first_rounds
    if delta_amt > 0 or (delta_amt == 0 and delta_rounds > 0):
        trend = "increased"
    elif delta_amt < 0 or (delta_amt == 0 and delta_rounds < 0):
        trend = "decreased"
    else:
        trend = "unchanged"
    overload_rows.append({
        "exercise_id": ex_id,
        "exercise_name": grp["workout_exercise_name"].iloc[-1],
        "times_logged": len(grp),
        "first_amount": first_amt,
        "last_amount": last_amt,
        "first_rounds": first_rounds,
        "last_rounds": last_rounds,
        "trend": trend,
    })

overload_df = pd.DataFrame(overload_rows).sort_values("times_logged", ascending=False)
overload_trend_counts = overload_df["trend"].value_counts().to_dict() if len(overload_df) else {}

# ---------------------------------------------------------------------------
# ANALYSIS 2 — MOVEMENT PATTERN BALANCE
# ---------------------------------------------------------------------------
catalog = pd.read_csv("data/exercise_list.csv")

# The catalog's movement_pattern field is often compound ("push/squat",
# "rotation/pull"). Use the first listed pattern as the "primary" pattern for
# a single-count breakdown -- documented simplification, not silently assumed.
def primary_pattern(val):
    if pd.isna(val):
        return None
    first = str(val).lower().split("/")[0].strip()
    # Strip parenthetical qualifiers like "(Stability)" or "(Explosive)"
    first = first.split("(")[0].strip()
    return first

catalog["primary_movement_pattern"] = catalog["exercise_movement_pattern"].apply(primary_pattern)

# Known standard patterns per the workout generator's own rotation logic
# (see code_workout_generator patternOrder in the n8n workflow).
standard_patterns = {"squat", "hinge", "push", "pull", "rotation", "carry"}
catalog["pattern_is_standard"] = catalog["primary_movement_pattern"].isin(standard_patterns)
nonstandard = catalog[~catalog["pattern_is_standard"]]
if len(nonstandard):
    quality_notes.append(
        f"{len(nonstandard)} catalog exercise(s) have a non-standard primary movement "
        f"pattern value not in the generator's own rotation set {sorted(standard_patterns)}: "
        + ", ".join(f"{r.exercise_name} ('{r.primary_movement_pattern}')" for r in nonstandard.itertuples())
        + ". Excluded from the movement-pattern chart rather than guessed."
    )

pattern_map = catalog.set_index(catalog["exercise_id"].astype(str))["primary_movement_pattern"].to_dict()
df_sorted["primary_movement_pattern"] = df_sorted["exercise_id"].astype(str).map(pattern_map)

unmatched = df_sorted["primary_movement_pattern"].isna().sum()
if unmatched:
    quality_notes.append(
        f"{unmatched} logged exercise instance(s) could not be matched to a catalog "
        f"movement pattern (exercise_id not found in catalog) -- excluded from the chart."
    )

pattern_counts = (
    df_sorted[df_sorted["primary_movement_pattern"].isin(standard_patterns)]
    ["primary_movement_pattern"].value_counts()
)
pattern_pct = (pattern_counts / pattern_counts.sum() * 100).round(1)

carry_present_in_catalog = "carry" in catalog["primary_movement_pattern"].values
if not carry_present_in_catalog:
    quality_notes.append(
        "The generator's movement-pattern rotation order includes 'carry', but zero "
        "exercises in the catalog are tagged with a 'carry' movement pattern -- the "
        "rotation logic can never actually place a carry exercise."
    )

# ---------------------------------------------------------------------------
# CHARTS
# ---------------------------------------------------------------------------
plt.style.use("seaborn-v0_8-whitegrid")

# Chart 1: sessions per month + average exercises per session per month
fig, ax1 = plt.subplots(figsize=(10, 5))
ax1.bar(monthly["session_date"], monthly["sessions"], width=15, color="#4C72B0", alpha=0.7, label="Sessions")
ax1.set_ylabel("Sessions per month", color="#4C72B0")
ax1.set_xlabel("Month")
ax2 = ax1.twinx()
ax2.plot(monthly["session_date"], monthly["avg_exercises_per_session"], color="#8172B2", marker="o",
         label="Avg exercises per session")
ax2.set_ylabel("Avg exercises per session", color="#8172B2")
ax1.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
fig.suptitle("Training frequency and session complexity, by month")
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

# Chart 4: exercises per session trend (per-session granularity, complements the
# monthly average in chart 1)
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

# Chart 5: new vs repeated exercises per month (stacked bar)
fig, ax = plt.subplots(figsize=(10, 5))
ax.bar(new_vs_repeat_monthly["session_date"], new_vs_repeat_monthly["repeated_exercises"],
       width=15, color="#4C72B0", alpha=0.8, label="Repeated exercise")
ax.bar(new_vs_repeat_monthly["session_date"], new_vs_repeat_monthly["new_exercises"],
       width=15, bottom=new_vs_repeat_monthly["repeated_exercises"], color="#DD8452", alpha=0.9,
       label="New exercise (first time logged)")
ax.set_title("New vs repeated exercises, by month")
ax.set_xlabel("Month")
ax.set_ylabel("Exercise instances")
ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
ax.legend()
fig.tight_layout()
fig.savefig("chart_5_new_vs_repeated.png", dpi=150)
plt.close(fig)

# Chart 6: progressive overload — trend outcome for exercises logged 3+ times (reps-type only)
fig, ax = plt.subplots(figsize=(8, 5))
if overload_trend_counts:
    order = ["increased", "unchanged", "decreased"]
    colors = {"increased": "#55A868", "unchanged": "#8C8C8C", "decreased": "#C44E52"}
    vals = [overload_trend_counts.get(k, 0) for k in order]
    ax.bar(order, vals, color=[colors[k] for k in order])
    for i, v in enumerate(vals):
        ax.text(i, v + 0.1, str(v), ha="center")
ax.set_title(f"Reps trend, first vs last logged (exercises logged 3+ times, reps-type only, n={len(overload_df)})")
ax.set_ylabel("Number of exercises")
fig.tight_layout()
fig.savefig("chart_6_progressive_overload.png", dpi=150)
plt.close(fig)

# Chart 7: movement pattern balance — actual distribution of logged exercise instances
fig, ax = plt.subplots(figsize=(9, 5))
order = ["squat", "hinge", "push", "pull", "rotation", "carry"]
vals = [pattern_counts.get(p, 0) for p in order]
pcts = [pattern_pct.get(p, 0) for p in order]
bar_colors = ["#4C72B0" if v > 0 else "#DDDDDD" for v in vals]
ax.bar(order, vals, color=bar_colors)
for i, (v, p) in enumerate(zip(vals, pcts)):
    label = f"{v}\n({p}%)" if v > 0 else "0\n(not in\ncatalog)"
    ax.text(i, v + max(vals) * 0.02, label, ha="center", fontsize=9)
ax.set_title("Movement pattern balance: logged exercise instances by primary pattern")
ax.set_ylabel("Exercise instances")
fig.tight_layout()
fig.savefig("chart_7_movement_pattern_balance.png", dpi=150)
plt.close(fig)

# ---------------------------------------------------------------------------
# OUTPUT
# ---------------------------------------------------------------------------
session_agg.to_csv("session_level_summary.csv", index=False)
monthly.to_csv("monthly_summary.csv", index=False)
new_vs_repeat_monthly.to_csv("new_vs_repeated_monthly.csv", index=False)
overload_df.to_csv("progressive_overload_by_exercise.csv", index=False)

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

print("\n=== NEW VS REPEATED SUMMARY ===")
for k, v in new_vs_repeat_summary.items():
    print(f"{k}: {v}")
print(new_vs_repeat_monthly.to_string(index=False))

print("\n=== PROGRESSIVE OVERLOAD SUMMARY (reps-type, logged 3+ times) ===")
print(f"Exercises meeting threshold: {len(overload_df)}")
print(f"Trend counts: {overload_trend_counts}")
print(overload_df.to_string(index=False))

print("\n=== MOVEMENT PATTERN BALANCE ===")
print(pattern_counts.to_string())
print("\nPercent of logged instances:")
print(pattern_pct.to_string())

pattern_counts.to_frame("instances").join(pattern_pct.to_frame("pct")).to_csv(
    "movement_pattern_balance.csv"
)

print("\nCharts written: chart_1_volume_by_month.png, chart_2_rounds_per_session.png, "
      "chart_3_consistency_gaps.png, chart_4_exercises_per_session.png, "
      "chart_5_new_vs_repeated.png, chart_6_progressive_overload.png, "
      "chart_7_movement_pattern_balance.png")
