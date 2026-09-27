import sqlite3
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = PROJECT_ROOT / "data" / "raw"
DB_PATH = PROJECT_ROOT / "esg.db"
SCHEMA_PATH = PROJECT_ROOT / "sql" / "create_tables.sql"


def create_schema(conn):
    with open(SCHEMA_PATH, "r") as f:
        conn.executescript(f.read())


def load_csvs_to_db(conn):
    companies = pd.read_csv(RAW_DIR / "companies.csv")
    claims = pd.read_csv(RAW_DIR / "claims.csv")
    emissions = pd.read_csv(RAW_DIR / "emissions.csv")

    companies.to_sql("companies", conn, if_exists="append", index=False)
    claims.to_sql("claims", conn, if_exists="append", index=False)
    emissions.to_sql(
        "emissions",
        conn,
        if_exists="append",
        index=False,
    )


def main():
    if DB_PATH.exists():
        DB_PATH.unlink()

    conn = sqlite3.connect(DB_PATH)
    create_schema(conn)
    load_csvs_to_db(conn)
    conn.commit()
    conn.close()

    print(f"Database created at {DB_PATH}")


if __name__ == "__main__":
    main()