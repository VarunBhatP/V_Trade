
import argparse
import time
from datetime import date, datetime
from pathlib import Path

import pandas as pd

from app.data.universe import InstrumentUniverse
from app.data.providers.yahoo_historical import YahooHistoricalProvider


PROJECT_ROOT = Path(__file__).resolve().parents[1]

UNIVERSE_FILE = (
    PROJECT_ROOT / "data" / "universe" / "validated_universe.csv"
)

DATA_DIR = PROJECT_ROOT / "data" / "raw" / "yahoo_20y"

MANIFEST_FILE = (
    PROJECT_ROOT / "data" / "universe" / "download_manifest.csv"
)

START_DATE = date(2006, 11, 9)
END_DATE = date(2026, 11, 9)

MAX_RETRIES = 3
DEFAULT_DELAY = 1.0

MANIFEST_COLUMNS = [
    "exchange",
    "symbol",
    "yahoo_symbol",
    "start_date",
    "end_date",
    "status",
    "candles",
    "coverage_start",
    "coverage_end",
    "last_attempt_at",
    "error",
]


def atomic_save_csv(df, path):
    path.parent.mkdir(parents=True, exist_ok=True)

    temporary_path = path.with_suffix(path.suffix + ".tmp")
    df.to_csv(temporary_path, index=False)
    temporary_path.replace(path)


def load_manifest():
    if not MANIFEST_FILE.exists():
        return {}

    df = pd.read_csv(MANIFEST_FILE, dtype=str).fillna("")

    records = {}

    for row in df.to_dict("records"):
        key = (
            row["exchange"],
            row["symbol"],
            row["start_date"],
            row["end_date"],
        )
        records[key] = row

    return records


def save_manifest(records):
    df = pd.DataFrame(
        list(records.values()),
        columns=MANIFEST_COLUMNS,
    )

    atomic_save_csv(df, MANIFEST_FILE)


def download_instrument(provider, instrument):
    last_error = None

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            df = provider.fetch_daily(
                exchange=instrument.exchange,
                symbol=instrument.symbol,
                start_date=START_DATE,
                end_date=END_DATE,
            )

            if df.empty:
                raise ValueError("Yahoo returned no historical candles.")

            if df.empty or list(df.columns) != [
                "date", "open", "high", "low", "close", "volume"
            ]:
                raise ValueError("Unexpected OHLCV output format.")

            return df

        except Exception as exc:
            last_error = exc

            if attempt < MAX_RETRIES:
                wait_seconds = 2 ** attempt

                print(
                    f"  Retry {attempt}/{MAX_RETRIES - 1} "
                    f"after {wait_seconds}s: {exc}"
                )

                time.sleep(wait_seconds)

    raise RuntimeError(str(last_error))


def main():
    parser = argparse.ArgumentParser(
        description="Download Yahoo daily history for the validated universe."
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=5,
        help="Number of instruments to process. Default: 5.",
    )

    parser.add_argument(
        "--all",
        action="store_true",
        help="Process the entire validated universe.",
    )

    parser.add_argument(
        "--delay",
        type=float,
        default=DEFAULT_DELAY,
        help="Delay between instruments in seconds.",
    )

    args = parser.parse_args()

    if args.limit < 1:
        raise ValueError("--limit must be at least 1.")

    if args.delay < 0:
        raise ValueError("--delay cannot be negative.")

    universe = InstrumentUniverse.from_csv(UNIVERSE_FILE)

    provider = YahooHistoricalProvider(
        instrument_registry=universe.registry
    )

    instruments = universe.get_all()

    if not args.all:
        instruments = instruments[:args.limit]

    records = load_manifest()

    print("\n========== YAHOO BULK DOWNLOADER ==========")
    print(f"Universe size: {universe.count()}")
    print(f"Selected instruments: {len(instruments)}")
    print(f"Date range: {START_DATE} to {END_DATE}")
    print(f"Output directory: {DATA_DIR}")
    print(f"Manifest: {MANIFEST_FILE}\n")

    counts = {
        "SUCCESS": 0,
        "SKIPPED": 0,
        "EMPTY": 0,
        "FAILED": 0,
    }

    for index, instrument in enumerate(instruments, start=1):
        key = (
            instrument.exchange,
            instrument.symbol,
            START_DATE.isoformat(),
            END_DATE.isoformat(),
        )

        output_file = (
            DATA_DIR /
            f"{instrument.exchange}_{instrument.symbol}.csv"
        )

        existing = records.get(key, {})

        if (
            existing.get("status") == "SUCCESS"
            and output_file.is_file()
        ):
            counts["SKIPPED"] += 1
            print(
                f"[{index}/{len(instruments)}] "
                f"{instrument.symbol:15} SKIPPED"
            )
            continue

        yahoo_symbol = instrument.provider_symbols.get("yahoo", "")

        print(
            f"[{index}/{len(instruments)}] "
            f"{instrument.symbol:15} downloading..."
        )

        try:
            df = download_instrument(provider, instrument)

            atomic_save_csv(df, output_file)

            records[key] = {
                "exchange": instrument.exchange,
                "symbol": instrument.symbol,
                "yahoo_symbol": yahoo_symbol,
                "start_date": START_DATE.isoformat(),
                "end_date": END_DATE.isoformat(),
                "status": "SUCCESS",
                "candles": str(len(df)),
                "coverage_start": str(df["date"].min()),
                "coverage_end": str(df["date"].max()),
                "last_attempt_at": datetime.now().isoformat(
                    timespec="seconds"
                ),
                "error": "",
            }

            counts["SUCCESS"] += 1

            print(
                f"  SUCCESS | {len(df)} candles | "
                f"{df['date'].min()} to {df['date'].max()}"
            )

        except ValueError as exc:
            # Empty history is recorded separately.
            if "no historical candles" in str(exc).lower():
                status = "EMPTY"
                counts["EMPTY"] += 1
            else:
                status = "FAILED"
                counts["FAILED"] += 1

            records[key] = {
                "exchange": instrument.exchange,
                "symbol": instrument.symbol,
                "yahoo_symbol": yahoo_symbol,
                "start_date": START_DATE.isoformat(),
                "end_date": END_DATE.isoformat(),
                "status": status,
                "candles": "0",
                "coverage_start": "",
                "coverage_end": "",
                "last_attempt_at": datetime.now().isoformat(
                    timespec="seconds"
                ),
                "error": str(exc)[:500],
            }

            print(f"  {status}: {exc}")

        except Exception as exc:
            counts["FAILED"] += 1

            records[key] = {
                "exchange": instrument.exchange,
                "symbol": instrument.symbol,
                "yahoo_symbol": yahoo_symbol,
                "start_date": START_DATE.isoformat(),
                "end_date": END_DATE.isoformat(),
                "status": "FAILED",
                "candles": "0",
                "coverage_start": "",
                "coverage_end": "",
                "last_attempt_at": datetime.now().isoformat(
                    timespec="seconds"
                ),
                "error": str(exc)[:500],
            }

            print(f"  FAILED: {exc}")

        finally:
            # Save progress after every instrument.
            save_manifest(records)

        if index < len(instruments):
            time.sleep(args.delay)

    print("\n========== DOWNLOAD SUMMARY ==========")
    for status, count in counts.items():
        print(f"{status:10}: {count}")

    print(f"\nManifest: {MANIFEST_FILE}")
    print(f"Data directory: {DATA_DIR}")


if __name__ == "__main__":
    main()
