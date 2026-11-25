"""Tests for loader/load_raw.py.

The first group needs no database. The last test loads the fixtures into a real
Postgres and is skipped when none is reachable (CI always provides one).
"""
from pathlib import Path

import pandas as pd
import pytest
from sqlalchemy import text

import load_raw
from load_raw import SchemaError, clean_tab, read_tab

FIXTURES = Path(__file__).parent / "fixtures"


def test_scratch_columns_next_to_workout_type_are_dropped():
    df = clean_tab(read_tab(FIXTURES / "workout_type.csv"), "workout_type")
    assert list(df.columns) == ["_source_row", "workout_type_id", "workout_type_name"]
    assert len(df) == 4


def test_fully_empty_rows_are_dropped():
    raw = read_tab(FIXTURES / "workout_exercise.csv")
    df = clean_tab(raw, "workout_exercise")
    assert len(raw) == 20  # 17 real rows + 3 empty formatted rows
    assert len(df) == 17


def test_source_row_points_at_the_sheet_row():
    df = clean_tab(read_tab(FIXTURES / "workout_exercise.csv"), "workout_exercise")
    # Header is sheet row 1, so the first data record is row 2.
    assert df["_source_row"].tolist()[:3] == [2, 3, 4]


def test_values_are_trimmed_but_kept_as_text():
    df = clean_tab(read_tab(FIXTURES / "workout_exercise.csv"), "workout_exercise")
    assert " 15 " not in df["workout_repetition_amount"].tolist()
    assert "15" in df["workout_repetition_amount"].tolist()
    assert df["workout_repetition_amount"].map(type).eq(str).all()


def test_missing_column_raises_schema_error():
    df = pd.DataFrame({"workout_type_id": ["1"]})
    with pytest.raises(SchemaError, match="workout_type_name"):
        clean_tab(df, "workout_type")


def test_column_headers_with_stray_spaces_are_accepted():
    df = pd.DataFrame({" workout_type_id ": ["1"], "workout_type_name": ["core"]})
    assert clean_tab(df, "workout_type")["workout_type_id"].tolist() == ["1"]


def _database_available() -> bool:
    try:
        with load_raw.get_engine().connect() as conn:
            conn.execute(text("select 1"))
        return True
    except Exception:
        return False


@pytest.mark.skipif(not _database_available(), reason="no Postgres reachable")
def test_fixtures_load_into_postgres():
    assert load_raw.main(["--data-dir", str(FIXTURES)]) == 0
    with load_raw.get_engine().connect() as conn:
        n = conn.execute(text("select count(*) from raw.workout_exercise")).scalar_one()
        types = conn.execute(
            text(
                "select data_type from information_schema.columns "
                "where table_schema = 'raw' and table_name = 'workout_exercise' "
                "and column_name = 'workout_rounds'"
            )
        ).scalar_one()
    assert n == 17
    assert types == "text"  # raw layer stays untyped; dbt does the typing
