from pathlib import Path

import pandas as pd
import sqlite3
import streamlit as st


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "esg.db"

COMPANY_SOURCE_TYPES = ["company_report", "company_website", "advertisement"]


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


def render_dashboard(scores):
    search = st.text_input("Search for a company")

    if search:
        filtered = scores[scores["company_name"].str.contains(search, case=False, na=False)]
        if filtered.empty:
            st.info(
                f"'{search}' isn't in this analysis yet. Currently covering: "
                + ", ".join(sorted(scores["company_name"]))
            )
    else:
        filtered = scores

    st.subheader("Leaderboard")
    display_df = filtered[[
        "company_name", "promotion_score", "substantiation_score",
        "performance_score", "risk_score", "risk_label"
    ]].sort_values("risk_score", ascending=False, na_position="last")

    display_df = display_df.fillna("N/A")

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
    company_claims = claims[claims["source_type"].isin(COMPANY_SOURCE_TYPES)]
    external_claims = claims[~claims["source_type"].isin(COMPANY_SOURCE_TYPES)]

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


def render_methodology():
    st.header("Methodology")

    st.subheader("What this tool does")
    st.write(
        "This tool compares what airlines publicly claim about sustainability against "
        "their actual reported emissions performance, producing a 'discrepancy risk' score. "
        "A high score means a company talks about sustainability a lot, backs it up with "
        "few specific commitments, and hasn't reduced emissions — not proof of intentional "
        "deception."
    )

    st.subheader("How the risk score is calculated")
    st.latex(r"""
    \text{Risk} = 0.40 \times \text{Promotion} + 0.30 \times (100 - \text{Substantiation}) + 0.30 \times (100 - \text{Performance})
    """)

    st.markdown("""
    - **Promotion score**: based on the number of company-sourced claims on record (company reports, company websites, advertisements only — third-party and regulatory sources are excluded from this score).
    - **Substantiation score**: the percentage of those company-sourced claims that include a specific number, a baseline year, and a target year.
    - **Performance score**: based on year-over-year change in Scope 1 emissions. A reduction of 2%+ scores 100, roughly flat (within ±2%) scores 50, an increase of more than 2% scores 0.
    - **Insufficient data**: companies with fewer than two years of emissions data on record are not assigned a risk score, rather than guessing.
    """)

    st.subheader("Source classification")
    st.write(
        "Every claim is tagged by where it came from: company_report, company_website, "
        "advertisement, regulatory_action, or news_report. Only the first three count toward "
        "the Promotion and Substantiation scores. Regulatory actions and news coverage are shown "
        "separately as 'external scrutiny' — they provide important context but are not treated "
        "as the company's own promotional claims."
    )

    st.subheader("Data sources")
    st.write(
        "Claims and emissions data were manually researched and compiled from company "
        "sustainability reports, SEC/regulatory filings, and credible news coverage. Each "
        "claim is tagged with a confidence level reflecting how directly it was sourced."
    )

    st.subheader("Known limitations")
    st.markdown("""
    - Covers 5 airlines and one reporting year; not a comprehensive industry survey.
    - Claims were researched and entered manually. Automated extraction from primary-source
      PDFs is planned for a future version.
    - Performance scoring currently uses Scope 1 emissions only, with a simple threshold model.
      It does not yet account for Scope 2/3, revenue-adjusted intensity, or longer-term trends.
    - A company with very few logged claims (e.g. 1) can show an extreme substantiation score
      (0% or 100%) that a larger sample would likely moderate.
    - This is a discrepancy indicator, not a legal or scientific determination of greenwashing.
    """)


def main():
    st.set_page_config(page_title="ESG Greenwashing Detector", layout="wide")

    st.title("ESG Greenwashing Detector")
    st.caption("Comparing airline sustainability claims against real emissions performance")

    scores = load_scores()

    tab1, tab2 = st.tabs(["Dashboard", "Methodology"])

    with tab1:
        render_dashboard(scores)

    with tab2:
        render_methodology()


if __name__ == "__main__":
    main()
