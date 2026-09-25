from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parent.parent
INPUT_FILE = PROJECT_ROOT / "data" / "raw" / "sample_companies.csv"
OUTPUT_FILE = PROJECT_ROOT / "data" / "processed" / "company_scores.csv"


def load_data():
    return pd.read_csv(INPUT_FILE)


def calculate_risk_score(df):
    df["risk_score"] = (
        0.40 * df["promotion_score"]
        + 0.30 * (100 - df["substantiation_score"])
        + 0.30 * (100 - df["performance_score"])
    ).round(2)
    return df


def assign_risk_label(score):
    if score < 30:
        return "Lower discrepancy"
    elif score < 60:
        return "Moderate discrepancy"
    elif score < 80:
        return "High discrepancy"
    else:
        return "Very high discrepancy"


def main():
    df = load_data()
    df = calculate_risk_score(df)
    df["risk_label"] = df["risk_score"].apply(assign_risk_label)
    df = df.sort_values("risk_score", ascending=False)

    print(df[["company_name", "risk_score", "risk_label"]].to_string(index=False))

    df.to_csv(OUTPUT_FILE, index=False)


if __name__ == "__main__":
    main()