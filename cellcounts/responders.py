"""Part 3: population frequencies of responders against non-responders."""
import sqlite3
from collections.abc import Iterable

import pandas as pd
import plotly.graph_objects as go
from scipy.stats import false_discovery_control, mannwhitneyu

from cellcounts.db import population_order

ALPHA = 0.05

RESPONSE_NAMES = {"yes": "Responder", "no": "Non-responder"}

COMPARISON_COLUMNS = [
    "population",
    "n_responder",
    "n_non_responder",
    "median_responder",
    "median_non_responder",
    "median_difference",
    "rank_biserial",
    "p_value",
    "p_adjusted",
    "significant",
]

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


def _populations(df: pd.DataFrame) -> list[str]:
    """Populations in display order, from the categorical set (if exists)."""
    if isinstance(df["population"].dtype, pd.CategoricalDtype):
        return list(df["population"].cat.categories)
    return list(dict.fromkeys(df["population"]))


def compare(df: pd.DataFrame, alpha: float = ALPHA) -> pd.DataFrame:
    """Two-sided Mann-Whitney U per population, Benjamini-Hochberg corrected."""
    rows = []
    for population in _populations(df):
        at = df.loc[df["population"] == population]
        responder = at.loc[at["response"] == "yes", "percentage"]
        non_responder = at.loc[at["response"] == "no", "percentage"]
        if responder.empty or non_responder.empty:
            raise ValueError(f"{population}: one response group has no observations")

        u, p_value = mannwhitneyu(responder, non_responder, alternative="two-sided")
        rows.append(
            {
                "population": population,
                "n_responder": len(responder),
                "n_non_responder": len(non_responder),
                "median_responder": responder.median(),
                "median_non_responder": non_responder.median(),
                "median_difference": responder.median() - non_responder.median(),
                "rank_biserial": 2 * u / (len(responder) * len(non_responder)) - 1,
                "p_value": p_value,
            }
        )
    """BH correction is applied."""
    out = pd.DataFrame(rows)
    out["p_adjusted"] = false_discovery_control(out["p_value"], method="bh")
    out["significant"] = out["p_adjusted"] < alpha
    return out[COMPARISON_COLUMNS]


def summarize(conn: sqlite3.Connection, alpha: float = ALPHA) -> pd.DataFrame:
    """The primary comparison, pooled samples, and day 0 only."""
    cohort = cohort_frequencies(conn)
    runs = {
        "subject means (primary)": subject_means(cohort),
        "pooled samples (sensitivity)": cohort,
        "day 0 only (sensitivity)": cohort.loc[cohort["time_from_treatment_start"] == 0],
    }
    stacked = [compare(frame, alpha).assign(run=name) for name, frame in runs.items()]
    return pd.concat(stacked, ignore_index=True)[["run", *COMPARISON_COLUMNS]]


def boxplot(
    df: pd.DataFrame, labels: dict[str, str] | None = None, title: str | None = None
) -> go.Figure:
    """Relative frequency by population, responders vs non-responders."""
    labels = labels or {}
    fig = go.Figure()
    for response, name in RESPONSE_NAMES.items():
        group = df.loc[df["response"] == response]
        fig.add_trace(
            go.Box(
                x=[labels.get(p, p) for p in group["population"]],
                y=group["percentage"],
                name=name,
            )
        )
    fig.update_layout(
        boxmode="group",
        template="plotly_white",
        title=title,
        yaxis_title="Relative frequency (%)",
    )
    fig.update_xaxes(
        categoryorder="array",
        categoryarray=[labels.get(p, p) for p in _populations(df)],
    )
    return fig
