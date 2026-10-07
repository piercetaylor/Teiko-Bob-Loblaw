"""Part 2: relative frequency of each cell population within each sample."""
import sqlite3
from collections.abc import Iterable

import pandas as pd

COLUMNS = ["sample", "total_count", "population", "count", "percentage"]

_QUERY = """
SELECT f.sample, f.total_count, f.population, f.count, f.percentage
FROM sample_frequencies f
JOIN populations p ON p.population = f.population
{where}
ORDER BY f.sample, p.sort_order
"""


def frequency_table(
    conn: sqlite3.Connection, samples: Iterable[str] | None = None
) -> pd.DataFrame:
    """One row per sample and population, as a percentage of that sample's total."""
    if samples is None:
        return pd.read_sql_query(_QUERY.format(where=""), conn)

    samples = list(samples)
    if not samples:
        return pd.DataFrame(columns=COLUMNS)
    where = "WHERE f.sample IN ({})".format(",".join("?" * len(samples)))
    return pd.read_sql_query(_QUERY.format(where=where), conn, params=samples)
