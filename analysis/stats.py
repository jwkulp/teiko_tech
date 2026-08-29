import sqlite3
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from scipy.stats import mannwhitneyu
from pathlib import Path
from statsmodels.stats.multitest import multipletests


SCRIPT_DIR = Path(__file__).resolve().parent
DB_PATH = SCRIPT_DIR.parent / 'cell-counts.db'
STATS_OUTPUT_PATH = SCRIPT_DIR.parent / 'output' / 'responder_stats.csv'
PLOT_OUTPUT_PATH = SCRIPT_DIR.parent / 'output' / 'responder_boxplot.png'


def get_comp_data(db_path: Path) -> pd.DataFrame:
    conn = sqlite3.connect(db_path)
    df = pd.read_sql_query("""
        SELECT
            su.subject_id AS subject,
            s.responded,
            cc.cell_type AS population,
            ROUND(cc.count * 100.0 / SUM(cc.count) OVER (PARTITION BY cc.sample_id), 2) AS percentage
            FROM cell_counts cc
            JOIN samples s ON s.sample_id = cc.sample_id
            JOIN subjects su ON su.subject_id = s.subject_id
            WHERE su.condition = 'melanoma'
                AND s.treatment = 'miraclib'
                AND s.sample_type = 'PBMC'
                AND s.responded IN ('yes', 'no')
    """, conn)
    conn.close()
    return df


def agg_by_subject(df: pd.DataFrame) -> pd.DataFrame:
    return (
        df.groupby(['subject', 'responded', 'population'], as_index=False)['percentage']
        .mean()
    )


def run_tests(subject_df: pd.DataFrame) -> pd.DataFrame:
    results = []
    for population, group in subject_df.groupby('population'):
        responders = group.loc[group['responded'] == 'yes', 'percentage']
        non_responders = group.loc[group['responded'] == 'no', 'percentage']
        stat, p_val = mannwhitneyu(responders, non_responders)
        results.append((population, len(responders), len(non_responders), stat, p_val))

    results_df = pd.DataFrame(
        results,
        columns=['population', 'n_responders', 'n_non_responders', 'statistic', 'p_value']
    )

    _, corrected_p, _, _ = multipletests(results_df['p_value'], method='fdr_bh')
    results_df['corrected_p_value'] = corrected_p
    results_df['significant'] = results_df['corrected_p_value'] < 0.05

    return results_df


def plot_boxplot(subject_df: pd.DataFrame, output_path: Path) -> None:
    plt.figure(figsize=(10,6))
    sns.boxplot(data=subject_df, x='population', y='percentage', hue='responded')
    plt.title(
        'Melanoma Patients Treated with Miraclib (PBMC Samples)\n'
        'Cell Population Relative Frequency: Responders vs Non-Responders'
    )
    plt.ylabel('Relative Frequency (%)')
    plt.xlabel('Cell Population')
    plt.tight_layout()
    plt.savefig(output_path)
    plt.close()


def main() -> None:
    STATS_OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    df = get_comp_data(DB_PATH)
    subject_df = agg_by_subject(df)

    results_df = run_tests(subject_df)
    results_df.to_csv(STATS_OUTPUT_PATH, index=False)

    plot_boxplot(subject_df, PLOT_OUTPUT_PATH)

if __name__ == '__main__':
    main()
