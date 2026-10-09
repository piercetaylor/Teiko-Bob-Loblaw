from cellcounts import baseline


def test_baseline_samples(real_conn):
    samples = baseline.baseline_samples(real_conn)
    assert list(samples.columns) == ["sample", "subject_id", "project", "response", "sex"]
    assert len(samples) == 656
    assert samples["subject_id"].is_unique


def test_samples_per_project(real_conn):
    out = baseline.samples_per_project(real_conn).set_index("project")["samples"]
    assert out.to_dict() == {"prj1": 384, "prj3": 272}
    assert out.sum() == 656


def test_subjects_per_response(real_conn):
    out = baseline.subjects_per_response(real_conn).set_index("response")["subjects"]
    assert out.to_dict() == {"yes": 331, "no": 325}


def test_subjects_per_sex(real_conn):
    out = baseline.subjects_per_sex(real_conn).set_index("sex")["subjects"]
    assert out.to_dict() == {"F": 312, "M": 344}


def test_baseline_excludes_other_samples(make_conn, row):
    conn = make_conn([
        row(sample="keep"),
        row(sample="day7", subject="s2", time_from_treatment_start="7"),
        row(sample="wb", subject="s3", sample_type="WB"),
        row(sample="lung", subject="s4", condition="lung"),
        row(sample="other", subject="s5", treatment="phauximab"),
    ])
    assert list(baseline.baseline_samples(conn)["sample"]) == ["keep"]
    assert baseline.samples_per_project(conn)["samples"].sum() == 1


def test_male_responder_b_cell_mean(real_conn, make_conn, row):
    assert baseline.male_responder_b_cell_mean(real_conn) == 10206.15
    conn = make_conn([
        row(sample="keep", b_cell="100"),
        row(sample="wb", subject="s2", sample_type="WB", treatment="phauximab", b_cell="300"),
        row(sample="female", subject="s3", sex="F", b_cell="1"),
        row(sample="non", subject="s4", response="no", b_cell="1"),
        row(sample="day7", subject="s5", time_from_treatment_start="7", b_cell="1"),
        row(sample="lung", subject="s6", condition="lung", b_cell="1"),
    ])
    assert baseline.male_responder_b_cell_mean(conn) == 200.0
