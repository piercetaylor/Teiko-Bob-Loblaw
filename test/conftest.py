import sqlite3
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from load_data import CSV_FILE, build_database
from validate_csv import validate

BASE_ROW = {
    "project": "prj1", "subject": "s1", "condition": "melanoma", "age": "50",
    "sex": "M", "treatment": "miraclib", "response": "yes",
    "sample": "smp1", "sample_type": "PBMC", "time_from_treatment_start": "0",
    "b_cell": "100", "cd8_t_cell": "200", "cd4_t_cell": "300",
    "nk_cell": "400", "monocyte": "500",
}


@pytest.fixture
def row():
    """One CSV row as a dict, with any field overridden by keyword."""
    return lambda **overrides: {**BASE_ROW, **overrides}


@pytest.fixture(scope="session")
def real_conn(tmp_path_factory):
    """Database built from cell-count.csv, which is shared by the all test sessions."""
    db_path = tmp_path_factory.mktemp("db") / "cell-count.db"
    build_database(validate(CSV_FILE), db_path)
    conn = sqlite3.connect(db_path)
    yield conn
    conn.close()


@pytest.fixture
def make_conn(tmp_path):
    """Builds a database from synthetic rows and returns an open connection."""
    conns = []

    def _make(rows):
        db_path = tmp_path / f"synthetic{len(conns)}.db"
        build_database(rows, db_path)
        conn = sqlite3.connect(db_path)
        conns.append(conn)
        return conn

    yield _make
    for conn in conns:
        conn.close()
