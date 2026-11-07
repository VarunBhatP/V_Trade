
from pathlib import Path

import numpy as np
import pandas as pd


REQUIRED_COLUMNS = [
    "date",
    "open",
    "high",
    "low",
    "close",
    "volume",
]

PRICE_COLUMNS = ["open", "high", "low", "close"]


def load_ohlcv_csv(file_path: str | Path) -> pd.DataFrame:
    path = Path(file_path)

    if not path.is_file():
        raise FileNotFoundError(f"Market data file not found: {path}")

    try:
        df = pd.read_csv(path)
    except pd.errors.ParserError as exc:
        raise ValueError(f"Invalid CSV format: {exc}") from exc

    if df.empty:
        raise ValueError("Market data file is empty")

    df.columns = df.columns.str.strip().str.lower()

    missing = set(REQUIRED_COLUMNS) - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")

    df = df[REQUIRED_COLUMNS].copy()

    df["date"] = pd.to_datetime(df["date"], errors="coerce")

    for column in PRICE_COLUMNS + ["volume"]:
        df[column] = pd.to_numeric(df[column], errors="coerce")

    if df.isnull().any().any():
        raise ValueError("Market data contains missing or invalid values")

    numeric_data = df[PRICE_COLUMNS + ["volume"]].to_numpy()

    if not np.isfinite(numeric_data).all():
        raise ValueError("Market data contains non-finite values")

    if (df[PRICE_COLUMNS] <= 0).any().any():
        raise ValueError("OHLC prices must be positive")

    if (df["volume"] < 0).any():
        raise ValueError("Volume cannot be negative")

    if (df["high"] < df[["open", "low", "close"]].max(axis=1)).any():
        raise ValueError("Invalid OHLC data: high price is inconsistent")

    if (df["low"] > df[["open", "high", "close"]].min(axis=1)).any():
        raise ValueError("Invalid OHLC data: low price is inconsistent")

    df = df.sort_values("date").reset_index(drop=True)

    if df["date"].duplicated().any():
        raise ValueError("Duplicate dates found in market data")

    return df
