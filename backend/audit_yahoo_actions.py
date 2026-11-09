
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DIR = ROOT / "data/corporate_actions"

events = pd.read_csv(DIR / "yahoo_action_events.csv")
summary = pd.read_csv(DIR / "yahoo_action_summary.csv")

print("\n========== CORPORATE ACTION AUDIT ==========")

print("Summary instruments:", len(summary))
print("Successful:", (summary["status"] == "SUCCESS").sum())
print("Failed:", (summary["status"] != "SUCCESS").sum())

dividend = events["dividend"].fillna(0) != 0
split = events["stock_split"].fillna(0) != 0

print("\nEvent rows:", len(events))
print("Dividend events:", int(dividend.sum()))
print("Split events:", int(split.sum()))
print("Both on same date:", int((dividend & split).sum()))
print("Rows without an action:", int((~dividend & ~split).sum()))

duplicates = events.duplicated(
    subset=["exchange", "symbol", "date"],
    keep=False
)

print("\nDuplicate instrument/date rows:", int(duplicates.sum()))

if duplicates.any():
    print(events.loc[duplicates].to_string(index=False))

# Compare event-level counts with the instrument summary.
actual = events.assign(
    dividend_count=dividend.astype(int),
    split_count=split.astype(int),
).groupby("symbol").agg(
    actual_dividends=("dividend_count", "sum"),
    actual_splits=("split_count", "sum"),
    actual_events=("date", "count"),
).reset_index()

comparison = summary.merge(
    actual,
    on="symbol",
    how="left",
)

for column in ["actual_dividends", "actual_splits", "actual_events"]:
    comparison[column] = comparison[column].fillna(0).astype(int)

mismatches = comparison[
    (comparison["dividend_events"] != comparison["actual_dividends"])
    | (comparison["split_events"] != comparison["actual_splits"])
    | (comparison["total_action_events"] != comparison["actual_events"])
]

print("\nSummary mismatches:", len(mismatches))

if not mismatches.empty:
    print(mismatches.to_string(index=False))

print("\nAction types:")
print("Unique dividend values:", events.loc[dividend, "dividend"].nunique())
print("Unique split factors:", sorted(events.loc[split, "stock_split"].unique()))

print("\n========== AUDIT COMPLETE ==========")
