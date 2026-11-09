
from datetime import date
from pathlib import Path

import pandas as pd

from app.data.loader import load_ohlcv_csv


PROJECT_ROOT = Path(__file__).resolve().parents[4]
DEFAULT_DATA_DIR = PROJECT_ROOT / "data" / "raw"

OHLCV_COLUMNS = [
    "date",
    "open",
    "high",
    "low",
    "close",
    "volume",
]


class CsvHistoricalProvider:
    def __init__(self, data_dir: str | Path | None = None):
        self.data_dir = Path(data_dir) if data_dir else DEFAULT_DATA_DIR

    def fetch_daily(
        self,
        *,
        exchange: str,
        symbol: str,
        start_date: date,
        end_date: date,
    ) -> pd.DataFrame:

        exchange = exchange.strip().upper()
        symbol = symbol.strip().upper()

        if exchange not in {"NSE", "BSE"}:
            raise ValueError("Only NSE and BSE are supported")

        if not symbol:
            raise ValueError("Symbol cannot be empty")

        if not isinstance(start_date, date) or isinstance(start_date, pd.Timestamp):
            raise ValueError("start_date must be a date")

        if not isinstance(end_date, date) or isinstance(end_date, pd.Timestamp):
            raise ValueError("end_date must be a date")

        if start_date > end_date:
            raise ValueError("start_date cannot be after end_date")

        # Exchange-specific naming avoids mixing NSE and BSE data.
        file_path = self.data_dir / f"{exchange}_{symbol}.csv"

        # Backward compatibility for existing NSE files such as RELIANCE.csv.
        if not file_path.is_file() and exchange == "NSE":
            legacy_path = self.data_dir / f"{symbol}.csv"
            if legacy_path.is_file():
                file_path = legacy_path

        df = load_ohlcv_csv(file_path)

        start = pd.Timestamp(start_date)
        end = pd.Timestamp(end_date)

        df = df[
            (df["date"] >= start) &
            (df["date"] <= end)
        ].copy()

        return df.reset_index(drop=True)
