
from pathlib import Path
import pandas as pd
import numpy as np

DATA_DIR = Path(__file__).resolve().parents[1] / "data/processed/yahoo_20y"

REQUIRED = ["date", "open", "high", "low", "close", "volume"]

files = sorted(DATA_DIR.glob("*.csv"))

total_rows = 0
failed = []
warnings = []

for path in files:
    try:
        df = pd.read_csv(path)
        issues = []

        missing = set(REQUIRED) - set(df.columns)
        if missing:
            issues.append(f"Missing columns: {missing}")
            failed.append((path.name, issues))
            continue

        if df.empty:
            issues.append("Empty file")

        dates = pd.to_datetime(df["date"], errors="coerce")

        if dates.isna().any():
            issues.append("Invalid dates")

        if dates.duplicated().any():
            issues.append("Duplicate dates")

        if not dates.is_monotonic_increasing:
            issues.append("Dates not sorted")

        numeric = df[REQUIRED[1:]].apply(
            pd.to_numeric, errors="coerce"
        )

        if numeric.isna().any().any():
            issues.append("Missing/non-numeric OHLCV")

        values = numeric.to_numpy(dtype=float)

        if not np.isfinite(values).all():
            issues.append("Non-finite OHLCV")

        if (numeric[["open", "high", "low", "close"]] <= 0).any().any():
            issues.append("Non-positive prices")

        if (numeric["volume"] < 0).any():
            issues.append("Negative volume")

        violation = np.maximum.reduce([
            (numeric["open"].clip(lower=numeric["close"]) - numeric["high"]).to_numpy(),
            (numeric["low"] - numeric["open"].clip(upper=numeric["close"])).to_numpy(),
            (numeric["low"] - numeric["high"]).to_numpy(),
            np.zeros(len(df)),
        ])

        # Small discrepancies are reported, not silently corrected.
        material = violation > 0.01

        if material.any():
            issues.append(
                f"{int(material.sum())} material OHLC inconsistencies"
            )

        if (violation > 0.0001).any() and not material.any():
            warnings.append(
                (path.name, int((violation > 0.0001).sum()))
            )

        if issues:
            failed.append((path.name, issues))

        total_rows += len(df)

    except Exception as exc:
        failed.append((path.name, [str(exc)]))


print("\n========== FINAL DATASET AUDIT ==========")
print("Files found:", len(files))
print("Total candles:", total_rows)
print("Failed files:", len(failed))
print("Files with small OHLC discrepancies:", len(warnings))

if failed:
    print("\nFAILURES:")
    for filename, issues in failed:
        print(filename, "->", "; ".join(issues))

if warnings:
    print("\nSMALL DISCREPANCIES:")
    for filename, count in warnings:
        print(filename, "->", count)

if not failed:
    print("\nALL FILES PASSED STRUCTURAL AUDIT")
