
from pathlib import Path

import pandas as pd
import yfinance as yf

PROJECT_ROOT = Path(__file__).resolve().parents[1]

MANIFEST_FILE = PROJECT_ROOT / "data" / "universe" / "download_manifest.csv"
UNIVERSE_FILE = PROJECT_ROOT / "data" / "universe" / "validated_universe.csv"

START_DATE = "2006-11-09"
END_DATE = "2026-11-10"


def main():
    manifest = pd.read_csv(MANIFEST_FILE)
    universe = pd.read_csv(UNIVERSE_FILE)

    failed = manifest[manifest["status"] == "FAILED"]

    symbol_map = {
        (row["exchange"], row["symbol"]): row["yahoo_symbol"]
        for _, row in universe.iterrows()
    }

    print(f"Failed instruments: {len(failed)}")

    for _, row in failed.iterrows():
        exchange = row["exchange"]
        symbol = row["symbol"]
        yahoo_symbol = symbol_map.get((exchange, symbol))

        print("\n" + "=" * 65)
        print(f"{symbol} | Yahoo: {yahoo_symbol}")

        if not yahoo_symbol:
            print("MISSING YAHOO SYMBOL MAPPING")
            continue

        try:
            history = yf.Ticker(yahoo_symbol).history(
                start=START_DATE,
                end=END_DATE,
                interval="1d",
                auto_adjust=False,
                actions=True,
            )

            if history.empty:
                print("NO HISTORICAL DATA")
                continue

            required = ["Open", "High", "Low", "Close"]
            missing = set(required) - set(history.columns)

            if missing:
                print(f"Missing columns: {missing}")
                continue

            prices = history[required].apply(
                pd.to_numeric, errors="coerce"
            )

            invalid_high = prices["High"] < prices[
                ["Open", "Close"]
            ].max(axis=1) - 1e-8

            invalid_low = prices["Low"] > prices[
                ["Open", "Close"]
            ].min(axis=1) + 1e-8

            invalid_range = prices["High"] < prices["Low"]

            bad = invalid_high | invalid_low | invalid_range

            print(f"Total candles: {len(history)}")
            print(f"Invalid candles: {bad.sum()}")

            if not bad.any():
                print("No OHLC inconsistencies found on fresh fetch.")
                continue

            columns = [
                "Open", "High", "Low", "Close",
                "Adj Close", "Volume",
                "Dividends", "Stock Splits",
            ]

            available = [
                col for col in columns if col in history.columns
            ]

            bad_positions = [
                i for i, is_bad in enumerate(bad) if is_bad
            ]

            for position in bad_positions[:10]:
                start = max(0, position - 1)
                end = min(len(history), position + 2)

                print("\nProblem date and surrounding candles:")
                print(history.iloc[start:end][available].to_string())

            if len(bad_positions) > 10:
                print(f"\n... {len(bad_positions) - 10} more invalid candles")

        except Exception as exc:
            print(f"FETCH ERROR: {type(exc).__name__}: {exc}")


if __name__ == "__main__":
    main()
