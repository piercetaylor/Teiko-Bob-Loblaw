"""
Build cell_counts.db from cell_counts.csv
run with `python load_data.py`, db rebuilt each run to assure pipeline reflects the csv input.
"""
import sqlite3
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CSV_FILE = ROOT / "cell_counts.csv"
SCHEMA_FILE = ROOT / "cell_counts_schema.sql"
DB_FILE = ROOT / "cell_counts.db"

POPULATIONS = ['b_cells', 'cd8_t_cells', 'cd4_t_cells', 'monocytes', 'nk_cells']
SUBJECT_COLUMNS = ["project", "condition", "age", "sex", "treatment", "response"]
MIN_SQLITE_VERSION = (3, 37, 0)  # Minimum SQLite version required for CHECK constraints

def read_csv(file_path: Path) -> list[dict]:
    with open(file_path, mode='r', newline='', encoding='utf-8') as csvfile:
        rows = list(csv.DictReader(csvfile))
    missing = set(SUBJECT_COLUMNS + POPULATIONS + ["subject", "sample"]) - set(rows[0])
    if missing: 
            raise ValueError(f"{path.name} is missing columns: {sorted(missing)}")
    return rows

def subjects_from_rows(rows: list[dict]) -> dict[str, dict]:
    """Collapse sample rows to one record per subject.

    Fails if a subject-level column disagrees between a subject's samples, e.g. if subject 123 has two samples with different ages.
    """
    subjects = {}
    for row in rows:
        record = {col: row[col] for col in SUBJECT_COLUMNS}
        seen = subjects.setdefault(row["subject"], record)
        if seen != record:
            raise ValueError(
                f"subject {row['subject']} has inconsistent metadata: {seen} vs {record}"
            )
    return subjects

