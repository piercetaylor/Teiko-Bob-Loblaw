"""Part 3: population frequencies of responders against non-responders."""
import sqlite3
from collections.abc import Iterable

import pandas as pd

from cellcounts.db import population_order

_COHORT_QUERY = """
SELECT d.subject_id, d.sample, d.response, d.time_from_treatment_start,
       f.population, f.count, f.percentage
FROM sample_frequencies f
JOIN sample_detail d ON d.sample = f.sample
JOIN populations p ON p.population = f.population
WHERE d.condition = 'melanoma'
  AND d.treatment = 'miraclib'
  AND d.sample_type = 'PBMC'
  AND d.response IN ('yes', 'no')
  {timepoints}
ORDER BY d.subject_id, d.time_from_treatment_start, p.sort_order
"""


def cohort_frequencies(
    conn: sqlite3.Connection, timepoints: Iterable[int] | None = None
) -> pd.DataFrame:
    """Melanoma PBMC samples under miraclib having a recorded response. """
    if timepoints is None:
        sql, params = _COHORT_QUERY.format(timepoints=""), []
    else:
        params = [int(t) for t in timepoints]
        clause = "AND d.time_from_treatment_start IN ({})".format(",".join("?" * len(params)))
        sql = _COHORT_QUERY.format(timepoints=clause)

    df = pd.read_sql_query(sql, conn, params=params)
    df["population"] = pd.Categorical(
        df["population"], categories=population_order(conn), ordered=True
    )
    return df


def subject_means(df: pd.DataFrame) -> pd.DataFrame:
    """Average each subject's percentages across their own samples.

    Every subject contributes three samples, one for each of the time points at days 0, 7 and 14.
    """
    return df.groupby(
        ["subject_id", "response", "population"], as_index=False, observed=True
    )[["percentage"]].mean()
