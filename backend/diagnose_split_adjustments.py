
from pathlib import Path

import pandas as pd
import yfinance as yf

ROOT = Path(__file__).resolve().parents[1]

EVENTS_FILE = ROOT / "data/corporate_actions/yahoo_action_events.csv"
UNIVERSE_FILE = ROOT / "data/universe/validated_universe.csv"

events = pd.read_csv(EVENTS_FILE)
universe = pd.read_csv(UNIVERSE_FILE)

# Keep only actual split events.
splits = events[events["stock_split"].fillna(0) != 0].copy()

# Map internal NSE symbols to Yahoo symbols.
symbol_map = universe.set_index("symbol")["yahoo_symbol"].to_dict()

# Pick one example for each distinct split factor.
samples = (
    splits.sort_values(["stock_split", "symbol"])
    .drop_duplicates(subset=["stock_split"])
    .head(12)
)

print("\n========== SPLIT ADJUSTMENT DIAGNOSTIC ==========")

for _, event in samples.iterrows():
    symbol = event["symbol"]
    yahoo_symbol = symbol_map.get(symbol)
    split_date = pd.Timestamp(event["date"]).date()
    factor = event["stock_split"]

    if not yahoo_symbol:
        print(f"\n{symbol}: Yahoo mapping missing")
        continue

    start = (pd.Timestamp(split_date) - pd.Timedelta(days=10)).date()
    end = (pd.Timestamp(split_date) + pd.Timedelta(days=11)).date()

    try:
        history = yf.Ticker(yahoo_symbol).history(
            start=start.isoformat(),
            end=end.isoformat(),
            interval="1d",
            auto_adjust=False,
            actions=True,
        )

        if history.empty:
            print(f"\n{symbol}: No history returned")
            continue

        history.index = pd.to_datetime(history.index).date

        print(f"\n{symbol} ({yahoo_symbol})")
        print(f"Split date: {split_date} | Reported factor: {factor}")

        columns = ["Open", "High", "Low", "Close", "Adj Close", "Stock Splits"]
        available = [c for c in columns if c in history.columns]

        print(history[available].to_string())

        before = history.loc[history.index < split_date, "Close"]
        after = history.loc[history.index >= split_date, "Close"]

        if not before.empty and not after.empty:
            previous_close = before.iloc[-1]
            next_close = after.iloc[0]

            print(f"Previous close: {previous_close:.4f}")
            print(f"Split-date/next available close: {next_close:.4f}")
            print(f"Close ratio: {next_close / previous_close:.4f}")

    except Exception as exc:
        print(f"\n{symbol}: ERROR - {exc}")

print("\n========== DIAGNOSTIC COMPLETE ==========")
