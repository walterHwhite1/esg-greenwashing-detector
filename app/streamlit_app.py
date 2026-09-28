from pathlib import Path

import pandas as pd
import sqlite3
import streamlit as st


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "esg.db"


def load_scores():
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT * FROM scores", conn)
    conn.close()
    return df


def main():
    st.set_page_config(page_title="ESG Greenwashing Detector", layout="wide")

    st.title("ESG Greenwashing Detector")
    st.caption("Comparing airline sustainability claims against real emissions performance")

    scores = load_scores()

    search = st.text_input("Search for a company")

    if search:
        filtered = scores[scores["company_name"].str.contains(search, case=False, na=False)]
    else:
        filtered = scores

    st.subheader("Leaderboard")
    display_df = filtered[[
        "company_name", "promotion_score", "substantiation_score",
        "performance_score", "risk_score", "risk_label"
    ]].sort_values("risk_score", ascending=False, na_position="last")

    st.dataframe(display_df, use_container_width=True, hide_index=True)

    st.caption("Risk score is a discrepancy indicator, not proof of greenwashing. See Methodology for details.")


if __name__ == "__main__":
    main()