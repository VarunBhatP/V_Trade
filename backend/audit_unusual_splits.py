
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
FILE = ROOT / "data/corporate_actions/yahoo_action_events.csv"

df = pd.read_csv(FILE)
splits = df[df["stock_split"].fillna(0) != 0].copy()

print("Total split events:", len(splits))
print("\nSplit factor frequency:")
print(splits["stock_split"].value_counts().sort_index().to_string())

print("\nUnusual factors (below 0.5 or above 2):")
unusual = splits[
    (splits["stock_split"] < 0.5)
    | (splits["stock_split"] > 2)
]

print(
    unusual[
        ["symbol", "date", "stock_split", "close", "adj_close"]
    ].sort_values(["symbol", "date"]).to_string(index=False)
)

print("\nPotentially non-standard fractional factors:")
fractional = splits[
    (splits["stock_split"] % 1).abs() > 0.000001
]

print(
    fractional[
        ["symbol", "date", "stock_split", "close", "adj_close"]
    ].sort_values(["symbol", "date"]).to_string(index=False)
)
