"""Load CSV exports of the fitness_exercise_catalog Google Sheet into Postgres.

ELT convention: every column lands in schema `raw` as text, exactly as exported.
Typing, parsing and cleaning happen later, in the dbt staging models.

Usage:
    python loader/load_raw.py                      # reads data/raw/*.csv
    python loader/load_raw.py --data-dir tests/fixtures

Connection settings come from environment variables (defaults in brackets):
    PGHOST [localhost]  PGPORT [5433]  PGUSER [postgres]  PGPASSWORD []  PGDATABASE [workout]
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL, Engine

# Columns kept per tab. Anything else in the sheet (scratch calculations,
# helper columns) is dropped on purpose, so the raw layer has a stable contract.
TABLES: dict[str, list[str]] = {
    "exercise_list": [
        "exercise_id",
        "exercise_name",
        "exercise_body_part_focus",
        "exercise_primary_equipment",
        "exercise_movement_pattern",
        "exercise_intensity_type",
        "exercise_description",
        "exercise_muscles_worked",
        "exercise_key_cues_safety",
        "exercise_non_machine_alternative",
        "exercise_name_normalized",
        "exercise_frequency",
    ],
    "workout_type": ["workout_type_id", "workout_type_name"],
    "workout_exercise": [
        "workout_id",
        "workout_date",
        "workout_type_id",
        "exercise_id",
        "workout_rounds",
        "workout_repetition_type",
        "workout_repetition_amount",
        "workout_type_name",
        "workout_exercise_name",
    ],
}

RAW_SCHEMA = "raw"


class SchemaError(ValueError):
    """Raised when an exported tab no longer has the columns the pipeline expects."""


def read_tab(path: Path) -> pd.DataFrame:
    """Read one exported tab with every value as a string (no type guessing)."""
    return pd.read_csv(path, dtype=str, keep_default_na=False)


def clean_tab(df: pd.DataFrame, table: str) -> pd.DataFrame:
    """Keep the expected columns, trim whitespace, drop fully empty rows.

    Adds `_source_row`: the row number in the Google Sheet (header = row 1),
    so every raw record can be traced back to its cell range.
    """
    expected = TABLES[table]
    df = df.rename(columns=lambda c: str(c).strip())

    missing = [c for c in expected if c not in df.columns]
    if missing:
        raise SchemaError(
            f"{table}: missing column(s) {missing}. Columns found: {list(df.columns)}"
        )

    out = df[expected].copy()
    for col in expected:
        out[col] = out[col].astype(str).str.strip()

    out.insert(0, "_source_row", range(2, len(out) + 2))
    not_empty = (out[expected] != "").any(axis=1)
    return out[not_empty].reset_index(drop=True)


def get_engine() -> Engine:
    url = URL.create(
        "postgresql+psycopg2",
        username=os.getenv("PGUSER", "postgres"),
        password=os.getenv("PGPASSWORD", ""),
        host=os.getenv("PGHOST", "localhost"),
        port=int(os.getenv("PGPORT", "5433")),
        database=os.getenv("PGDATABASE", "workout"),
    )
    return create_engine(url)


def load(engine: Engine, frames: dict[str, pd.DataFrame]) -> dict[str, int]:
    """Replace each raw table with the given frame. Returns row counts."""
    loaded_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    counts: dict[str, int] = {}
    with engine.begin() as conn:
        conn.execute(text(f"create schema if not exists {RAW_SCHEMA}"))
        for table, df in frames.items():
            # Drop with cascade: dbt staging views depend on these tables.
            conn.execute(text(f"drop table if exists {RAW_SCHEMA}.{table} cascade"))
            df.assign(_loaded_at=loaded_at).to_sql(
                table, conn, schema=RAW_SCHEMA, if_exists="replace", index=False
            )
            counts[table] = len(df)
    return counts


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--data-dir", default="data/raw", type=Path)
    args = parser.parse_args(argv)

    frames: dict[str, pd.DataFrame] = {}
    for table in TABLES:
        path = args.data_dir / f"{table}.csv"
        if not path.exists():
            print(f"Missing file: {path}  (export the '{table}' tab as CSV)", file=sys.stderr)
            return 1
        frames[table] = clean_tab(read_tab(path), table)

    counts = load(get_engine(), frames)
    for table, n in counts.items():
        print(f"{RAW_SCHEMA}.{table}: {n} rows")
    return 0


if __name__ == "__main__":
    sys.exit(main())
