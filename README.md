# Loblaw Bio immune cell counts

Bob Loblaw is running a clinical trial on a drug candidate, miraclib, and wants to know how it affects immune cell
populations. The trial data includes 10,500 samples from 3,500 patients in `cell-count.csv`, with counts
for 5 cell populations: B cells, CD8 T cells, CD4 T cells, NK cells and monocytes.

Dashboard: _STREAMLIT_LINK_TO_BE_ADDED_.

The dashboard also runs locally at <http://localhost:8501> with `make dashboard`.

## Running it

Python 3.12. The Makefile uses `python3`, which is what GitHub Codespaces provides.

```sh
make setup      # pip install -r requirements.txt
make pipeline   # python3 load_data.py, then python3 -m cellcounts.report
make dashboard  # Streamlit dashboard reading cell-count.db
make test       # pytest; the dashboard tests skip until the pipeline has built the database
```

The pipeline builds `cell-count.db` in the root of the repository, then prints tables for Parts 2-4, and
writes them to `outputs/`, along with the boxplot for Part 3. To use another interpreter, pass it in:
`make pipeline PYTHON=.venv/Scripts/python.exe`.

## Part 1: database

`load_data.py` validates the CSV file then loads it into 4 tables: `subjects`, `samples`,
`populations` and `cell_counts`. A subject's project, condition, age, sex, treatment and
response are the same on all three of their samples, so they are stored in the `subjects` table.
Each sample is one row in `samples`, and each count is one row in the `cell_counts` table, keyed by sample
and population. Adding another cell population requires another row in `populations` and an entry added to
`validate_csv.py`, with no change to the schema or the analysis. The `sample_frequencies` view computes
each population's percentage of its sample total, and is used in parts 2-4 for the downstream analysis.

Schema (`schema.sql`):

```text
subjects     subject_id PK, project, subject, condition, age, sex, treatment, response
samples      sample PK, subject_id -> subjects, sample_type, time_from_treatment_start
populations  population PK, label, sort_order
cell_counts  (sample -> samples, population -> populations) PK, count

sample_frequencies  view: sample, total_count, population, count, percentage
sample_detail       view: each sample joined to its subject
```

Columns are typed and checked (`STRICT`, `CHECK`, `FOREIGN KEY`).

## Part 2: relative frequencies

One row per sample and population, 52,500 in all, with the columns `sample`, `total_count`,
`population`, `count` and `percentage`. The total is the sum of a sample's five counts and the
percentage is each count as a share of that total. The dashboard filters the table and compares
mean composition across projects, conditions, treatments, days or responses.

## Part 3: responders versus non-responders

No population differs significantly between melanoma responders and non-responders on
miraclib, using PBMC samples from 331 responding and 325 non-responding subjects.

Each subject has samples at days 0, 7 and 14. Treating them as three independent observations
would triple the sample size, so they were averaged to one value per subject. The groups were
compared utilizing a two-sided Mann-Whitney U test, chosen before looking at the data because it
does not assume normality. Five populations give five chances to find a difference, so the
p-values were Benjamini-Hochberg (BH) adjusted and significance is judged on the adjusted value.

| Population | Median responder (%) | Median non-responder (%) | Rank-biserial | p | Adjusted p |
| --- | --- | --- | --- | --- | --- |
| B cell | 9.67 | 9.84 | -0.043 | 0.346 | 0.432 |
| CD8 T cell | 24.90 | 25.01 | -0.022 | 0.622 | 0.622 |
| CD4 T cell | 30.21 | 29.82 | 0.113 | 0.012 | 0.062 |
| NK cell | 14.74 | 14.96 | -0.069 | 0.127 | 0.317 |
| Monocyte | 19.79 | 20.28 | -0.050 | 0.264 | 0.432 |

**CD4 T cells come closest.** Responders have a median 0.39 percentage points higher, and the
raw p of 0.012 would pass on its own, but the BH-adjusted p of 0.062 does not. The effect is small:
a random responder has a higher CD4 frequency than a random non-responder about 56% of the time,
against 50% for no effect. The subject means are close to normal (skewed below 0.3), so a Welch
t-test could be valid, and it gives CD4 an adjusted p of 0.023. The two tests disagree, so CD4 is
borderline: worth testing with a new or larger data set, but not a finding from this trial.

Three checks are shown in the dashboard:

1. Pooling the 1,968 samples across days as if independent is wrong in principle but doesn't change
   the result(CD4 p = 0.013, adjusted 0.067).
2. the only samples available before treatment, day 0 samples, gives no population an adjusted
   p value below 0.88, so there isn't a baseline signal for predicting response.
3. When testing each day separately, no p value is <= 0.05 post-BH correction on any day; the
   largest difference in this case is at day 7 for CD4 (p = 0.030) and day 14 for B cells (p = 0.014),
   consistent with an on-treatment change but this was not tested directly.

*Caveats: the five percentages share a denominator, so the five tests are not independent, and*
*project, age and sex are not adjusted for.*

## Part 4: baseline cohort

there are 656 melanoma PBMC samples at day 0 from subjects on miraclib, one per subject: 384 from 
project 1 (`prj1`) and 272 from project 3 (`prj3`). Out of these subjects, 331 responded and 325 
did not;344 are male and 312 female.

**Considering melanoma males of all sample and treatment types, what is the average number of
B cells for responders at time 0?** **10206.15**, the mean over 485 samples.

## Layout

```text
.
├── Makefile              # setup, pipeline, dashboard, test
├── requirements.txt
├── cell-count.csv        # input (Bob Loblaw's dataset)
├── schema.sql            # four tables, constraints and the two views
├── validate_csv.py       # Part 1: checks the cellcount.csv before loading it into cell-count.db
├── load_data.py          # Part 1: builds cell-count.db
├── cellcounts/
│   ├── db.py             # read-only connection and population order
│   ├── frequencies.py    # Part 2: relative frequency table
│   ├── responders.py     # Part 3: cohort query, subject means, tests, boxplot
│   ├── baseline.py       # Part 4: baseline cohort, counts
│   └── report.py         # prints Parts 2 to 4 and writes outputs/
├── dashboard.py          # Streamlit dashboard for Parts 1 to 4
├── .streamlit/
│   └── config.toml       # dashboard theme
└── test/                 # pytest; the analysis tests build their own database from cell-count.csv
```
