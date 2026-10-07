"""Database location and read-only connections for the analysis modules."""
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_FILE = ROOT / "cell-count.db"
OUTPUT_DIR = ROOT / "outputs"


def connect_readonly(db_path: Path = DB_FILE) -> sqlite3.Connection:
    """Open the database for reading."""
    db_path = Path(db_path)
    if not db_path.exists():
        raise FileNotFoundError(f"{db_path} not found; run `python load_data.py` first")
    return sqlite3.connect(f"{db_path.as_uri()}?mode=ro", uri=True)


def population_order(conn: sqlite3.Connection) -> list[str]:
    """Population names in display order, read from the populations table."""
    return [r[0] for r in conn.execute("SELECT population FROM populations ORDER BY sort_order")]


def population_labels(conn: sqlite3.Connection) -> dict[str, str]:
    """Population name to display label, e.g. cd8_t_cell -> CD8 T cell."""
    return dict(conn.execute("SELECT population, label FROM populations ORDER BY sort_order"))
