"""Streamlit dashboard for Parts 1 to 4, reading cell-count.db built by the pipeline."""
from contextlib import closing
from datetime import datetime

import pandas as pd
import plotly.express as px
import streamlit as st

from cellcounts import baseline, frequencies, responders
from cellcounts.db import DB_FILE, connect_readonly, population_labels

PRIMARY = "subject means (primary)"
RUNS = {
    "Subject means (primary)": PRIMARY,
    "Pooled samples (every sample, days 0, 7 and 14)": "pooled samples (sensitivity)",
    "Day 0 only (pre-treatment samples)": "day 0 only (sensitivity)",
}
FILTERS = {
    "condition": "Condition",
    "treatment": "Treatment",
    "sample_type": "Sample type",
    "time_from_treatment_start": "Day",
    "response": "Response",
}
TABLES = {
    "subjects": "subject",
    "samples": "sample",
    "populations": "immune cell population",
    "cell_counts": "sample and population",
}
QUESTIONS = {
    "Overview (Part 1)": "Loblaw Bio: How does miraclib affect immune cell populations?",
    "Sample frequencies (Part 2)": "What is the frequency of each cell type within each sample?",
    "Responders vs non-responders (Part 3)": "Which cell populations differ between miraclib responders and non-responders?",
    "Baseline cohort (Part 4)": "Which subjects are in the baseline melanoma PBMC cohort treated with miraclib?",
}
RUN_COLUMNS = ["run", "n_responder", "n_non_responder", "p_value", "p_adjusted", "significant"]
DAY_COLUMNS = ["day", "population", "median_difference", "rank_biserial", "p_value", "p_adjusted", "significant"]
FORMATS = {
    **{c: st.column_config.NumberColumn(format="%.3f") for c in ("p_value", "p_adjusted", "welch_p", "welch_p_adjusted")},
    **{c: st.column_config.NumberColumn(format="%.2f") for c in ("percentage", "median_responder", "median_non_responder", "median_difference", "rank_biserial")},
}
# Reference grey, repeated from chartCategoricalColors in .streamlit/config.toml: a trace cannot reference a theme slot.
NON_RESPONDER_COLOR = "#666666"


@st.cache_data
def load() -> dict:
    """Read every table the dashboard shows."""
    with closing(connect_readonly()) as conn:
        cohort = responders.cohort_frequencies(conn)
        detail = frequencies.frequency_detail(conn)
        detail["response"] = detail["response"].fillna("not recorded")
        return {
            "labels": population_labels(conn),
            "detail": detail,
            "schema": pd.DataFrame({
                "table": list(TABLES),
                "one row per": list(TABLES.values()),
                "rows": [conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in TABLES],
            }),
            "projects": conn.execute("SELECT COUNT(DISTINCT project) FROM subjects").fetchone()[0],
            "comparison": responders.summarize(conn),
            "by_day": responders.by_timepoint(cohort),
            "frames": {
                PRIMARY: responders.subject_means(cohort),
                "pooled samples (sensitivity)": cohort,
                "day 0 only (sensitivity)": cohort.loc[cohort["time_from_treatment_start"] == 0],
            },
            "baseline_samples": baseline.baseline_samples(conn),
            "baseline_counts": [
                baseline.samples_per_project(conn),
                baseline.subjects_per_response(conn),
                baseline.subjects_per_sex(conn),
            ],
            "b_cell_mean": baseline.male_responder_b_cell_mean(conn),
        }


def headline(comparison: pd.DataFrame) -> str:
    """The population with the smallest adjusted p value in the primary run."""
    primary = comparison.loc[comparison["run"] == PRIMARY]
    return primary.loc[primary["p_adjusted"].idxmin(), "population"]


def card(title: str):
    """A bordered container with a one-line bold label."""
    box = st.container(border=True)
    box.markdown(f"**{title}**")
    return box


def download(frame: pd.DataFrame, filename: str) -> None:
    """DataFrame as a CSV download."""
    st.download_button(f"Download {filename}", frame.to_csv(index=False), filename, "text/csv")


def overview(data: dict) -> None:
    """Right panel: the answer to Bob's questions."""
    comparison = data["comparison"]
    primary = comparison.loc[comparison["run"] == PRIMARY].set_index("population")
    closest = headline(comparison)
    top, label = primary.loc[closest], data["labels"][closest]
    with card("Do miraclib responders and non-responders differ in any immune cell population?"):
        st.markdown(
            "No population differs significantly by Mann-Whitney U test after Benjamini-Hochberg correction. "
            f":primary[{label}s are closest: p = {top['p_value']:.3f} before BH correction, adjusted p = {top['p_adjusted']:.3f} after.]"
        )
        st.metric(f"Populations significant (adjusted p ≤ {responders.ALPHA})", f"{int(primary['significant'].sum())} of {len(primary)}", border=True)
        st.metric(f"Smallest BH-adjusted p-value ({label})", f"{top['p_adjusted']:.3f}", border=True)
        st.metric("Subjects compared (melanoma, miraclib, PBMC)", f"{data['frames'][PRIMARY]['subject_id'].nunique():,}", border=True)


def part1(data: dict) -> None:
    """The SQL database used to answer each question."""
    rows = data["schema"].set_index("table")["rows"]
    st.markdown(
        "Bob Loblaw of Loblaw Bio is running a clinical trial of the drug candidate miraclib and wants to understand its "
        "effect on immune cell populations. The trial data cover melanoma and carcinoma patients treated with miraclib or "
        f"its competitor, phauximab, alongside untreated healthy donors. For each patient, {len(data['labels'])} cell populations were counted at 3 timepoints: "
        "days 0, 7 and 14. Treated patients were recorded as responders or non-responders. Each tab answers Bob's questions in order:\n"
        "- **Part 2** shows each population's relative frequency in each sample.\n"
        "- **Part 3** tests if these relative frequencies differ between miraclib responders and non-responders in melanoma patients.\n"
        "- **Part 4** describes the baseline samples of that melanoma PBMC cohort."
    )
    st.subheader("Trial data: SQLite database built from cell-count.csv")
    counts = {"Subjects": rows["subjects"], "Samples": rows["samples"], "Projects": data["projects"], "Populations": rows["populations"]}
    with st.container(horizontal=True):
        for label, n in counts.items():
            st.metric(label, f"{n:,}", border=True)
    with card("SQLite schema"):
        st.dataframe(data["schema"], hide_index=True, alt="Tables in cell-count.db with their row counts")
        st.caption(
            "cell-count.csv (input file) is split into one row per subject, per sample, and per cell count. "
            "The `sample_frequencies` view computes each cell population's share of its sample's total. "
            "Because samples and populations are stored as rows, and percentages are computed from "
            "those rows, new projects and samples load without change to the schema or the analysis. A new cell population "
            "needs new row added to the `populations` table and an entry in the validator's population list."
        )


def part2(data: dict) -> None:
    """Summary table of each population's relative frequency in each sample."""
    detail, labels = data["detail"], data["labels"]
    st.markdown(
        "For each sample, the population counts are summed, and each population's relative frequency is "
        "its count as a percentage of that sample's total. The table gives one row per sample and population; the chart below it "
        "averages those percentages over the selected samples."
    )
    shown = detail
    with card("Filter the table and chart"), st.container(horizontal=True):
        for field, label in FILTERS.items():
            options = sorted(detail[field].unique())
            chosen = st.pills(label, options, selection_mode="multi", default=options, wrap=True)
            shown = shown.loc[shown[field].isin(chosen)]
    if shown.empty:
        st.info("No samples match the current filters.")
        return
    with card(f"Cell counts and relative frequencies for {shown['sample'].nunique():,} samples"):
        summary = shown[frequencies.COLUMNS]
        st.dataframe(summary, hide_index=True, column_config=FORMATS, alt="Relative frequency of each population per sample")
        download(summary, "frequencies_filtered.csv")
    with card("Mean population composition of the selected samples"):
        group = st.segmented_control(
            "Group by", list(FILTERS), format_func=FILTERS.__getitem__, default="condition", required=True,
            help="Which field forms the x-axis",
        )
        composition = (
            shown.groupby([group, "population"])["percentage"].mean().reset_index()
            .assign(population=lambda d: d["population"].map(labels), **{group: lambda d: d[group].astype(str)})
        )
        fig = px.bar(
            composition, x=group, y="percentage", color="population", barmode="stack", text_auto=".1f",
            category_orders={"population": list(labels.values())},
            labels={"percentage": "Mean relative frequency (%)", group: FILTERS[group], "population": "Population"},
        )
        fig.update_xaxes(type="category")
        st.plotly_chart(fig, alt=f"Stacked bars of mean population composition by {FILTERS[group].lower()}")
        st.caption(f"{shown['sample'].nunique():,} samples selected. Change the selection in the filter card above.")


def part3(data: dict) -> None:
    """Responders vs non-responders, melanoma, miraclib, PBMC."""
    comparison = data["comparison"]
    top_pop = headline(comparison)
    label, n_pops = data["labels"][top_pop], len(data["labels"])
    top = comparison.loc[(comparison["run"] == PRIMARY) & (comparison["population"] == top_pop)].iloc[0]
    direction = "higher" if top["median_difference"] > 0 else "lower"
    st.markdown(
        f"No population remains significant after Benjamini-Hochberg adjustment for {n_pops} tests. **{label}s differ before adjustment** "
        f"(p = {top['p_value']:.3f}, adjusted p = {top['p_adjusted']:.3f}), with a {direction} median relative frequency in responders. "
        "Each population is compared with a two-sided Mann-Whitney U test, chosen before the data were inspected "
        f"(see Methods), and the {n_pops} p-values were then Benjamini-Hochberg adjusted.\n\nA Welch t-test on the same subject means "
        f"would call {label}s significant (adjusted p = {top['welch_p_adjusted']:.3f}), so that result depends on the choice of test. "
        f"The {label} difference is a hypothesis for new data, not a finding. The primary subject-mean comparison mixes "
        "pre-treatment and on-treatment samples, so it tests association; the day 0 only run is the predictive one, and its "
        "rows equal the day 0 rows of the per-day table below. The boxplots compare each "
        "population's relative frequency in responders and non-responders, and the table under them reports the "
        "medians, the rank-biserial effect size, and the p-values from both tests."
    )
    choice = st.segmented_control(
        "Unit of analysis", list(RUNS), default="Subject means (primary)", required=True,
        help="Pooled samples treat days 0, 7 and 14 as independent; shown as a sensitivity check",
    )
    with st.expander("Methods"):
        st.markdown(
            "The Mann-Whitney U test ranks all subjects together and asks whether responders tend to "
            "rank higher or lower than non-responders. It was fixed as the decision rule in advance because "
            "it needs no normality assumption. The subject means turn out to be close to "
            "normal, so Welch's t-test is also valid and is reported beside it; where the two disagree, as "
            f"they do for {label}s, the conclusion is that the evidence is borderline rather than that one "
            "test wins. All populations were tested together, so the Benjamini-Hochberg procedure adjusts their "
            "p-values jointly to keep the expected share of false discoveries at most 5%. The rank-biserial "
            f"correlation is the effect size: {top['rank_biserial']:.2f} for {label}s means a random responder "
            f"has a higher {label} relative frequency than a random non-responder about {50 * (1 + top['rank_biserial']):.0f}% "
            "of the time, against 50% for no effect. The relative frequencies share a denominator, and project, "
            "age and sex are not adjusted for. The CSV below holds all three runs."
        )
        download(comparison, "responders_comparison.csv")
    run = RUNS[choice]
    table = comparison.loc[comparison["run"] == run].set_index("population")
    labels = {p: f"{l}<br>adj. p = {table.loc[p, 'p_adjusted']:.3f}" for p, l in data["labels"].items()}
    fig = responders.boxplot(data["frames"][run], labels).update_layout(template="streamlit")
    fig.data[1].marker.color = NON_RESPONDER_COLOR
    unit = "samples" if run.startswith("pooled") else "subjects"
    with card("Relative frequency by population, responders and non-responders"):
        st.plotly_chart(fig, alt="Boxplots of relative frequency per population, responders beside non-responders")
        st.caption(
            f"Unit of analysis: {choice}. Each population compares {int(table['n_responder'].iloc[0])} responder and "
            f"{int(table['n_non_responder'].iloc[0])} non-responder {unit} by two-sided Mann-Whitney U, with p-values "
            "Benjamini-Hochberg adjusted across the populations."
        )
    shown = table.reset_index().drop(columns="run").assign(population=lambda d: d["population"].map(data["labels"]))
    with card("Responders vs non-responders, one test per population"):
        st.dataframe(shown, hide_index=True, column_config=FORMATS, alt="Mann-Whitney results per population")
    with card(f"{label}s: n and p-values under three units of analysis"):
        runs = comparison.loc[comparison["population"] == top_pop, RUN_COLUMNS]
        st.dataframe(runs, hide_index=True, column_config=FORMATS, alt=f"{label} result under each unit of analysis")
        st.caption(
            "Each subject has a sample at days 0, 7 and 14. Counting those as three independent "
            "observations triples the apparent sample size. The primary analysis averages them into one "
            "value per subject. Pooling is invalid in principle but happens not to change the result here."
        )
    by_day = data["by_day"]
    lowest = by_day.loc[by_day["p_value"].idxmin()]
    with card("Each day independently: does the difference in relative frequency exist before treatment or appear during it?"):
        st.markdown(
            f"One row per population per day, comparing the same {lowest['n_responder']} responders and "
            f"{lowest['n_non_responder']} non-responders using only that day's sample from each subject. "
            "`median_difference` is the responder median minus the "
            "non-responder median, in percentage points, so a positive value means responders have more of that "
            "population. `rank_biserial` runs from -1 to 1 and gives the direction and size of the effect; 0 is no "
            "difference. Benjamini-Hochberg is applied within each day across its populations."
        )
        shown = by_day[DAY_COLUMNS].assign(population=lambda d: d["population"].map(data["labels"]))
        st.dataframe(shown, hide_index=True, column_config=FORMATS, alt="Mann-Whitney results per population within each day")
        st.caption(
            f"The smallest raw p-value "
            f"is {data['labels'][lowest['population']]} on day {lowest['day']} (p = {lowest['p_value']:.3f}, adjusted "
            f"p = {lowest['p_adjusted']:.3f}). Nothing is significant after correction on any day, and nothing comes "
            "close at day 0, so the baseline data carry no detectable signal for predicting response. The larger day 7 and 14 "
            "differences are consistent with an on-treatment change, but that was not tested directly and this table is exploratory."
        )


def part4(data: dict) -> None:
    """Melanoma PBMC samples at baseline from subjects treated with miraclib."""
    st.markdown(
        f"The {len(data['baseline_samples'])} melanoma PBMC samples taken at day 0 from subjects treated with miraclib, one per subject. "
        "Samples are counted per project, subjects per response and per sex; the full table follows."
    )
    titles = ["Samples per project", "Subjects per response", "Subjects per sex"]
    for col, frame, title in zip(st.columns(3), data["baseline_counts"], titles):
        axes = {c: c.replace("_", " ").capitalize() for c in frame.columns}
        fig = px.bar(frame, x=frame.columns[0], y=frame.columns[1], text_auto=True, labels=axes).update_layout(height=260)
        with col, card(title):
            st.plotly_chart(fig, alt=title)
    with card("Among male melanoma patients of every sample and treatment type, what is the mean B cell count of responders at day 0?"):
        st.metric("Mean B cell count at day 0, male melanoma responders", f"{data['b_cell_mean']:,.2f}", border=True)
    with card(f"The {len(data['baseline_samples'])} baseline melanoma PBMC samples from miraclib-treated patients"):
        st.dataframe(data["baseline_samples"], hide_index=True, alt="Baseline samples with subject, project, response and sex")
        download(data["baseline_samples"], "baseline_samples.csv")


def main() -> None:
    """Lay out the four parts of the project as tabs, with a panel about the results beside them."""
    st.set_page_config(page_title="Loblaw Bio immune cell counts", page_icon=":material/biotech:", layout="wide")
    if not DB_FILE.exists():
        import load_data
        load_data.main()
    try:
        data = load()
    except FileNotFoundError:
        st.error("cell-count.db not found. Run `make pipeline` to build it.")
        return
    st.html("<style>[data-testid='stMetricLabel'] p{white-space:normal;overflow:visible}</style>")
    parts, side = st.columns([7, 2], gap="large")
    with side:
        st.title("Loblaw Bio")
        st.markdown("#### :primary[Immune cell populations under miraclib, under phauximab, and in untreated donors]")
        overview(data)
        st.caption(f"Database built {datetime.fromtimestamp(DB_FILE.stat().st_mtime):%Y-%m-%d %H:%M}, opened read-only.")
    renderers = [part1, part2, part3, part4]
    for tab, question, render in zip(parts.tabs(list(QUESTIONS)), QUESTIONS.values(), renderers):
        with tab:
            st.subheader(question)
            render(data)


main()
