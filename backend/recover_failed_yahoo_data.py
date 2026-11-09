
import time
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf


PROJECT_ROOT = Path(__file__).resolve().parents[1]

MANIFEST_FILE = PROJECT_ROOT / "data/universe/download_manifest.csv"
RAW_RECOVERY_DIR = PROJECT_ROOT / "data/raw/yahoo_recovery"
REPORT_FILE = PROJECT_ROOT / "data/universe/yahoo_recovery_report.csv"
ANOMALY_FILE = PROJECT_ROOT / "data/universe/yahoo_recovery_anomalies.csv"

START_DATE = "2006-11-09"
END_DATE = "2026-11-10"  # Exclusive; includes Nov 9.

PRECISION_TOLERANCE = 0.0001
REVIEW_TOLERANCE = 0.01

yf.config.debug.hide_exceptions = False


def fetch_yahoo_history(yahoo_symbol):
    ticker = yf.Ticker(yahoo_symbol)

    return ticker.history(
        start=START_DATE,
        end=END_DATE,
        interval="1d",
        auto_adjust=False,
        actions=True,
    )


def diagnose_candles(df, symbol):
    required = ["Open", "High", "Low", "Close", "Volume"]

    missing = set(required) - set(df.columns)
    if missing:
        raise ValueError(f"Missing columns: {sorted(missing)}")

    data = df.copy().reset_index()

    date_column = "Date" if "Date" in data.columns else "Datetime"
    if date_column not in data.columns:
        raise ValueError("Yahoo response has no date column.")

    data = data.rename(columns={
        date_column: "date",
        "Open": "open",
        "High": "high",
        "Low": "low",
        "Close": "close",
        "Volume": "volume",
    })

    reasons = [[] for _ in range(len(data))]
    statuses = ["PASS"] * len(data)

    def flag(mask, reason, severity):
        for pos in np.flatnonzero(mask):
            reasons[pos].append(reason)

            if severity == "QUARANTINE":
                statuses[pos] = "QUARANTINE"
            elif statuses[pos] != "QUARANTINE":
                statuses[pos] = "WARNING"

    numeric_columns = ["open", "high", "low", "close", "volume"]

    for column in numeric_columns:
        data[column] = pd.to_numeric(data[column], errors="coerce")

    values = data[numeric_columns].to_numpy(dtype=float)
    finite = np.isfinite(values).all(axis=1)

    flag(
        ~finite,
        "MISSING_OR_NONFINITE_VALUE",
        "QUARANTINE",
    )

    prices = data[["open", "high", "low", "close"]].to_numpy(
        dtype=float
    )

    valid_prices = np.isfinite(prices).all(axis=1)

    flag(
        valid_prices & (prices <= 0).any(axis=1),
        "NONPOSITIVE_PRICE",
        "QUARANTINE",
    )

    volume = data["volume"].to_numpy(dtype=float)

    flag(
        ~np.isfinite(volume) | (volume < 0),
        "INVALID_VOLUME",
        "QUARANTINE",
    )

    open_price = data["open"].to_numpy(dtype=float)
    high = data["high"].to_numpy(dtype=float)
    low = data["low"].to_numpy(dtype=float)
    close = data["close"].to_numpy(dtype=float)

    violation = np.maximum.reduce([
        np.maximum(0, np.maximum(open_price, close) - high),
        np.maximum(0, low - np.minimum(open_price, close)),
        np.maximum(0, low - high),
    ])

    flag(
        valid_prices & (violation > REVIEW_TOLERANCE),
        "MATERIAL_OHLC_INCONSISTENCY",
        "QUARANTINE",
    )

    flag(
        valid_prices
        & (violation > PRECISION_TOLERANCE)
        & (violation <= REVIEW_TOLERANCE),
        "SMALL_OHLC_INCONSISTENCY",
        "WARNING",
    )

    dates = pd.to_datetime(data["date"], errors="coerce")

    flag(
        dates.isna().to_numpy(),
        "INVALID_DATE",
        "QUARANTINE",
    )

    duplicate_dates = dates.notna() & dates.duplicated(keep=False)

    flag(
        duplicate_dates.to_numpy(),
        "DUPLICATE_DATE",
        "QUARANTINE",
    )

    data["date"] = dates.astype(str)
    data["symbol"] = symbol
    data["quality_status"] = statuses
    data["quality_reason"] = [
        "; ".join(items) for items in reasons
    ]

    anomalies = data[data["quality_status"] != "PASS"].copy()

    summary = {
        "candles": len(data),
        "pass": statuses.count("PASS"),
        "warning": statuses.count("WARNING"),
        "quarantine": statuses.count("QUARANTINE"),
    }

    return data, anomalies, summary


def main():
    manifest = pd.read_csv(MANIFEST_FILE)

    failed = manifest[
        manifest["status"].astype(str).str.upper() == "FAILED"
    ].copy()

    if failed.empty:
        print("No failed instruments found.")
        return

    RAW_RECOVERY_DIR.mkdir(parents=True, exist_ok=True)

    report_rows = []
    anomaly_frames = []

    print(f"Failed instruments to recover: {len(failed)}")

    for _, instrument in failed.iterrows():
        exchange = instrument["exchange"]
        symbol = instrument["symbol"]
        yahoo_symbol = instrument["yahoo_symbol"]

        print(f"\nFetching {exchange}:{symbol} ({yahoo_symbol})")

        try:
            history = fetch_yahoo_history(yahoo_symbol)

            if history.empty:
                raise ValueError("Yahoo returned empty history.")

            # Preserve the complete Yahoo response.
            raw_path = RAW_RECOVERY_DIR / f"{exchange}_{symbol}.csv"

            raw = history.copy()
            raw.index.name = "date"
            raw.to_csv(raw_path)

            data, anomalies, summary = diagnose_candles(
                history, symbol
            )

            if not anomalies.empty:
                anomaly_frames.append(anomalies)

            report_rows.append({
                "exchange": exchange,
                "symbol": symbol,
                "yahoo_symbol": yahoo_symbol,
                "status": "FETCHED",
                "raw_file": str(raw_path),
                **summary,
                "error": "",
            })

            print(
                f"  Candles: {summary['candles']} | "
                f"PASS: {summary['pass']} | "
                f"WARNING: {summary['warning']} | "
                f"QUARANTINE: {summary['quarantine']}"
            )

        except Exception as exc:
            report_rows.append({
                "exchange": exchange,
                "symbol": symbol,
                "yahoo_symbol": yahoo_symbol,
                "status": "FETCH_FAILED",
                "raw_file": "",
                "candles": 0,
                "pass": 0,
                "warning": 0,
                "quarantine": 0,
                "error": str(exc),
            })

            print(f"  FETCH FAILED: {exc}")

        time.sleep(1)

    report = pd.DataFrame(report_rows)

    anomalies = (
        pd.concat(anomaly_frames, ignore_index=True)
        if anomaly_frames
        else pd.DataFrame()
    )

    report.to_csv(REPORT_FILE, index=False)
    anomalies.to_csv(ANOMALY_FILE, index=False)

    print("\n========== RECOVERY SUMMARY ==========")
    print(report["status"].value_counts().to_string())

    print("\nCandle totals:")
    for column in ["candles", "pass", "warning", "quarantine"]:
        print(f"{column}: {report[column].sum()}")

    print(f"\nReport: {REPORT_FILE}")
    print(f"Anomalies: {ANOMALY_FILE}")
    print(f"Raw responses: {RAW_RECOVERY_DIR}")


if __name__ == "__main__":
    main()
