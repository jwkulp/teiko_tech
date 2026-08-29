# Teiko Cell Count Analysis

This project loads the data from `cell-count.csv` into a SQLite database and uses it
to answer a few questions about immune cell populations, treatment response, and a
baseline subset of patients.

## Running it

```bash
make setup      # install dependencies
make pipeline   # init the database, load the data, and generate all tables/plots
make dashboard  # start the interactive dashboard at http://localhost:8501
```

`make pipeline` runs the whole thing start to finish, no manual steps needed. Once it
finishes, the database (`cell-counts.db`) will be sitting in the repo root, and
everything else generated (tables, the boxplot, the B-cell average) will be in
`output/`.

The dashboard only runs locally for now (`http://localhost:8501` via `make
dashboard`), it hasn't been deployed anywhere public.

## The database schema

The data ends up split across three tables instead of one big table matching the CSV:

```sql
subjects (subject_id PK, project, condition, sex, age)
samples  (sample_id PK, subject_id FK, sample_type, time_from_treatment, treatment, responded)
cell_counts (sample_id FK, cell_type, count, PK(sample_id, cell_type))
```

The reason for splitting it up is that a single row in the CSV is really describing
three different things at once: a fact about the subject (their age, sex, condition),
a fact about one particular sample draw (what treatment they were on, whether they'd
responded yet), and a measurement of that sample (the five cell counts). Keeping it all
in one table means subject information like age and sex would get repeated on every
single sample row, which is wasteful and also risky, since it would be easy for those
repeated values to accidentally end up inconsistent with each other.

Deciding what belongs on `subjects` versus `samples` came down to asking whether a
value stays true for the whole subject or is really tied to one specific point in
time. Age, sex, and condition don't change over the course of a two-week trial, so
those stayed on `subjects`. Treatment and response, on the other hand, are tied to a
specific sample draw, since in general a patient's treatment could change or their
response could only become known partway through, even though in this particular
dataset they happen to stay the same across a subject's samples.

The cell counts are also their own table, with one row per sample per cell type,
instead of five separate columns on the samples table. This is mostly because adding a
sixth cell type later would just mean inserting more rows, not changing the table
structure, and computing something like relative frequency works the same way no
matter how many cell types exist.

The schema also uses primary keys, foreign keys, and check constraints so the database
itself enforces things like "a sample must belong to a real subject," rather than
relying on the Python code to always get that right.

### Scaling this up

If this dataset grew to hundreds of projects and thousands of samples, a few things
would need to change. Indexes would need to be added on columns that get filtered or
joined on a lot, like `subject_id` and `condition`, since right now the schema mostly
just relies on the primary keys. SQLite itself would likely become a bottleneck too,
since it doesn't handle multiple people writing to it at the same time very well, so a
real database like Postgres would probably be needed once more than one person is
querying or loading data at once. The long-format cell counts table would keep working
fine at a larger scale, since new cell types or new metrics wouldn't require any schema
changes, unlike a wide-column version. If certain analyses (like the frequency table)
get queried very often, it would also make sense to precompute and store the result
somewhere instead of recalculating it from scratch every time.

## Code structure

```
models.py               # Subject, Sample dataclasses, and the Response enum
load_data.py             # Part 1: builds the schema and loads the CSV
analysis/frequencies.py  # Part 2: relative frequency table
analysis/stats.py        # Part 3: responder vs non-responder comparison, plus the boxplot
analysis/queries.py      # Part 4: baseline subset breakdowns and the B-cell average
dashboard/app.py         # the interactive dashboard
output/                  # everything the pipeline generates
```

`load_data.py` has to live in the root directory because of the assignment
requirements, so the rest of the project just stays flat as well instead of using a
`src` folder, which wouldn't really be adding anything useful here anyway since this
isn't a package that gets installed anywhere.

Each script in `analysis/` can be run on its own, but can also be imported by other
files, which is what lets `make pipeline` run them one after another and also lets the
dashboard reuse the same queries instead of duplicating logic.

One thing worth explaining about `models.py`: the `Response` field is an enum
(`YES`, `NO`, `NOT_APPL`) instead of just `Optional[bool]`. A blank response in the CSV
doesn't actually mean the data is missing, it means the subject hadn't been treated
yet, so it seemed important not to lump that in with an actual unknown value.

Part 3 also has a couple of choices worth explaining since they're not obvious just
from reading the code. Each subject shows up in multiple samples (different
timepoints), so before running any statistics, the samples get averaged down to one
value per subject. Otherwise the same person's repeated measurements would get counted
as if they were separate people, which would make the results look more significant
than they really are. A Mann-Whitney U test was used instead of a t-test since there's
no reason to assume the relative frequencies are normally distributed, especially with
a fairly small number of subjects once everything gets filtered down. Since five
separate tests get run (one per cell population), the p-values also get adjusted using
a Benjamini-Hochberg correction, since running that many tests at once increases the
odds that one of them looks significant purely by chance.
