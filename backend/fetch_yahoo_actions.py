
import argparse
import time
from pathlib import Path

import pandas as pd
import yfinance as yf


PROJECT_ROOT = Path(__file__).resolve().parents[1]

UNIVERSE_FILE = PROJECT_ROOT / "data/universe/validated_universe.csv"
OUTPUT_DIR = PROJECT_ROOT / "data/corporate_actions"
EVENTS_FILE = OUTPUT_DIR / "yahoo_action_events.csv"
SUMMARY_FILE = OUTPUT_DIR / "yahoo_action_summary.csv"

START_DATE = "2006-11-09"
END_DATE = "2026-11-10"

yf.config.debug.hide_exceptions = False


def atomic_save(df, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(".tmp")
    df.to_csv(temp, index=False)
    temp.replace(path)


def fetch_actions(row):
    ticker_symbol = row["yahoo_symbol"]

    ticker = yf.Ticker(ticker_symbol)

    history = ticker.history(
        start=START_DATE,
        end=END_DATE,
        interval="1d",
        auto_adjust=False,
        actions=True,
    )

    if history.empty:
        raise ValueError("Yahoo returned no historical data")

    required = {"Dividends", "Stock Splits"}

    if not required.issubset(history.columns):
        raise ValueError("Corporate-action columns missing")

    events = []

    for timestamp, candle in history.iterrows():
        dividend = float(candle["Dividends"])
        split = float(candle["Stock Splits"])

        if dividend == 0 and split == 0:
            continue

        events.append({
            "exchange": row["exchange"],
            "symbol": row["symbol"],
            "company_name": row["company_name"],
            "isin": row["isin"],
            "yahoo_symbol": ticker_symbol,
            "date": timestamp.date().isoformat(),
            "dividend": dividend,
            "stock_split": split,
            "close": float(candle["Close"]),
            "adj_close": float(candle["Adj Close"]),
        })

    return events, len(history)

def load_existing_results():
    if SUMMARY_FILE.exists():
        summary = pd.read_csv(SUMMARY_FILE)
    else:
        summary = pd.DataFrame()

    if EVENTS_FILE.exists():
        events = pd.read_csv(EVENTS_FILE)
    else:
        events = pd.DataFrame()

    return summary, events


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--delay", type=float, default=1.0)
    args = parser.parse_args()

    universe = pd.read_csv(UNIVERSE_FILE)

    if args.all:
        selected = universe
    else:
        if args.limit < 1:
            raise ValueError("--limit must be positive")
        selected = universe.head(args.limit)

    print("Universe size:", len(universe))
    print("Selected instruments:", len(selected))

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    existing_summary, existing_events = load_existing_results()

    completed = set()

    if not existing_summary.empty:
        completed = set(
            existing_summary.loc[
                existing_summary["status"] == "SUCCESS",
                "symbol"
            ]
        )

    summaries = existing_summary.to_dict("records")
    all_events = existing_events.to_dict("records")

    selected = selected[
        ~selected["symbol"].isin(completed)
    ].copy()

    print("Already completed:", len(completed))
    print("Remaining:", len(selected))

    for index, (_, row) in enumerate(selected.iterrows(), start=1):
        symbol = row["symbol"]

        print(f"\n[{index}/{len(selected)}] {symbol}", end=" ")

        try:
            events, candles = fetch_actions(row)

            all_events.extend(events)

            summaries.append({
                "exchange": row["exchange"],
                "symbol": symbol,
                "yahoo_symbol": row["yahoo_symbol"],
                "status": "SUCCESS",
                "historical_candles": candles,
                "dividend_events": sum(
                    event["dividend"] != 0 for event in events
                ),
                "split_events": sum(
                    event["stock_split"] != 0 for event in events
                ),
                "total_action_events": len(events),
                "error": "",
            })

            print(
                f"SUCCESS | candles={candles} "
                f"| actions={len(events)}"
            )

        except Exception as exc:
            summaries.append({
                "exchange": row["exchange"],
                "symbol": symbol,
                "yahoo_symbol": row["yahoo_symbol"],
                "status": "FAILED",
                "historical_candles": 0,
                "dividend_events": 0,
                "split_events": 0,
                "total_action_events": 0,
                "error": str(exc),
            })

            print("FAILED:", exc)

        # Persist after each instrument so the run can be inspected.
        atomic_save(pd.DataFrame(all_events), EVENTS_FILE)
        atomic_save(pd.DataFrame(summaries), SUMMARY_FILE)

        if index < len(selected):
            time.sleep(args.delay)

    summary = pd.DataFrame(summaries)

    print("\n========== CORPORATE ACTION SUMMARY ==========")
    print("Processed:", len(summary))
    print("\nStatuses:")
    print(summary["status"].value_counts().to_string())

    print("\nDividend events:", summary["dividend_events"].sum())
    print("Split events:", summary["split_events"].sum())
    print("Total action events:", summary["total_action_events"].sum())

    print("\nEvents file:", EVENTS_FILE)
    print("Summary file:", SUMMARY_FILE)


if __name__ == "__main__":
    main()
