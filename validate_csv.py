"""Validate cell-count.csv against invariants"""
import csv
import sys
from pathlib import Path

REQUIRED_COLUMNS = {
    "project", "subject", "condition", "age", "sex", "treatment", "response",
    "sample", "sample_type", "time_from_treatment_start",
    "b_cell", "cd8_t_cell", "cd4_t_cell", "nk_cell", "monocyte",
}
POPULATIONS = ["b_cell", "cd8_t_cell", "cd4_t_cell", "nk_cell", "monocyte"]
SUBJECT_COLUMNS = ["project", "condition", "age", "sex", "treatment", "response"]

CSV_PATH = Path(__file__).resolve().parent / "cell-count.csv"


class ValidationError(Exception):
    pass


def load_rows(csv_path: Path) -> list[dict]:
    with open(csv_path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        raise ValidationError(f"{csv_path} has no data rows")
    missing = REQUIRED_COLUMNS - set(rows[0])
    if missing:
        raise ValidationError(f"missing columns: {sorted(missing)}")
    return rows


def check_counts(rows: list[dict]) -> None:
    """Counts, age and day must be non-negative integers; sex M or F; sample ids unique."""
    seen = set()
    for row in rows:
        for col in [*POPULATIONS, "age", "time_from_treatment_start"]:
            if not row[col].isdecimal():
                raise ValidationError(
                    f"sample {row['sample']}: {col}={row[col]!r} is not a non-negative integer"
                )
        if row["sex"] not in ("M", "F"):
            raise ValidationError(f"sample {row['sample']}: invalid sex {row['sex']!r}")
        if row["sample"] in seen:
            raise ValidationError(f"duplicate sample id {row['sample']!r}")
        seen.add(row["sample"])


def check_response_treatment(rows: list[dict]) -> None:
    for row in rows:
        response, treatment = row["response"], row["treatment"]
        if response not in ("yes", "no", ""):
            raise ValidationError(f"sample {row['sample']}: invalid response {response!r}")
        if (response == "") != (treatment == "none"):
            raise ValidationError(
                f"sample {row['sample']}: response {response!r} inconsistent with treatment {treatment!r}"
            )


def check_subject_metadata(rows: list[dict]) -> None:
    seen: dict[tuple[str, str], dict] = {}
    for row in rows:
        key = (row["project"], row["subject"])
        record = {col: row[col] for col in SUBJECT_COLUMNS}
        prior = seen.setdefault(key, record)
        if prior != record:
            raise ValidationError(f"subject {key}: inconsistent metadata {prior} vs {record}")


def validate(csv_path: Path) -> list[dict]:
    rows = load_rows(csv_path)
    check_counts(rows)
    check_response_treatment(rows)
    check_subject_metadata(rows)
    return rows


def main() -> None:
    try:
        rows = validate(CSV_PATH)
    except ValidationError as exc:
        print(f"INVALID: {exc}", file=sys.stderr)
        sys.exit(1)
    print(f"OK: {len(rows)} rows validated in {CSV_PATH.name}")


if __name__ == "__main__":
    main()
