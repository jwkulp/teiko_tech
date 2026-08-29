import sqlite3
from pathlib import Path

import pandas as pd


SCRIPT_DIR = Path(__file__).resolve().parent
DB_PATH = SCRIPT_DIR.parent / 'cell-counts.db'
OUTPUT_DIR = SCRIPT_DIR.parent / 'output'


def get_baseline_subset(db_path: Path) -> pd.DataFrame:
    conn = sqlite3.connect(db_path)
    df = pd.read_sql_query("""
        SELECT
            s.sample_id AS sample,
            s.subject_id AS subject,
            s.responded,
            su.project,
            su.sex
        FROM samples s
        JOIN subjects su ON su.subject_id = s.subject_id
        WHERE su.condition = 'melanoma'
          AND s.sample_type = 'PBMC'
          AND s.treatment = 'miraclib'
          AND s.time_from_treatment = 0
    """, conn)
    conn.close()
    return df


def samples_per_project(baseline_df: pd.DataFrame) -> pd.DataFrame:
    return (
        baseline_df.groupby('project', as_index=False)['sample']
        .count()
        .rename(columns={'sample': 'sample_count'})
    )


def subjects_by_response(baseline_df: pd.DataFrame) -> pd.DataFrame:
    return (
        baseline_df.drop_duplicates('subject')
        .groupby('responded', as_index=False)['subject']
        .count()
        .rename(columns={'subject': 'subject_count'})
    )


def subjects_by_sex(baseline_df: pd.DataFrame) -> pd.DataFrame:
    return (
        baseline_df.drop_duplicates('subject')
        .groupby('sex', as_index=False)['subject']
        .count()
        .rename(columns={'subject': 'subject_count'})
    )


def average_b_cells_for_male_responders(db_path: Path) -> float:
    conn = sqlite3.connect(db_path)
    df = pd.read_sql_query("""
        SELECT cc.count
        FROM cell_counts cc
        JOIN samples s ON s.sample_id = cc.sample_id
        JOIN subjects su ON su.subject_id = s.subject_id
        WHERE su.condition = 'melanoma'
          AND su.sex = 'M'
          AND s.responded = 'yes'
          AND s.time_from_treatment = 0
          AND cc.cell_type = 'b_cell'
    """, conn)
    conn.close()
    return round(df['count'].mean(), 2)


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    baseline_df = get_baseline_subset(DB_PATH)

    project_counts = samples_per_project(baseline_df)
    response_counts = subjects_by_response(baseline_df)
    sex_counts = subjects_by_sex(baseline_df)

    project_counts.to_csv(OUTPUT_DIR / 'baseline_samples_per_project.csv', index=False)
    response_counts.to_csv(OUTPUT_DIR / 'baseline_subjects_by_response.csv', index=False)
    sex_counts.to_csv(OUTPUT_DIR / 'baseline_subjects_by_sex.csv', index=False)

    avg_b_cells = average_b_cells_for_male_responders(DB_PATH)
    with open(OUTPUT_DIR / 'avg_b_cells_male_responders.txt', 'w') as f:
        f.write(f'{avg_b_cells:.2f}\n')


if __name__ == '__main__':
    main()
