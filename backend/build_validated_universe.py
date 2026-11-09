
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
UNIVERSE_DIR = PROJECT_ROOT / "data" / "universe"

SOURCE_FILE = UNIVERSE_DIR / "nse_constituents.csv"
MAPPING_FILE = UNIVERSE_DIR / "yahoo_symbol_mapping.csv"

OUTPUT_FILE = UNIVERSE_DIR / "validated_universe.csv"
EXCLUDED_FILE = UNIVERSE_DIR / "excluded_universe.csv"

KEY_COLUMNS = ["exchange", "symbol", "isin"]


def normalize(df):
    for column in KEY_COLUMNS:
        df[column] = df[column].astype(str).str.strip().str.upper()
    return df


def main():
    source = pd.read_csv(SOURCE_FILE, dtype=str).fillna("")
    mapping = pd.read_csv(MAPPING_FILE, dtype=str).fillna("")

    required_source = {
        "exchange", "symbol", "company_name", "isin", "indices"
    }
    required_mapping = {
        "exchange", "symbol", "company_name", "isin",
        "yahoo_symbol", "status", "error"
    }

    if not required_source.issubset(source.columns):
        raise ValueError("Source CSV is missing required columns.")

    if not required_mapping.issubset(mapping.columns):
        raise ValueError("Yahoo mapping CSV is missing required columns.")

    source = normalize(source)
    mapping = normalize(mapping)

    mapping["status"] = mapping["status"].str.strip().str.upper()

    if source.duplicated(KEY_COLUMNS).any():
        raise ValueError("Duplicate instruments found in source CSV.")

    if mapping.duplicated(KEY_COLUMNS).any():
        raise ValueError("Duplicate instruments found in mapping CSV.")

    # Confirm every source instrument has exactly one mapping record.
    merged = mapping.merge(
        source,
        on=KEY_COLUMNS,
        how="outer",
        suffixes=("_mapping", "_source"),
        indicator=True,
        validate="one_to_one",
    )

    unmatched = merged[merged["_merge"] != "both"]

    if not unmatched.empty:
        raise ValueError(
            f"Source/mapping mismatch: {len(unmatched)} unmatched records."
        )

    # Verify company names have not changed between the files.
    name_mismatch = (
        merged["company_name_mapping"].str.strip().str.upper()
        != merged["company_name_source"].str.strip().str.upper()
    )

    if name_mismatch.any():
        raise ValueError("Company-name mismatch between source and mapping.")

    if not set(mapping["status"]).issubset({"VALID", "ERROR"}):
        raise ValueError("Unexpected status found in mapping CSV.")

    valid = merged[merged["status"] == "VALID"].copy()
    excluded = merged[merged["status"] != "VALID"].copy()

    if len(valid) != 499 or len(excluded) != 2:
        raise ValueError(
            f"Unexpected counts: VALID={len(valid)}, "
            f"EXCLUDED={len(excluded)}. Expected 499 and 2."
        )

    expected_exclusions = {"BAGMANE", "DUMMYHEG"}

    if set(excluded["symbol"]) != expected_exclusions:
        raise ValueError("Unexpected excluded instruments.")

    # Build the validated universe.
    validated = pd.DataFrame({
        "exchange": valid["exchange"],
        "symbol": valid["symbol"],
        "company_name": valid["company_name_source"],
        "isin": valid["isin"],
        "yahoo_symbol": valid["yahoo_symbol"],
        "indices": valid["indices"],
    })

    # Keep an audit trail for excluded instruments.
    excluded["exclusion_reason"] = excluded["symbol"].map({
        "BAGMANE": (
            "Yahoo returned no data; genuine security, "
            "excluded from Yahoo-backed universe."
        ),
        "DUMMYHEG": (
            "Placeholder-like, unverified constituent record; "
            "excluded pending verification."
        ),
    })

    excluded_output = excluded[[
        "exchange",
        "symbol",
        "company_name_source",
        "isin",
        "yahoo_symbol",
        "status",
        "error",
        "exclusion_reason",
    ]].rename(columns={"company_name_source": "company_name"})

    validated.to_csv(OUTPUT_FILE, index=False)
    excluded_output.to_csv(EXCLUDED_FILE, index=False)

    print("\n========== VALIDATED UNIVERSE ==========")
    print(f"Source instruments: {len(source)}")
    print(f"Yahoo mappings:     {len(mapping)}")
    print(f"Validated:          {len(validated)}")
    print(f"Excluded:           {len(excluded_output)}")

    print(f"\nSaved: {OUTPUT_FILE}")
    print(f"Saved: {EXCLUDED_FILE}")

    print("\nExcluded instruments:")
    print(excluded_output[
        ["symbol", "company_name", "exclusion_reason"]
    ].to_string(index=False))


if __name__ == "__main__":
    main()
