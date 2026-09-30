from pathlib import Path

import pandas as pd
import sqlite3
import streamlit as st


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "esg.db"

@st.cache_data
def load_scores():
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT * FROM scores", conn)
    conn.close()
    return df

@st.cache_data
def load_claims(company_id):
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query(
        "SELECT * FROM claims WHERE company_id = ?",
        conn,
        params=(company_id,),
    )
    conn.close()
    return df

@st.cache_data
def load_emissions(company_id):
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query(
        "SELECT * FROM emissions WHERE company_id = ? ORDER BY year",
        conn,
        params=(company_id,),
    )
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
    st.divider()
    st.subheader("Company Detail")

    company_names = sorted(scores["company_name"].unique())
    selected_name = st.selectbox("Choose a company", company_names)

    selected_row = scores[scores["company_name"] == selected_name].iloc[0]
    company_id = int(selected_row["company_id"])

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Promotion", f"{selected_row['promotion_score']:.0f}")
    col2.metric("Substantiation", f"{selected_row['substantiation_score']:.0f}")

    perf = selected_row["performance_score"]
    col3.metric("Performance", "N/A" if pd.isna(perf) else f"{perf:.0f}")

    risk = selected_row["risk_score"]
    col4.metric("Risk Score", "N/A" if pd.isna(risk) else f"{risk:.1f}", selected_row["risk_label"])

    claims = load_claims(company_id)
    company_claims = claims[claims["source_type"].isin(["company_report", "company_website", "advertisement"])]
    external_claims = claims[~claims["source_type"].isin(["company_report", "company_website", "advertisement"])]

    specific_count = (
        (company_claims["has_number"] == 1)
        & (company_claims["has_baseline_year"] == 1)
        & (company_claims["has_target_year"] == 1)
    ).sum()

    summary_parts = [
        f"{len(company_claims)} company-sourced claim(s) logged, {specific_count} fully specific."
    ]
    if len(external_claims) > 0:
        summary_parts.append(f"{len(external_claims)} external/regulatory mention(s) on record.")

    emissions = load_emissions(company_id)
    scope1 = emissions.dropna(subset=["scope_1_kg"]).sort_values("year")
    if len(scope1) >= 2:
        latest = scope1.iloc[-1]
        previous = scope1.iloc[-2]
        pct = (latest["scope_1_kg"] - previous["scope_1_kg"]) / previous["scope_1_kg"] * 100
        direction = "rose" if pct > 0 else "fell"
        summary_parts.append(
            f"Scope 1 emissions {direction} {abs(pct):.1f}% from {int(previous['year'])} to {int(latest['year'])}."
        )
    else:
        summary_parts.append("Not enough emissions history to calculate a year-over-year trend.")

    st.write(" ".join(summary_parts))

    st.markdown("**Claims**")
    st.dataframe(
        claims[["claim_text", "claim_type", "source_type", "source_name", "confidence"]],
        hide_index=True,
        use_container_width=True,
    )

    st.markdown("**Emissions**")
    if not emissions.empty:
        st.dataframe(
            emissions[["year", "scope_1_kg", "scope_2_kg", "scope_3_kg", "externally_assured"]],
            hide_index=True,
            use_container_width=True,
        )
        if len(scope1) >= 2:
            st.bar_chart(scope1.set_index("year")["scope_1_kg"])
    else:
        st.info("No emissions data on record for this company.")


if __name__ == "__main__":
    main()