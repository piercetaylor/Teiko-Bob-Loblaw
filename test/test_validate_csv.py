import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from validate_csv import (
    CSV_FILE,
    ValidationError,
    check_counts,
    check_response_treatment,
    check_subject_metadata,
    validate,
)

BASE_ROW = {
    "project": "prj1", "subject": "s1", "condition": "melanoma", "age": "50",
    "sex": "M", "treatment": "miraclib", "response": "yes",
    "sample": "smp1", "sample_type": "PBMC", "time_from_treatment_start": "0",
    "b_cell": "100", "cd8_t_cell": "200", "cd4_t_cell": "300",
    "nk_cell": "400", "monocyte": "500",
}


def row(**overrides):
    return {**BASE_ROW, **overrides}


def test_counts_reject_negative():
    with pytest.raises(ValidationError):
        check_counts([row(b_cell="-1")])


def test_counts_reject_non_numeric():
    with pytest.raises(ValidationError):
        check_counts([row(b_cell="")])


def test_counts_accept_valid():
    check_counts([row()])


def test_response_treatment_rejects_mismatch():
    with pytest.raises(ValidationError):
        check_response_treatment([row(response="", treatment="miraclib")])


def test_response_treatment_accepts_none_pair():
    check_response_treatment([row(response="", treatment="none")])


def test_response_treatment_rejects_bad_value():
    with pytest.raises(ValidationError):
        check_response_treatment([row(response="maybe")])


def test_subject_metadata_rejects_conflict():
    rows = [row(sample="smp1"), row(sample="smp2", age="51")]
    with pytest.raises(ValidationError):
        check_subject_metadata(rows)


def test_subject_metadata_accepts_repeats():
    rows = [row(sample="smp1"), row(sample="smp2", time_from_treatment_start="7")]
    check_subject_metadata(rows)


def test_real_csv_is_valid():
    validate(CSV_FILE)
