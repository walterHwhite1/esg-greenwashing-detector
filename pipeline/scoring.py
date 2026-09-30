import sqlite3
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "esg.db"

COMPANY_SOURCE_TYPES = ("company_report", "company_website", "advertisement")


def calculate_promotion_score(conn):
    placeholders = ",".join("?" * len(COMPANY_SOURCE_TYPES))
    query = f"""
        SELECT company_id, COUNT(*) AS company_claim_count
        FROM claims
        WHERE source_type IN ({placeholders})
        GROUP BY company_id
    """
    df = pd.read_sql_query(query, conn, params=COMPANY_SOURCE_TYPES)
    df["promotion_score"] = (df["company_claim_count"] * 20).clip(upper=100)
    return df[["company_id", "promotion_score"]]


def calculate_substantiation_score(conn):
    placeholders = ",".join("?" * len(COMPANY_SOURCE_TYPES))
    query = f"""
        SELECT company_id,
               SUM(CASE WHEN source_type IN ({placeholders}) AND has_number=1 AND has_baseline_year=1 AND has_target_year=1 THEN 1 ELSE 0 END) AS specific_count,
               SUM(CASE WHEN source_type IN ({placeholders}) THEN 1 ELSE 0 END) AS total_company_claims
        FROM claims
        GROUP BY company_id
    """
    params = COMPANY_SOURCE_TYPES * 2
    df = pd.read_sql_query(query, conn, params=params)
    df = df[df["total_company_claims"] > 0]
    df["substantiation_score"] = (
        df["specific_count"] / df["total_company_claims"] * 100
    ).round(1)
    return df[["company_id", "substantiation_score"]]


def calculate_external_scrutiny(conn):
    query = """
        SELECT company_id, COUNT(*) AS external_scrutiny_count
        FROM claims
        WHERE source_type IN ('regulatory_action', 'news_report')
        GROUP BY company_id
    """
    return pd.read_sql_query(query, conn)


def calculate_performance_score(conn):
    query = """
        SELECT company_id, year, scope_1_kg
        FROM emissions
        ORDER BY company_id, year
    """
    df = pd.read_sql_query(query, conn)

    results = []
    for company_id, group in df.groupby("company_id"):
        group = group.dropna(subset=["scope_1_kg"])
        if len(group) < 2:
            results.append({"company_id": company_id, "performance_score": None, "scope_1_pct_change": None})
            continue
        latest = group.iloc[-1]["scope_1_kg"]
        previous = group.iloc[-2]["scope_1_kg"]
        pct_change = round((latest - previous) / previous * 100, 2)

        if pct_change <= -2:
            score = 100
        elif pct_change <= 2:
            score = 50
        else:
            score = 0

        results.append({"company_id": company_id, "performance_score": score, "scope_1_pct_change": pct_change})

    return pd.DataFrame(results)


def calculate_risk_score(row):
    if pd.isna(row["performance_score"]) or pd.isna(row["substantiation_score"]):
        return None
    return round(
        0.40 * row["promotion_score"]
        + 0.30 * (100 - row["substantiation_score"])
        + 0.30 * (100 - row["performance_score"]),
        2,
    )


def assign_risk_label(score):
    if pd.isna(score):
        return "Insufficient data"
    elif score < 30:
        return "Lower discrepancy"
    elif score < 60:
        return "Moderate discrepancy"
    elif score < 80:
        return "High discrepancy"
    else:
        return "Very high discrepancy"


def main():
    conn = sqlite3.connect(DB_PATH)

    companies = pd.read_sql_query("SELECT company_id, company_name FROM companies", conn)
    promotion = calculate_promotion_score(conn)
    substantiation = calculate_substantiation_score(conn)
    performance = calculate_performance_score(conn)
    external = calculate_external_scrutiny(conn)

    scores = companies.merge(promotion, on="company_id", how="left")
    scores = scores.merge(substantiation, on="company_id", how="left")
    scores = scores.merge(performance, on="company_id", how="left")
    scores = scores.merge(external, on="company_id", how="left")

    scores["promotion_score"] = scores["promotion_score"].fillna(0)
    scores["substantiation_score"] = scores["substantiation_score"].fillna(0)
    scores["external_scrutiny_count"] = scores["external_scrutiny_count"].fillna(0).astype(int)

    scores["risk_score"] = scores.apply(calculate_risk_score, axis=1)
    scores["risk_label"] = scores["risk_score"].apply(assign_risk_label)

    scores = scores.sort_values("risk_score", ascending=False, na_position="last")

    print(scores[[
        "company_name", "promotion_score", "substantiation_score",
        "performance_score", "scope_1_pct_change", "external_scrutiny_count",
        "risk_score", "risk_label"
    ]].to_string(index=False))

    scores.to_sql("scores", conn, if_exists="replace", index=False)
    conn.commit()
    conn.close()


if __name__ == "__main__":
    main()