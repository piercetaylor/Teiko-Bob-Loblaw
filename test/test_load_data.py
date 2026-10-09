import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from load_data import CSV_FILE, POPULATIONS, build_database, collapse_subjects

BASE_ROW = {
    "project": "prj1", "subject": "s1", "condition": "melanoma", "age": "50",
    "sex": "M", "treatment": "miraclib", "response": "yes",
    "sample": "smp1", "sample_type": "PBMC", "time_from_treatment_start": "0",
    "b_cell": "100", "cd8_t_cell": "200", "cd4_t_cell": "300",
    "nk_cell": "400", "monocyte": "500",
}


def row(**overrides):
    return {**BASE_ROW, **overrides}


def test_collapse_subjects_dedupes_repeated_subject():
    rows = [row(sample="smp1"), row(sample="smp2", time_from_treatment_start="7")]
    subjects = collapse_subjects(rows)
    assert list(subjects.keys()) == [("prj1", "s1")]


def test_collapse_subjects_keeps_distinct_subjects_separate():
    rows = [row(sample="smp1"), row(sample="smp2", subject="s2")]
    subjects = collapse_subjects(rows)
    assert set(subjects.keys()) == {("prj1", "s1"), ("prj1", "s2")}


def test_build_database_round_trips_synthetic_rows(tmp_path):
    rows = [
        row(sample="smp1", subject="s1"),
        row(sample="smp2", subject="s1", time_from_treatment_start="7"),
        row(sample="smp3", subject="s2", response="no", b_cell="10"),
    ]
    db_path = tmp_path / "test.db"
    build_database(rows, db_path)

    conn = sqlite3.connect(db_path)
    assert conn.execute("SELECT COUNT(*) FROM subjects").fetchone()[0] == 2
    assert conn.execute("SELECT COUNT(*) FROM samples").fetchone()[0] == 3
    assert conn.execute("SELECT COUNT(*) FROM cell_counts").fetchone()[0] == 3 * len(POPULATIONS)
    assert conn.execute(
        "SELECT count FROM cell_counts WHERE sample = 'smp3' AND population = 'b_cell'"
    ).fetchone()[0] == 10
    conn.close()


def test_build_database_healthy_subject_response_is_null(tmp_path):
    rows = [row(sample="smp1", treatment="none", response="")]
    db_path = tmp_path / "test.db"
    build_database(rows, db_path)

    conn = sqlite3.connect(db_path)
    assert conn.execute("SELECT response FROM subjects").fetchone()[0] is None
    conn.close()


def test_build_database_matches_real_csv(tmp_path):
    from validate_csv import validate

    rows = validate(CSV_FILE)
    db_path = tmp_path / "cell_counts.db"
    build_database(rows, db_path)

    conn = sqlite3.connect(db_path)
    assert conn.execute("SELECT COUNT(*) FROM subjects").fetchone()[0] == 3500
    assert conn.execute("SELECT COUNT(*) FROM samples").fetchone()[0] == 10500
    assert conn.execute("SELECT COUNT(*) FROM cell_counts").fetchone()[0] == 52500

    quiz = conn.execute(
        """
        SELECT ROUND(AVG(cc.count), 2)
        FROM cell_counts cc
        JOIN sample_detail sd ON sd.sample = cc.sample
        WHERE cc.population = 'b_cell'
          AND sd.condition = 'melanoma'
          AND sd.sex = 'M'
          AND sd.response = 'yes'
          AND sd.time_from_treatment_start = 0
        """
    ).fetchone()[0]
    assert quiz == 10206.15
    conn.close()


def test_script_runs_without_arguments_and_builds_db_in_its_root(tmp_path):
    import shutil
    import subprocess
    root = Path(__file__).resolve().parent.parent
    for name in ("load_data.py", "validate_csv.py", "schema.sql", "cell-count.csv"):
        shutil.copy(root / name, tmp_path / name)
    for _ in range(2):  # second run replaces the first database cleanly
        result = subprocess.run([sys.executable, "load_data.py"], cwd=tmp_path, capture_output=True, text=True)
        assert result.returncode == 0, result.stderr
        assert "OK: loaded 10500 rows" in result.stdout
    assert (tmp_path / "cell-count.db").exists()
    assert not (tmp_path / "cell-count.tmp").exists()
    with sqlite3.connect(tmp_path / "cell-count.db") as conn:
        assert conn.execute("SELECT COUNT(*) FROM samples").fetchone()[0] == 10500
