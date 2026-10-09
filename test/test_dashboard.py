import tomllib

import pytest
from streamlit.testing.v1 import AppTest

from cellcounts.db import DB_FILE, ROOT

pytestmark = pytest.mark.skipif(not DB_FILE.exists(), reason="run `make pipeline` first")


@pytest.fixture(scope="module")
def app():
    at = AppTest.from_file(str(ROOT / "dashboard.py"), default_timeout=120).run()
    assert not at.exception, [str(e.value) for e in at.exception]
    return at


def test_tabs_and_headline(app):
    assert [t.label for t in app.tabs] == [
        "Overview (Part 1)", "Sample frequencies (Part 2)", "Responders vs non-responders (Part 3)",
        "Baseline cohort (Part 4)",
    ]
    assert [h.value for h in app.subheader] == [
        "How is the trial data stored?",
        "Trial data: SQLite database built from cell-count.csv",
        "What is the frequency of each cell type within each sample?",
        "Which cell populations differ between miraclib responders and non-responders?",
        "Which subjects are in the baseline melanoma PBMC cohort treated with miraclib?",
    ]
    values = {m.label: m.value for m in app.metric}
    assert values["Populations significant (adjusted p ≤ 0.05)"] == "0 of 5"
    assert values["Smallest BH-adjusted p-value (CD4 T cell)"] == "0.062"
    assert values["Subjects compared (melanoma, miraclib, PBMC)"] == "656"
    assert values["Subjects"] == "3,500"
    assert values["Samples"] == "10,500"
    assert values["Mean B cell count at day 0, male melanoma responders"] == "10,206.15"
    assert any("No population differs" in m.value for m in app.markdown)


def test_charts_use_the_theme_palette(app):
    specs = [el.proto.spec for el in app.get("plotly_chart")]
    assert len(specs) == 5
    assert all("#000001" in spec for spec in specs)
    assert not any("#66C2A5" in spec or "#636efa" in spec.lower() for spec in specs)
    assert sum("#666666" in spec for spec in specs) == 1


def test_unit_of_analysis_switches_without_error(app):
    control = next(c for c in app.segmented_control if c.label == "Unit of analysis")
    for option in control.options:
        control.set_value(option).run()
        assert not app.exception, [str(e.value) for e in app.exception]


def test_filters_narrow_the_frequency_table(app):
    condition = next(p for p in app.pills if p.label == "Condition")
    condition.set_value(["melanoma"]).run()
    assert not app.exception
    assert any(c.value.startswith("5,175 samples selected") for c in app.caption)
    assert any("relative frequencies for 5,175 samples" in m.value for m in app.markdown)


def test_clearing_a_filter_shows_a_message_not_a_blank_chart(app):
    condition = next(p for p in app.pills if p.label == "Condition")
    condition.set_value([]).run()
    assert not app.exception
    assert any("No samples match" in i.value for i in app.info)


def test_theme_palette_fills_all_ten_slots():
    # Streamlit swaps ten placeholder colours; a shorter list leaves Plotly's box traces on its default blue.
    theme = tomllib.loads((ROOT / ".streamlit" / "config.toml").read_text())["theme"]
    assert len(theme["chartCategoricalColors"]) == 10


def test_day_grouping_uses_a_categorical_axis():
    at = AppTest.from_file(str(ROOT / "dashboard.py"), default_timeout=120).run()
    next(c for c in at.segmented_control if c.label == "Group by").set_value("time_from_treatment_start").run()
    assert not at.exception, [str(e.value) for e in at.exception]
    assert any('"type":"category"' in el.proto.spec.replace(" ", "") for el in at.get("plotly_chart"))
