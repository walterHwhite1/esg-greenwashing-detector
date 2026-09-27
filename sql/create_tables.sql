CREATE TABLE companies (
    company_id INTEGER PRIMARY KEY,
    company_name TEXT NOT NULL,
    ticker TEXT,
    sector TEXT,
    report_year INTEGER
);

CREATE TABLE claims (
    claim_id INTEGER PRIMARY KEY,
    company_id INTEGER,
    claim_text TEXT,
    claim_type TEXT,
    has_number INTEGER,
    has_baseline_year INTEGER,
    has_target_year INTEGER,
    source TEXT,
    FOREIGN KEY (company_id) REFERENCES companies(company_id)
);

CREATE TABLE emissions (
    emission_id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id INTEGER,
    year INTEGER,
    scope_1_kg REAL,
    scope_2_kg REAL,
    scope_3_kg REAL,
    unit TEXT,
    externally_assured INTEGER,
    FOREIGN KEY (company_id) REFERENCES companies(company_id)
);