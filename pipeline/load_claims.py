from pathlib import Path
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = PROJECT_ROOT / "data" / "raw"

def main():
    companies = pd.read_csv(RAW_DIR / "companies.csv")
    claims = pd.read_csv(RAW_DIR / "claims.csv")
    emissions = pd.read_csv(RAW_DIR / "emissions.csv")
    print("=== Companies ===")
    print(companies)

    print("\n=== Claims per company ===")
    print(claims.groupby("company_id").size())
    print("\n=== Specific vs vague claims ===")
    claims["is_specific"] = (
        (claims["has_number"] == 1)
        & (claims["has_baseline_year"] == 1)
        & (claims["has_target_year"] == 1)
    )
    print(claims[["claim_id", "company_id", "is_specific"]])

    print("\n=== Emissions ===")
    print(emissions)


if __name__ == "__main__":
    main()
