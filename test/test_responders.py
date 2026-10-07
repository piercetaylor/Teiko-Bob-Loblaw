import pandas as pd
import pytest

from cellcounts import responders


def test_cohort_counts(real_conn):
    cohort = responders.cohort_frequencies(real_conn)
    samples = cohort.drop_duplicates("sample")
    assert len(samples) == 1968
    assert samples["subject_id"].nunique() == 656
    assert samples["response"].value_counts().to_dict() == {"yes": 993, "no": 975}
    assert set(samples["time_from_treatment_start"]) == {0, 7, 14}


def test_cohort_excludes_other_samples(make_conn, row):
    conn = make_conn([
        row(sample="keep"),
        row(sample="wb", subject="s2", sample_type="WB"),
        row(sample="lung", subject="s3", condition="lung"),
        row(sample="drug", subject="s4", treatment="phauximab"),
        row(sample="healthy", subject="s5", treatment="none", response=""),
    ])
    assert set(responders.cohort_frequencies(conn)["sample"]) == {"keep"}


def test_timepoints_filter(real_conn):
    day0 = responders.cohort_frequencies(real_conn, timepoints=[0])
    assert set(day0["time_from_treatment_start"]) == {0}
    assert day0["sample"].nunique() == 656


def test_subject_means_one_row_per_subject_and_population(real_conn):
    means = responders.subject_means(responders.cohort_frequencies(real_conn))
    assert len(means) == 656 * 5
    assert means["subject_id"].nunique() == 656


def test_subject_means_averages_timepoints(make_conn, row):
    zero = {"cd4_t_cell": "0", "nk_cell": "0", "monocyte": "0"}
    conn = make_conn([
        row(sample="d0", b_cell="10", cd8_t_cell="90", **zero),
        row(sample="d7", b_cell="20", cd8_t_cell="80", time_from_treatment_start="7", **zero),
        row(sample="d14", b_cell="30", cd8_t_cell="70", time_from_treatment_start="14", **zero),
    ])
    means = responders.subject_means(responders.cohort_frequencies(conn)).set_index("population")
    assert means.loc["b_cell", "percentage"] == pytest.approx(20.0)
    assert means.loc["cd8_t_cell", "percentage"] == pytest.approx(80.0)


def _two_groups(responder, non_responder):
    rows = [{"response": "yes", "population": "x", "percentage": v} for v in responder]
    rows += [{"response": "no", "population": "x", "percentage": v} for v in non_responder]
    return pd.DataFrame(rows)


def test_rank_biserial_sign_follows_direction():
    higher = responders.compare(_two_groups([5, 6, 7, 8], [1, 2, 3, 4])).iloc[0]
    lower = responders.compare(_two_groups([1, 2, 3, 4], [5, 6, 7, 8])).iloc[0]
    assert higher["rank_biserial"] == 1.0
    assert lower["rank_biserial"] == -1.0
    assert higher["median_difference"] == 4.0
    assert higher["p_value"] == lower["p_value"]


def test_bh_boundary_is_significant():
    df = _two_groups([5, 6, 7, 8], [1, 2, 3, 4])
    p_adjusted = responders.compare(df).iloc[0]["p_adjusted"]
    assert responders.compare(df, alpha=p_adjusted).iloc[0]["significant"]
    assert not responders.compare(df, alpha=p_adjusted / 2).iloc[0]["significant"]


def test_compare_rejects_empty_group():
    with pytest.raises(ValueError):
        responders.compare(_two_groups([1, 2, 3], []))


def test_primary_comparison_matches_known_values(real_conn):
    cohort = responders.cohort_frequencies(real_conn)
    out = responders.compare(responders.subject_means(cohort)).set_index("population")
    assert list(out.index) == ["b_cell", "cd8_t_cell", "cd4_t_cell", "nk_cell", "monocyte"]
    assert (out["n_responder"] == 331).all()
    assert (out["n_non_responder"] == 325).all()
    assert out.loc["cd4_t_cell", "p_value"] == pytest.approx(0.01242, rel=1e-3)
    assert out.loc["cd4_t_cell", "p_adjusted"] == pytest.approx(0.06211, rel=1e-3)
    assert out.loc["cd4_t_cell", "rank_biserial"] == pytest.approx(0.1128, rel=1e-3)
    assert not out["significant"].any()


def test_summarize_runs(real_conn):
    out = responders.summarize(real_conn)
    assert list(out.columns) == ["run", *responders.COMPARISON_COLUMNS]
    assert out["run"].value_counts().to_dict() == {
        "subject means (primary)": 5,
        "pooled samples (sensitivity)": 5,
        "day 0 only (sensitivity)": 5,
    }
    pooled = out[(out["run"] == "pooled samples (sensitivity)") & (out["population"] == "cd4_t_cell")]
    assert pooled["p_value"].item() == pytest.approx(0.01334, rel=1e-3)
    day0 = out[out["run"] == "day 0 only (sensitivity)"]
    assert day0["p_adjusted"].min() == pytest.approx(0.8853, rel=1e-3)
    assert not out["significant"].any()


def test_boxplot_has_two_traces_in_population_order(real_conn):
    cohort = responders.cohort_frequencies(real_conn)
    fig = responders.boxplot(responders.subject_means(cohort), {"b_cell": "B cell"})
    assert [t.name for t in fig.data] == ["Responder", "Non-responder"]
    assert list(fig.layout.xaxis.categoryarray)[:2] == ["B cell", "cd8_t_cell"]
