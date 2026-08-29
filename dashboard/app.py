import sqlite3
from pathlib import Path

import pandas as pd
import streamlit as st

SCRIPT_DIR = Path(__file__).resolve().parent
DB_PATH = SCRIPT_DIR.parent / 'cell-counts.db'
OUTPUT_DIR = SCRIPT_DIR.parent / 'output'


def get_connection():
    return sqlite3.connect(DB_PATH)


def show_sample_frequencies():
    st.header('Cell Type Frequency by Sample')

    conn = get_connection()
    try:
        samples = pd.read_sql_query('SELECT sample_id FROM samples ORDER BY sample_id', conn)
    finally:
        conn.close()

    selected_sample = st.selectbox('Select a sample', samples['sample_id'])

    conn = get_connection()
    try:
        freq_df = pd.read_sql_query(
            """
            SELECT
                cell_type AS population,
                count,
                ROUND(count * 100.0 / SUM(count) OVER (), 2) AS percentage
            FROM cell_counts
            WHERE sample_id = ?
            ORDER BY population
            """,
            conn,
            params=(selected_sample,),
        )
    finally:
        conn.close()

    st.dataframe(freq_df, width='stretch')


def show_responder_analysis():
    st.header('Responders vs Non-Responders (Melanoma, miraclib, PBMC)')

    stats_path = OUTPUT_DIR / 'responder_stats.csv'
    boxplot_path = OUTPUT_DIR / 'responder_boxplot.png'

    if stats_path.exists():
        st.dataframe(pd.read_csv(stats_path), width='stretch')
    else:
        st.warning('Run `make pipeline` first to generate responder_stats.csv')

    if boxplot_path.exists():
        st.image(str(boxplot_path))
    else:
        st.warning('Run `make pipeline` first to generate the boxplot')


def show_baseline_subset():
    st.header('Baseline Miraclib Melanoma PBMC Samples (time=0)')

    project_path = OUTPUT_DIR / 'baseline_samples_per_project.csv'
    response_path = OUTPUT_DIR / 'baseline_subjects_by_response.csv'
    sex_path = OUTPUT_DIR / 'baseline_subjects_by_sex.csv'
    avg_b_cells_path = OUTPUT_DIR / 'avg_b_cells_male_responders.txt'

    col_a, col_b, col_c = st.columns(3)
    with col_a:
        st.subheader('Samples per project')
        if project_path.exists():
            st.dataframe(pd.read_csv(project_path))
        else:
            st.warning('Run `make pipeline` first')

    with col_b:
        st.subheader('Subjects by response')
        if response_path.exists():
            st.dataframe(pd.read_csv(response_path))
        else:
            st.warning('Run `make pipeline` first')

    with col_c:
        st.subheader('Subjects by sex')
        if sex_path.exists():
            st.dataframe(pd.read_csv(sex_path))
        else:
            st.warning('Run `make pipeline` first')

    if avg_b_cells_path.exists():
        avg_b_cells = avg_b_cells_path.read_text().strip()
        st.metric('Avg B cells, melanoma male responders at time=0 (all sample/treatment types)', avg_b_cells)
    else:
        st.warning('Run `make pipeline` first to generate avg_b_cells_male_responders.txt')


def main():
    st.title('Immune Cell Population Explorer')

    if not DB_PATH.exists():
        st.error('Database not found. Run `make pipeline` first.')
        st.stop()

    show_sample_frequencies()
    show_responder_analysis()
    show_baseline_subset()


if __name__ == '__main__':
    main()
