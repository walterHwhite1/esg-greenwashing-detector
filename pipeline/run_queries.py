import sqlite3
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "esg.db"


def run_query(conn, label, query):
    print(f"\n=== {label} ===")
    df = pd.read_sql_query(query, conn)
    print(df)


def main():
    conn = sqlite3.connect(DB_PATH)

    run_query(
        conn,
        "All claims with company name (JOIN)",
        """
        SELECT c.company_name, cl.claim_text, cl.claim_type
        FROM claims cl
        JOIN companies c ON cl.company_id = c.company_id;
        """,
    )

    run_query(
        conn,
        "Count of claims per company",
        """
        SELECT c.company_name, COUNT(*) AS total_claims
        FROM claims cl
        JOIN companies c ON cl.company_id = c.company_id
        GROUP BY c.company_name;
        """,
    )

    run_query(
        conn,
        "Only specific claims (has number + baseline + target)",
        """
        SELECT c.company_name, cl.claim_text
        FROM claims cl
        JOIN companies c ON cl.company_id = c.company_id
        WHERE cl.has_number = 1
          AND cl.has_baseline_year = 1
          AND cl.has_target_year = 1;
        """,
    )

    run_query(
        conn,
        "Companies missing Scope 3 data",
        """
        SELECT c.company_name, e.year, e.scope_3_kg
        FROM emissions e
        JOIN companies c ON e.company_id = c.company_id
        WHERE e.scope_3_kg IS NULL;
        """,
    )

    run_query(
        conn,
        "Emissions year-over-year change for Delta",
        """
        SELECT year, scope_1_kg,
               scope_1_kg - LAG(scope_1_kg) OVER (ORDER BY year) AS change_from_prior_year
        FROM emissions
        WHERE company_id = 1
        ORDER BY year;
        """,
    )

    conn.close()


if __name__ == "__main__":
    main()