import sqlite3
import csv
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
DB_PATH = SCRIPT_DIR.parent / 'cell-counts.db'
OUTPUT_PATH = SCRIPT_DIR.parent / 'output' / 'cell_frequencies.csv'


def compute_frequencies(db_path: Path, output_path: Path) -> None:
    conn = sqlite3.connect(db_path)
    cursor = conn.execute("""
        SELECT
            sample_id AS sample,
            SUM(count) OVER w AS total_count,
            cell_type AS population,
            count,
            ROUND(count * 100.0 / SUM(count) OVER w, 2) AS percentage
        FROM cell_counts
        WINDOW w AS (PARTITION BY sample_id)
        ORDER BY sample, population;
    """)

    rows = cursor.fetchall()
    conn.close()

    with open(output_path, 'w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(['sample', 'total_count', 'population', 'count', 'percentage'])
        writer.writerows(rows)


def main() -> None:
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    compute_frequencies(DB_PATH, OUTPUT_PATH)


if __name__ == "__main__":
    main()
