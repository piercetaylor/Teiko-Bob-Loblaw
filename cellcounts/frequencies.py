"""Part 2: relative frequency of each cell population within each sample."""
import sqlite3

import pandas as pd

COLUMNS = ["sample", "total_count", "population", "count", "percentage"]

_QUERY = """
SELECT f.sample, f.total_count, f.population, f.count, f.percentage
FROM sample_frequencies f
JOIN populations p ON p.population = f.population
ORDER BY f.sample, p.sort_order
"""


def frequency_table(conn: sqlite3.Connection) -> pd.DataFrame:
    """One row per sample and population, as a percentage of that sample's total."""
    return pd.read_sql_query(_QUERY, conn)


_DETAIL_QUERY = """
SELECT f.sample, f.total_count, f.population, f.count, f.percentage,
       d.condition, d.treatment, d.sample_type, d.time_from_treatment_start, d.response
FROM sample_frequencies f
JOIN sample_detail d ON d.sample = f.sample
JOIN populations p ON p.population = f.population
ORDER BY f.sample, p.sort_order
"""


def frequency_detail(conn: sqlite3.Connection) -> pd.DataFrame:
    """The frequency table with the sample metadata needed to filter it."""
    return pd.read_sql_query(_DETAIL_QUERY, conn)
