import csv
import sqlite3
from pathlib import Path

from models import Subject, Sample, Response


SCRIPT_DIR = Path(__file__).resolve().parent
CSV_PATH = SCRIPT_DIR / 'cell-count.csv'
DB_PATH = SCRIPT_DIR / 'cell-counts.db'

CELL_TYPES = ['b_cell',
              'cd8_t_cell',
              'cd4_t_cell',
              'nk_cell',
              'monocyte']


def init_db(cursor: sqlite3.Cursor) -> None:
    cursor.execute("PRAGMA foreign_keys = ON")

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS subjects (
            subject_id TEXT PRIMARY KEY,
            project TEXT NOT NULL,
            condition TEXT NOT NULL,
            sex TEXT NOT NULL,
            age INTEGER NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS samples (
            sample_id TEXT PRIMARY KEY,
            subject_id TEXT NOT NULL REFERENCES subjects(subject_id),
            sample_type TEXT NOT NULL,
            time_from_treatment INTEGER NOT NULL,
            treatment TEXT NOT NULL,
            responded TEXT NOT NULL CHECK (responded IN ('yes', 'no', 'n/a'))
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cell_counts (
            sample_id TEXT NOT NULL REFERENCES samples(sample_id),
            cell_type TEXT NOT NULL,
            count INTEGER NOT NULL,
            PRIMARY KEY (sample_id, cell_type)
        )
    """)


def parse_row(row: dict[str, str]) -> tuple[Subject, Sample, list[tuple[str, str, int]]]:
    subject = Subject(
        subject_id=row['subject'],
        project=row['project'],
        condition=row['condition'],
        sex=row['sex'],
        age=int(row['age']),
    )

    sample = Sample(
        sample_id=row['sample'],
        subject_id=row['subject'],
        sample_type=row['sample_type'],
        time_from_treatment=int(row['time_from_treatment_start']),
        treatment=row['treatment'],
        responded=Response(row['response']) if row['response'] else Response.NOT_APPL,
    )

    cell_counts = [
        (row['sample'], cell_type, int(row[cell_type]))
        for cell_type in CELL_TYPES
    ]

    return subject, sample, cell_counts


def load_csv() -> list[tuple[Subject, Sample, list[tuple[str, str, int]]]]:
    with open(CSV_PATH, newline='') as file:
        reader = csv.DictReader(file)
        return [parse_row(row) for row in reader]


def load_db(rows: list[tuple[Subject, Sample, list[tuple[str, str, int]]]]) -> None:
    conn = sqlite3.connect(DB_PATH)
    try:
        cursor = conn.cursor()
        init_db(cursor)

        subjects_seen = set()
        for subject, sample, cell_counts in rows:
            if subject.subject_id not in subjects_seen:
                cursor.execute(
                    "INSERT INTO subjects VALUES (?, ?, ?, ?, ?)",
                    (
                        subject.subject_id,
                        subject.project,
                        subject.condition,
                        subject.sex,
                        subject.age,
                    ),
                )
                subjects_seen.add(subject.subject_id)

            cursor.execute(
                "INSERT INTO samples VALUES (?, ?, ?, ?, ?, ?)",
                (
                    sample.sample_id,
                    sample.subject_id,
                    sample.sample_type,
                    sample.time_from_treatment,
                    sample.treatment,
                    sample.responded.value,
                ),
            )

            cursor.executemany(
                "INSERT INTO cell_counts VALUES (?, ?, ?)",
                cell_counts,
            )

        conn.commit()
    finally:
        conn.close()


def main() -> None:
    DB_PATH.unlink(missing_ok=True)
    rows = load_csv()
    load_db(rows)


if __name__ == '__main__':
    main()
