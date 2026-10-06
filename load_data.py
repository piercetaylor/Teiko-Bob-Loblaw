"""
Build cell-count.db from cell-counts.csv, validating the CSV first using validate_csv.py.
Run with `python load_data.py`, db rebuilt each run to assure pipeline reflects the csv input.
"""
import os
import sqlite3
import sys
from pathlib import Path

from validate_csv import POPULATIONS, SUBJECT_COLUMNS, ValidationError, validate

ROOT = Path(__file__).resolve().parent
CSV_FILE = ROOT / "cell-count.csv"
SCHEMA_FILE = ROOT / "schema.sql"
DB_FILE = ROOT / "cell_counts.db"


def collapse_subjects(rows: list[dict]) -> dict[tuple[str, str], dict]:
    """One record per (project, subject); validate() already guarantees agreement."""
    subjects: dict[tuple[str, str], dict] = {}
    for row in rows:
        key = (row["project"], row["subject"])
        subjects.setdefault(key, {col: row[col] for col in SUBJECT_COLUMNS})
    return subjects


def insert_subjects(conn: sqlite3.Connection, subjects: dict) -> dict[tuple[str, str], int]:
    subject_ids = {}
    for (project, subject), fields in subjects.items():
        cur = conn.execute(
            "INSERT INTO subjects (project, subject, condition, age, sex, treatment, response) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                project, subject, fields["condition"], int(fields["age"]), fields["sex"],
                fields["treatment"], fields["response"] or None,
            ),
        )
        subject_ids[(project, subject)] = cur.lastrowid
    return subject_ids


def insert_samples_and_counts(
    conn: sqlite3.Connection, rows: list[dict], subject_ids: dict[tuple[str, str], int]
) -> None:
    for row in rows:
        subject_id = subject_ids[(row["project"], row["subject"])]
        conn.execute(
            "INSERT INTO samples (sample, subject_id, sample_type, time_from_treatment_start) "
            "VALUES (?, ?, ?, ?)",
            (row["sample"], subject_id, row["sample_type"], int(row["time_from_treatment_start"])),
        )
        conn.executemany(
            "INSERT INTO cell_counts (sample, population, count) VALUES (?, ?, ?)",
            [(row["sample"], pop, int(row[pop])) for pop in POPULATIONS],
        )


def check(conn: sqlite3.Connection, rows: list[dict]) -> None:
    """Post-build sanity checks the schema itself can't express."""
    def one(sql, params=()):
        return conn.execute(sql, params).fetchone()[0]

    n_subjects = len({(r["project"], r["subject"]) for r in rows})
    assert one("SELECT COUNT(*) FROM subjects") == n_subjects
    assert one("SELECT COUNT(*) FROM samples") == len(rows)
    assert one("SELECT COUNT(*) FROM cell_counts") == len(rows) * len(POPULATIONS)

    for pop in POPULATIONS:
        expected = sum(int(r[pop]) for r in rows)
        assert one("SELECT SUM(count) FROM cell_counts WHERE population = ?", (pop,)) == expected, pop

    # the composite PK rules out duplicate (sample, population) pairs but not a
    # sample missing one; the grand total above can't catch an uneven split either
    assert one(
        "SELECT COUNT(*) FROM samples s WHERE "
        "(SELECT COUNT(*) FROM cell_counts c WHERE c.sample = s.sample) <> "
        "(SELECT COUNT(*) FROM populations)"
    ) == 0

    assert conn.execute("PRAGMA foreign_key_check").fetchall() == []

    assert one("SELECT MIN(total_count) FROM sample_frequencies") > 0
    assert one(
        "SELECT MAX(ABS(pct - 100)) FROM "
        "(SELECT SUM(percentage) AS pct FROM sample_frequencies GROUP BY sample)"
    ) < 1e-9


def build_database(rows: list[dict], db_path: Path) -> None:
    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(SCHEMA_FILE.read_text(encoding="utf-8"))

        subjects = collapse_subjects(rows)
        subject_ids = insert_subjects(conn, subjects)
        insert_samples_and_counts(conn, rows, subject_ids)

        check(conn, rows)
        conn.commit()
    finally:
        conn.close()


def main() -> None:
    try:
        rows = validate(CSV_FILE)
    except ValidationError as exc:
        print(f"INVALID: {exc}", file=sys.stderr)
        sys.exit(1)

    tmp_path = DB_FILE.with_suffix(".tmp")
    tmp_path.unlink(missing_ok=True)
    build_database(rows, tmp_path)
    os.replace(tmp_path, DB_FILE)
    print(f"OK: loaded {len(rows)} rows into {DB_FILE.name}")


if __name__ == "__main__":
    main()
