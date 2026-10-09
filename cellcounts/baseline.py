"""Part 4: melanoma PBMC samples at baseline from subjects treated with miraclib.

Also the bonus mean baseline B cell count for male melanoma responders.
"""
import sqlite3

import pandas as pd

_BASELINE = """
FROM sample_detail
WHERE condition = 'melanoma'
  AND treatment = 'miraclib'
  AND sample_type = 'PBMC'
  AND time_from_treatment_start = 0
"""


def baseline_samples(conn: sqlite3.Connection) -> pd.DataFrame:
    """Every baseline sample with its project, response and sex."""
    sql = "SELECT sample, subject, project, response, sex " + _BASELINE + "ORDER BY sample"
    return pd.read_sql_query(sql, conn)


def samples_per_project(conn: sqlite3.Connection) -> pd.DataFrame:
    """Number of baseline samples from each project."""
    sql = "SELECT project, COUNT(*) AS samples " + _BASELINE + "GROUP BY project ORDER BY project"
    return pd.read_sql_query(sql, conn)


def subjects_per_response(conn: sqlite3.Connection) -> pd.DataFrame:
    """Number of baseline subjects who responded and who did not."""
    sql = (
        "SELECT response, COUNT(DISTINCT subject_id) AS subjects "
        + _BASELINE
        + "GROUP BY response ORDER BY response DESC"
    )
    return pd.read_sql_query(sql, conn)


def subjects_per_sex(conn: sqlite3.Connection) -> pd.DataFrame:
    """Number of male and female baseline subjects."""
    sql = (
        "SELECT sex, COUNT(DISTINCT subject_id) AS subjects "
        + _BASELINE
        + "GROUP BY sex ORDER BY sex"
    )
    return pd.read_sql_query(sql, conn)


def male_responder_b_cell_mean(conn: sqlite3.Connection) -> float | None:
    """Mean baseline B cell count for male melanoma responders, any sample type or treatment."""
    sql = """
    SELECT ROUND(AVG(c.count), 2)
    FROM cell_counts c
    JOIN sample_detail d ON d.sample = c.sample
    WHERE c.population = 'b_cell'
      AND d.condition = 'melanoma'
      AND d.sex = 'M'
      AND d.response = 'yes'
      AND d.time_from_treatment_start = 0
    """
    return conn.execute(sql).fetchone()[0]
