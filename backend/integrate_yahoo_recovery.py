
import argparse
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]

PROCESSED_DIR = PROJECT_ROOT / "data/processed/yahoo_20y"
RAW_RECOVERY_DIR = PROJECT_ROOT / "data/raw/yahoo_recovery"

BASE_REPORT = PROJECT_ROOT / "data/universe/data_quality_report.csv"
RECOVERY_REPORT = PROJECT_ROOT / "data/universe/yahoo_recovery_report.csv"
ANOMALY_FILE = PROJECT_ROOT / "data/universe/yahoo_recovery_anomalies.csv"

FINAL_REPORT = PROJECT_ROOT / "data/universe/data_quality_report_final.csv"
FINAL_QUARANTINE = PROJECT_ROOT / "data/processed/quarantined_candles_final.csv"
FINAL_WARNINGS = PROJECT_ROOT / "data/processed/warning_candles_final.csv"

OHLCV_COLUMNS = ["date", "open", "high", "low", "close", "volume"]


def atomic_save_csv(df, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    df.to_csv(temp, index=False)
    temp.replace(path)


def load_csv(path):
    return pd.read_csv(path)


def prepare_recovery():
    base = load_csv(BASE_REPORT)
    recovery = load_csv(RECOVERY_REPORT)
    anomalies = load_csv(ANOMALY_FILE)

    if len(base) != 499:
        raise ValueError("Expected 499 instruments in the original report.")

    failed_symbols = set(
        base.loc[base["quality_status"] == "MISSING_FILE", "symbol"]
    )

    recovered_symbols = set(recovery["symbol"])

    if failed_symbols != recovered_symbols:
        raise ValueError(
            "The recovered symbols do not exactly match the 18 missing stocks."
        )

    if not (recovery["status"] == "FETCHED").all():
        raise ValueError("Some recovery fetches failed.")

    prepared_files = []
    quarantine_frames = []
    warning_frames = []
    updated_rows = []

    for _, item in recovery.iterrows():
        exchange = item["exchange"]
        symbol = item["symbol"]

        raw_path = RAW_RECOVERY_DIR / f"{exchange}_{symbol}.csv"

        if not raw_path.is_file():
            raise FileNotFoundError(raw_path)

        raw = pd.read_csv(raw_path)

        required = {"date", "Open", "High", "Low", "Close", "Volume"}

        if not required.issubset(raw.columns):
            raise ValueError(
                f"{symbol}: missing raw columns "
                f"{required - set(raw.columns)}"
            )

        raw["date"] = raw["date"].astype(str).str[:10]

        stock_anomalies = anomalies[
            anomalies["symbol"] == symbol
        ].copy()

        stock_anomalies["date"] = (
            stock_anomalies["date"].astype(str).str[:10]
        )

        quarantined_dates = set(
            stock_anomalies.loc[
                stock_anomalies["quality_status"] == "QUARANTINE",
                "date"
            ]
        )

        warning_dates = set(
            stock_anomalies.loc[
                stock_anomalies["quality_status"] == "WARNING",
                "date"
            ]
        )

        # Validate that every flagged date exists in the raw response.
        raw_dates = set(raw["date"])

        if not quarantined_dates.issubset(raw_dates):
            raise ValueError(f"{symbol}: quarantined date missing in raw data.")

        if not warning_dates.issubset(raw_dates):
            raise ValueError(f"{symbol}: warning date missing in raw data.")

        clean = pd.DataFrame({
            "date": raw["date"],
            "open": pd.to_numeric(raw["Open"], errors="coerce"),
            "high": pd.to_numeric(raw["High"], errors="coerce"),
            "low": pd.to_numeric(raw["Low"], errors="coerce"),
            "close": pd.to_numeric(raw["Close"], errors="coerce"),
            "volume": pd.to_numeric(raw["Volume"], errors="coerce"),
        })

        clean = clean[~clean["date"].isin(quarantined_dates)].copy()

        if clean.duplicated("date").any():
            raise ValueError(f"{symbol}: duplicate dates in clean data.")

        if clean[OHLCV_COLUMNS].isna().any().any():
            raise ValueError(f"{symbol}: missing numeric values in clean data.")

        if len(clean) != int(item["pass"] + item["warning"]):
            raise ValueError(
                f"{symbol}: processed candle count does not match "
                "the recovery report."
            )

        quarantine_frames.append(stock_anomalies[
            stock_anomalies["quality_status"] == "QUARANTINE"
        ])

        warning_frames.append(stock_anomalies[
            stock_anomalies["quality_status"] == "WARNING"
        ])

        status = (
            "RECOVERED_WITH_QUARANTINE"
            if item["quarantine"] > 0
            else "RECOVERED_WITH_WARNING"
            if item["warning"] > 0
            else "RECOVERED"
        )

        dates = pd.to_datetime(clean["date"], errors="raise")
        gaps = dates.sort_values().diff().dt.days.dropna()

        updated_rows.append({
            "symbol": symbol,
            "raw_rows": len(raw),
            "pass_candles": int(item["pass"]),
            "warning_candles": int(item["warning"]),
            "quarantined_candles": int(item["quarantine"]),
            "processed_candles": len(clean),
            "date_gaps_over_7_days": int((gaps > 7).sum()),
            "max_calendar_gap_days": int(gaps.max()) if not gaps.empty else 0,
            "quality_status": status,
        })

        prepared_files.append((
            clean,
            PROCESSED_DIR / f"{exchange}_{symbol}.csv"
        ))

    return (
        base,
        prepared_files,
        updated_rows,
        quarantine_frames,
        warning_frames,
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Write the recovered processed files and final reports."
    )
    args = parser.parse_args()

    (
        base,
        prepared_files,
        updated_rows,
        quarantine_frames,
        warning_frames,
    ) = prepare_recovery()

    # Build a separate final report.
    final_report = base.copy()

    for update in updated_rows:
        mask = final_report["symbol"] == update["symbol"]

        for column, value in update.items():
            final_report.loc[mask, column] = value

    quarantine = pd.concat(quarantine_frames, ignore_index=True)
    warnings = pd.concat(warning_frames, ignore_index=True)

    print("\n========== RECOVERY INTEGRATION VALIDATION ==========")
    print(f"Recovered instruments: {len(prepared_files)}")
    print(f"Quarantined candles: {len(quarantine)}")
    print(f"Warning candles: {len(warnings)}")
    print(
        "Recovered processed candles:",
        sum(len(df) for df, _ in prepared_files)
    )

    print("\nFinal instrument statuses:")
    print(final_report["quality_status"].value_counts().to_string())

    print("\nFinal processed candle total:")
    print(final_report["processed_candles"].sum())

    if not args.apply:
        print("\nDRY RUN: No files were modified.")
        print("Review the summary, then run with --apply.")
        return

    # All 18 files have passed validation before reaching this point.
    for df, path in prepared_files:
        atomic_save_csv(df, path)

    atomic_save_csv(final_report, FINAL_REPORT)
    atomic_save_csv(quarantine, FINAL_QUARANTINE)
    atomic_save_csv(warnings, FINAL_WARNINGS)

    print("\nINTEGRATION COMPLETE")
    print(f"Final report: {FINAL_REPORT}")
    print(f"Final quarantine: {FINAL_QUARANTINE}")
    print(f"Final warnings: {FINAL_WARNINGS}")
    print(f"Processed directory: {PROCESSED_DIR}")


if __name__ == "__main__":
    main()
