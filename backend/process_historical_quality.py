
import argparse
from pathlib import Path

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]

UNIVERSE_FILE = PROJECT_ROOT / "data" / "universe" / "validated_universe.csv"
MANIFEST_FILE = PROJECT_ROOT / "data" / "universe" / "download_manifest.csv"

RAW_DIR = PROJECT_ROOT / "data" / "raw" / "yahoo_20y"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed" / "yahoo_20y"

REPORT_FILE = PROJECT_ROOT / "data" / "universe" / "data_quality_report.csv"
QUARANTINE_FILE = PROJECT_ROOT / "data" / "processed" / "quarantined_candles.csv"
WARNING_FILE = PROJECT_ROOT / "data" / "processed" / "warning_candles.csv"

REQUIRED_COLUMNS = [
    "date", "open", "high", "low", "close", "volume"
]

PRECISION_TOLERANCE = 0.0001
REVIEW_TOLERANCE = 0.01


def atomic_save_csv(df, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(path.suffix + ".tmp")
    df.to_csv(temp_path, index=False)
    temp_path.replace(path)


def load_inputs():
    universe = pd.read_csv(UNIVERSE_FILE)
    manifest = pd.read_csv(MANIFEST_FILE)

    required_universe = {"exchange", "symbol"}
    required_manifest = {
        "exchange", "symbol", "status", "candles",
        "coverage_start", "coverage_end", "error"
    }

    if not required_universe.issubset(universe.columns):
        raise ValueError("Validated universe has missing columns.")

    if not required_manifest.issubset(manifest.columns):
        raise ValueError("Download manifest has missing columns.")

    for df in (universe, manifest):
        df["exchange"] = df["exchange"].astype(str).str.upper().str.strip()
        df["symbol"] = df["symbol"].astype(str).str.upper().str.strip()

    if universe.duplicated(["exchange", "symbol"]).any():
        raise ValueError("Duplicate instruments in validated universe.")

    if manifest.duplicated(["exchange", "symbol"]).any():
        raise ValueError("Duplicate instruments in download manifest.")

    return universe, manifest


def classify_file(exchange, symbol):
    path = RAW_DIR / f"{exchange}_{symbol}.csv"

    if not path.is_file():
        return None, "MISSING_FILE"

    try:
        df = pd.read_csv(path)
    except Exception as exc:
        return None, f"READ_ERROR: {exc}"

    missing = set(REQUIRED_COLUMNS) - set(df.columns)

    if missing:
        return None, f"MISSING_COLUMNS: {sorted(missing)}"

    return df[REQUIRED_COLUMNS].copy(), "READ_SUCCESS"


def process_candles(df, exchange, symbol):
    df = df.copy()
    df["_row_number"] = np.arange(2, len(df) + 2)

    reasons = [[] for _ in range(len(df))]
    status = ["PASS"] * len(df)

    def flag(mask, reason, severity):
        for position in np.flatnonzero(mask):
            reasons[position].append(reason)

            if severity == "QUARANTINE":
                status[position] = "QUARANTINE"
            elif status[position] != "QUARANTINE":
                status[position] = "WARNING"

    # Parse dates.
    dates = pd.to_datetime(df["date"], errors="coerce")
    flag(dates.isna().to_numpy(), "INVALID_DATE", "QUARANTINE")

    # Parse numeric columns.
    for column in REQUIRED_COLUMNS[1:]:
        df[column] = pd.to_numeric(df[column], errors="coerce")

    numeric = df[REQUIRED_COLUMNS[1:]].to_numpy(dtype=float)
    finite = np.isfinite(numeric).all(axis=1)

    flag(~finite, "MISSING_OR_NONFINITE_NUMERIC_VALUE", "QUARANTINE")

    prices = df[["open", "high", "low", "close"]].to_numpy(dtype=float)

    positive_prices = np.isfinite(prices).all(axis=1) & (prices > 0).all(axis=1)
    flag(~positive_prices, "NONPOSITIVE_OR_INVALID_PRICE", "QUARANTINE")

    volume = df["volume"].to_numpy(dtype=float)
    flag(
        ~np.isfinite(volume) | (volume < 0),
        "INVALID_VOLUME",
        "QUARANTINE"
    )

    # OHLC consistency checks.
    open_price = df["open"].to_numpy(dtype=float)
    high = df["high"].to_numpy(dtype=float)
    low = df["low"].to_numpy(dtype=float)
    close = df["close"].to_numpy(dtype=float)

    valid_prices = np.isfinite(prices).all(axis=1)

    violation = np.zeros(len(df), dtype=float)

    high_violation = np.maximum(
        0,
        np.maximum(open_price, close) - high
    )

    low_violation = np.maximum(
        0,
        low - np.minimum(open_price, close)
    )

    range_violation = np.maximum(0, low - high)

    violation = np.maximum.reduce([
        high_violation,
        low_violation,
        range_violation
    ])

    flag(
        valid_prices & (violation > REVIEW_TOLERANCE),
        "MATERIAL_OHLC_INCONSISTENCY",
        "QUARANTINE"
    )

    flag(
        valid_prices
        & (violation > PRECISION_TOLERANCE)
        & (violation <= REVIEW_TOLERANCE),
        "SMALL_OHLC_INCONSISTENCY_REVIEW",
        "WARNING"
    )

    # Quarantine every occurrence of a duplicate date.
    duplicate_dates = dates.notna() & dates.duplicated(keep=False)
    flag(
        duplicate_dates.to_numpy(),
        "DUPLICATE_DATE",
        "QUARANTINE"
    )

    df["date"] = dates.dt.strftime("%Y-%m-%d")
    df["quality_status"] = status
    df["quality_reason"] = [
        "; ".join(row_reasons) for row_reasons in reasons
    ]

    df["source_file"] = f"{exchange}_{symbol}.csv"

    quarantined = df[df["quality_status"] == "QUARANTINE"].copy()
    warnings = df[df["quality_status"] == "WARNING"].copy()

    processed = df[df["quality_status"] != "QUARANTINE"].copy()

    # Keep standard OHLCV columns in processed files.
    processed = processed[REQUIRED_COLUMNS]

    # Date gaps are measured on retained candles.
    valid_dates = pd.to_datetime(processed["date"], errors="coerce")
    gaps = valid_dates.sort_values().diff().dt.days.dropna()
    large_gaps = gaps[gaps > 7]

    gap_count = len(large_gaps)
    max_gap = int(gaps.max()) if not gaps.empty else 0

    summary = {
        "raw_rows": len(df),
        "pass_candles": status.count("PASS"),
        "warning_candles": status.count("WARNING"),
        "quarantined_candles": status.count("QUARANTINE"),
        "processed_candles": len(processed),
        "date_gaps_over_7_days": gap_count,
        "max_calendar_gap_days": max_gap,
    }

    return processed, quarantined, warnings, summary


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Process only the first N instruments for a pilot."
    )
    args = parser.parse_args()

    universe, manifest = load_inputs()

    if args.limit is not None:
        if args.limit < 1:
            raise ValueError("--limit must be positive.")
        universe = universe.head(args.limit).copy()

    manifest_lookup = manifest.set_index(
        ["exchange", "symbol"]
    ).to_dict("index")

    report_rows = []
    quarantine_frames = []
    warning_frames = []

    for _, instrument in universe.iterrows():
        exchange = instrument["exchange"]
        symbol = instrument["symbol"]
        key = (exchange, symbol)

        manifest_row = manifest_lookup.get(key, {})

        base = {
            "exchange": exchange,
            "symbol": symbol,
            "manifest_status": manifest_row.get("status", "NO_ENTRY"),
            "manifest_candles": manifest_row.get("candles", np.nan),
            "coverage_start": manifest_row.get("coverage_start", np.nan),
            "coverage_end": manifest_row.get("coverage_end", np.nan),
            "manifest_error": manifest_row.get("error", np.nan),
        }

        df, read_status = classify_file(exchange, symbol)

        if df is None:
            base.update({
                "quality_status": read_status,
                "raw_rows": 0,
                "pass_candles": 0,
                "warning_candles": 0,
                "quarantined_candles": 0,
                "processed_candles": 0,
                "date_gaps_over_7_days": 0,
                "max_calendar_gap_days": 0,
            })
            report_rows.append(base)
            continue

        try:
            processed, quarantined, warnings, summary = process_candles(
                df, exchange, symbol
            )

            if not processed.empty:
                output_path = PROCESSED_DIR / f"{exchange}_{symbol}.csv"
                atomic_save_csv(processed, output_path)

            if not quarantined.empty:
                quarantine_frames.append(quarantined)

            if not warnings.empty:
                warning_frames.append(warnings)

            if summary["quarantined_candles"] > 0:
                quality_status = "HAS_QUARANTINED_CANDLES"
            elif summary["warning_candles"] > 0 or summary["date_gaps_over_7_days"] > 0:
                quality_status = "WARNING"
            else:
                quality_status = "PASS"

            base.update(summary)
            base["quality_status"] = quality_status

        except Exception as exc:
            base.update({
                "quality_status": f"PROCESSING_ERROR: {exc}",
                "raw_rows": len(df),
                "pass_candles": 0,
                "warning_candles": 0,
                "quarantined_candles": 0,
                "processed_candles": 0,
                "date_gaps_over_7_days": 0,
                "max_calendar_gap_days": 0,
            })

        report_rows.append(base)

        print(
            f"{exchange}:{symbol} -> "
            f"{base['quality_status']}"
        )

    report = pd.DataFrame(report_rows)

    quarantine = (
        pd.concat(quarantine_frames, ignore_index=True)
        if quarantine_frames else pd.DataFrame()
    )

    warnings = (
        pd.concat(warning_frames, ignore_index=True)
        if warning_frames else pd.DataFrame()
    )

    atomic_save_csv(report, REPORT_FILE)
    atomic_save_csv(quarantine, QUARANTINE_FILE)
    atomic_save_csv(warnings, WARNING_FILE)

    print("\n========== QUALITY PROCESSING SUMMARY ==========")
    print(f"Instruments processed: {len(report)}")
    print("\nStock quality statuses:")
    print(report["quality_status"].value_counts(dropna=False).to_string())

    print("\nCandle totals:")
    for column in [
        "raw_rows",
        "pass_candles",
        "warning_candles",
        "quarantined_candles",
        "processed_candles",
    ]:
        print(f"{column}: {report[column].sum()}")

    print(f"\nReport: {REPORT_FILE}")
    print(f"Quarantine: {QUARANTINE_FILE}")
    print(f"Warnings: {WARNING_FILE}")
    print(f"Processed data: {PROCESSED_DIR}")


if __name__ == "__main__":
    main()
