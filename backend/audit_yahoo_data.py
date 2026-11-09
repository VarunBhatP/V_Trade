
from pathlib import Path

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]

DATA_DIR = PROJECT_ROOT / "data" / "raw" / "yahoo_20y"
MANIFEST_FILE = (
    PROJECT_ROOT / "data" / "universe" / "download_manifest.csv"
)

REQUIRED_COLUMNS = [
    "date", "open", "high", "low", "close", "volume"
]


def audit_file(path, manifest_row):
    issues = []
    warnings = []

    try:
        df = pd.read_csv(path)
    except Exception as exc:
        return ["Cannot read CSV: " + str(exc)], warnings

    if list(df.columns) != REQUIRED_COLUMNS:
        return [
            f"Unexpected columns: {list(df.columns)}"
        ], warnings

    df["date"] = pd.to_datetime(df["date"], errors="coerce")

    numeric_columns = ["open", "high", "low", "close", "volume"]

    for column in numeric_columns:
        df[column] = pd.to_numeric(df[column], errors="coerce")

    if df.empty:
        return ["Empty CSV"], warnings

    if df["date"].isna().any():
        issues.append("Invalid dates found")

    if df[numeric_columns].isna().any().any():
        issues.append("Missing or non-numeric OHLCV values")

    values = df[numeric_columns].to_numpy(dtype=float)

    if not np.isfinite(values).all():
        issues.append("Infinite or non-finite OHLCV values")

    if (df[["open", "high", "low", "close"]] <= 0).any().any():
        issues.append("Non-positive prices found")

    if (df["volume"] < 0).any():
        issues.append("Negative volume found")

    if df["date"].duplicated().any():
        issues.append("Duplicate dates found")

    if not df["date"].is_monotonic_increasing:
        issues.append("Dates are not sorted ascending")

    valid_prices = df[["open", "high", "low", "close"]].dropna()

    if not valid_prices.empty:
        maximum = valid_prices[["open", "close"]].max(axis=1)
        minimum = valid_prices[["open", "close"]].min(axis=1)

        if (valid_prices["high"] < maximum - 1e-8).any():
            issues.append("High is below open or close")

        if (valid_prices["low"] > minimum + 1e-8).any():
            issues.append("Low is above open or close")

        if (valid_prices["high"] < valid_prices["low"]).any():
            issues.append("High is below low")

    valid_dates = df["date"].dropna()

    if len(valid_dates) > 1:
        gaps = valid_dates.diff().dt.days.dropna()
        large_gaps = gaps[gaps > 7]

        if not large_gaps.empty:
            warnings.append(
                f"{len(large_gaps)} date gaps exceed 7 calendar days; "
                "investigate against the NSE trading calendar"
            )

    if manifest_row is not None:
        expected_count = int(manifest_row["candles"])

        if len(df) != expected_count:
            issues.append(
                f"Manifest candle count mismatch: "
                f"{len(df)} vs {expected_count}"
            )

        if not valid_dates.empty:
            actual_start = valid_dates.min().date().isoformat()
            actual_end = valid_dates.max().date().isoformat()

            if actual_start != manifest_row["coverage_start"]:
                issues.append("Manifest start-date mismatch")

            if actual_end != manifest_row["coverage_end"]:
                issues.append("Manifest end-date mismatch")

    return issues, warnings


def main():
    manifest = pd.read_csv(
        MANIFEST_FILE,
        dtype=str
    ).fillna("")

    manifest_lookup = {
        (row["exchange"], row["symbol"]): row
        for row in manifest.to_dict("records")
    }

    files = sorted(DATA_DIR.glob("*.csv"))

    print("\n========== HISTORICAL DATA AUDIT ==========")
    print("Files found:", len(files))

    passed = 0
    failed = 0
    warning_count = 0

    for path in files:
        parts = path.stem.split("_", 1)

        if len(parts) != 2:
            print(f"\n{path.name}: INVALID FILENAME")
            failed += 1
            continue

        exchange, symbol = parts
        row = manifest_lookup.get((exchange, symbol))

        issues, warnings = audit_file(path, row)

        print(f"\n{symbol}")

        if row is None:
            issues.append("No matching manifest entry")

        if issues:
            failed += 1
            print("  FAIL")
            for issue in issues:
                print("  -", issue)
        else:
            passed += 1
            print("  PASS")

        for warning in warnings:
            warning_count += 1
            print("  WARNING:", warning)

    print("\n========== AUDIT SUMMARY ==========")
    print("Files audited:", len(files))
    print("Passed:", passed)
    print("Failed:", failed)
    print("Warnings:", warning_count)


if __name__ == "__main__":
    main()
