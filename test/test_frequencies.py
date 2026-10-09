import load_data
from cellcounts import db, frequencies
from validate_csv import POPULATIONS


def test_db_file_matches_load_data():
    assert db.DB_FILE == load_data.DB_FILE


def test_populations_table_matches_validate_csv(real_conn):
    assert db.population_order(real_conn) == POPULATIONS


def test_full_table_shape_and_columns(real_conn):
    table = frequencies.frequency_table(real_conn)
    assert list(table.columns) == ["sample", "total_count", "population", "count", "percentage"]
    assert len(table) == 10500 * 5


def test_percentages_sum_to_100_per_sample(real_conn):
    table = frequencies.frequency_table(real_conn)
    sums = table.groupby("sample")["percentage"].sum()
    assert (sums - 100).abs().max() < 1e-9


def test_total_count_is_sum_of_counts(real_conn):
    table = frequencies.frequency_table(real_conn)
    totals = table.groupby("sample").agg(total=("total_count", "first"), summed=("count", "sum"))
    assert (totals["total"] == totals["summed"]).all()


def test_rows_follow_sort_order_not_alphabetical(real_conn):
    first = frequencies.frequency_table(real_conn)
    first = first[first["sample"] == "sample00000"]
    assert list(first["population"]) == POPULATIONS


def test_percentage_of_known_counts(make_conn, row):
    conn = make_conn([row(b_cell="25", cd8_t_cell="50", cd4_t_cell="75", nk_cell="50", monocyte="0")])
    table = frequencies.frequency_table(conn).set_index("population")
    assert table.loc["b_cell", "percentage"] == 12.5
    assert table.loc["cd8_t_cell", "percentage"] == 25.0
    assert table.loc["cd4_t_cell", "percentage"] == 37.5
    assert table.loc["monocyte", "percentage"] == 0.0
    assert (table["total_count"] == 200).all()


def test_frequency_detail_adds_sample_metadata(real_conn):
    detail = frequencies.frequency_detail(real_conn)
    assert len(detail) == 10500 * 5
    assert list(detail.columns[:5]) == frequencies.COLUMNS
    assert set(detail["sample_type"]) == {"PBMC", "WB"}
    assert detail["response"].isna().sum() > 0
