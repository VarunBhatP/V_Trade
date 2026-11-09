
import time
from pathlib import Path

import pandas as pd
import yfinance as yf


PROJECT_ROOT = Path(__file__).resolve().parents[1]

UNIVERSE_FILE = (
    PROJECT_ROOT / "data" / "universe" / "nse_constituents.csv"
)

OUTPUT_FILE = (
    PROJECT_ROOT / "data" / "universe" / "yahoo_symbol_mapping.csv"
)

yf.config.debug.hide_exceptions = False

df = pd.read_csv(UNIVERSE_FILE)

results = []

print(f"Validating {len(df)} NSE securities...\n")

for index, row in df.iterrows():
    symbol = row["symbol"]
    yahoo_symbol = f"{symbol}.NS"

    result = {
        "exchange": row["exchange"],
        "symbol": symbol,
        "company_name": row["company_name"],
        "isin": row["isin"],
        "yahoo_symbol": yahoo_symbol,
        "status": "ERROR",
        "candles": 0,
        "latest_date": None,
        "error": None,
    }

    try:
        history = yf.Ticker(yahoo_symbol).history(
            period="5d",
            interval="1d",
            auto_adjust=False,
            actions=False,
        )

        if history.empty:
            result["status"] = "EMPTY"
        else:
            result["status"] = "VALID"
            result["candles"] = len(history)
            result["latest_date"] = str(history.index[-1].date())

    except Exception as exc:
        result["error"] = str(exc)

    results.append(result)

    # Save progress after every stock
    pd.DataFrame(results).to_csv(OUTPUT_FILE, index=False)

    print(
        f"[{index + 1}/{len(df)}] "
        f"{symbol:15} {result['status']:6} "
        f"Candles: {result['candles']}"
    )

    # Avoid sending requests too quickly
    time.sleep(1.0)

result_df = pd.DataFrame(results)

print("\n========== VALIDATION SUMMARY ==========")
print(result_df["status"].value_counts().to_string())
print(f"\nTotal: {len(result_df)}")
print(f"Valid: {(result_df['status'] == 'VALID').sum()}")
print(f"Empty: {(result_df['status'] == 'EMPTY').sum()}")
print(f"Errors: {(result_df['status'] == 'ERROR').sum()}")
print(f"\nSaved mapping: {OUTPUT_FILE}")
