import sqlite3
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "esg.db"


def calculate_promotion_score(conn):
    query = """
        SELECT company_id, COUNT(*) AS claim_count
        FROM claims
        GROUP BY company_id
    """
    df = pd.read_sql_query(query, conn)
    df["promotion_score"] = (df["claim_count"] * 10).clip(upper=100)
    return df[["company_id", "promotion_score"]]


def calculate_substantiation_score(conn):
    query = """
        SELECT company_id,
               SUM(CASE WHEN has_number=1 AND has_baseline_year=1 AND has_target_year=1 THEN 1 ELSE 0 END) AS specific_count,
               COUNT(*) AS total_count
        FROM claims
        GROUP BY company_id
    """
    df = pd.read_sql_query(query, conn)
    df["substantiation_score"] = (df["specific_count"] / df["total_count"] * 100).round(1)
    return df[["company_id", "substantiation_score"]]


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
            results.append({"company_id": company_id, "performance_score": None})
            continue
        latest = group.iloc[-1]["scope_1_kg"]
        previous = group.iloc[-2]["scope_1_kg"]
        score = 100 if latest < previous else 0
        results.append({"company_id": company_id, "performance_score": score})

    return pd.DataFrame(results)


def calculate_risk_score(row):
    if pd.isna(row["performance_score"]):
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

    scores = companies.merge(promotion, on="company_id", how="left")
    scores = scores.merge(substantiation, on="company_id", how="left")
    scores = scores.merge(performance, on="company_id", how="left")

    scores["risk_score"] = scores.apply(calculate_risk_score, axis=1)
    scores["risk_label"] = scores["risk_score"].apply(assign_risk_label)

    scores = scores.sort_values("risk_score", ascending=False, na_position="last")

    print(scores[["company_name", "promotion_score", "substantiation_score", "performance_score", "risk_score", "risk_label"]].to_string(index=False))

    scores.to_sql("scores", conn, if_exists="replace", index=False)
    conn.commit()
    conn.close()


if __name__ == "__main__":
    main()