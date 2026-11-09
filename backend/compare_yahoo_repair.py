
from pathlib import Path

import pandas as pd
import yfinance as yf

ROOT = Path(__file__).resolve().parents[1]

EVENTS_FILE = ROOT / "data/corporate_actions/yahoo_action_events.csv"
UNIVERSE_FILE = ROOT / "data/universe/validated_universe.csv"

events = pd.read_csv(EVENTS_FILE)
universe = pd.read_csv(UNIVERSE_FILE)

symbol_map = universe.set_index("symbol")["yahoo_symbol"].to_dict()

# A deliberately small pilot, covering different split ratios.
selected = [
    ("ABB", "2007-06-28"),
    ("BEL", "2017-09-28"),
    ("ASTRAL", "2019-09-16"),
    ("RELIANCE", "2024-10-28"),
    ("PATANJALI", "2019-11-14"),
    ("GODREJIND", "2015-01-05"),
]

print("\n========== YAHOO REPAIR COMPARISON ==========")

for symbol, split_date in selected:
    yahoo_symbol = symbol_map.get(symbol)

    if not yahoo_symbol:
        print(f"\n{symbol}: Yahoo symbol missing")
        continue

    start = (
        pd.Timestamp(split_date) - pd.Timedelta(days=15)
    ).date()

    end = (
        pd.Timestamp(split_date) + pd.Timedelta(days=16)
    ).date()

    ticker = yf.Ticker(yahoo_symbol)

    try:
        original = ticker.history(
            start=start.isoformat(),
            end=end.isoformat(),
            interval="1d",
            auto_adjust=False,
            actions=True,
            repair=False,
        )

        repaired = ticker.history(
            start=start.isoformat(),
            end=end.isoformat(),
            interval="1d",
            auto_adjust=False,
            actions=True,
            repair=True,
        )

        if original.empty or repaired.empty:
            print(f"\n{symbol}: Empty history")
            continue

        original.index = pd.to_datetime(original.index).date
        repaired.index = pd.to_datetime(repaired.index).date

        common = original.index.intersection(repaired.index)

        columns = ["Open", "High", "Low", "Close", "Adj Close"]

        comparison = pd.DataFrame(index=common)

        for column in columns:
            if column not in original or column not in repaired:
                continue

            comparison[f"{column}_original"] = original.loc[
                common, column
            ]

            comparison[f"{column}_repaired"] = repaired.loc[
                common, column
            ]

            comparison[f"{column}_difference"] = (
                comparison[f"{column}_repaired"]
                - comparison[f"{column}_original"]
            )

        print(f"\n{symbol} ({yahoo_symbol})")
        print(f"Split date: {split_date}")

        differences = [
            column for column in comparison.columns
            if column.endswith("_difference")
        ]

        changed = comparison[
            (comparison[differences].abs() > 0.0001).any(axis=1)
        ]

        print("Rows compared:", len(comparison))
        print("Rows changed by repair:", len(changed))

        if not changed.empty:
            print(changed.to_string())

    except Exception as exc:
        print(f"\n{symbol}: ERROR - {exc}")

print("\n========== COMPARISON COMPLETE ==========")
