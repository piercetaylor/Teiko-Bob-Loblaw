PRAGMA foreign_keys = ON;

CREATE TABLE subjects (
    subject_id INTEGER PRIMARY KEY,
    project TEXT NOT NULL,
    subject TEXT NOT NULL,
    condition TEXT NOT NULL,
    age INTEGER NOT NULL CHECK (age >= 0),
    sex TEXT NOT NULL CHECK (sex IN ('M', 'F')),
    treatment TEXT NOT NULL,
    response TEXT CHECK (response IN ('yes', 'no')),
    UNIQUE (project, subject),
    CHECK (treatment <> 'none' OR response IS NULL)
) STRICT;

CREATE TABLE samples (
    sample TEXT PRIMARY KEY NOT NULL,
    subject_id INTEGER NOT NULL REFERENCES subjects(subject_id),
    sample_type TEXT NOT NULL,
    time_from_treatment_start INTEGER NOT NULL
) STRICT;

CREATE TABLE populations (
    population TEXT PRIMARY KEY NOT NULL,
    label TEXT NOT NULL,
    sort_order INTEGER NOT NULL UNIQUE CHECK (sort_order > 0)
) STRICT;

INSERT INTO populations (population, label, sort_order) VALUES
    ('b_cell', 'B cell', 1),
    ('cd8_t_cell', 'CD8 T cell', 2),
    ('cd4_t_cell', 'CD4 T cell', 3),
    ('nk_cell', 'NK cell', 4),
    ('monocyte', 'Monocyte', 5);

CREATE TABLE cell_counts (
    sample TEXT NOT NULL REFERENCES samples(sample),
    population TEXT NOT NULL REFERENCES populations(population),
    count INTEGER NOT NULL CHECK (count >= 0),
    PRIMARY KEY (sample, population)
) STRICT;

CREATE INDEX idx_samples_subject ON samples(subject_id);
CREATE INDEX idx_subjects_cohort ON subjects(condition, treatment, response);
CREATE INDEX idx_samples_cohort ON samples(sample_type, time_from_treatment_start);

CREATE VIEW sample_frequencies AS
SELECT
    cc.sample AS sample,
    totals.total_count AS total_count,
    cc.population AS population,
    cc.count AS count,
    100.0 * cc.count / NULLIF(totals.total_count, 0) AS percentage
FROM cell_counts cc
JOIN (
    SELECT sample, SUM(count) AS total_count
    FROM cell_counts
    GROUP BY sample
) totals ON totals.sample = cc.sample;

CREATE VIEW sample_detail AS
SELECT
    s.sample,
    s.sample_type,
    s.time_from_treatment_start,
    sub.subject_id,
    sub.project,
    sub.subject,
    sub.condition,
    sub.age,
    sub.sex,
    sub.treatment,
    sub.response
FROM samples s
JOIN subjects sub ON sub.subject_id = s.subject_id;
