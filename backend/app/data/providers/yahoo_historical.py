
from datetime import date, timedelta

import numpy as np
import pandas as pd
import yfinance as yf

from app.data.instruments import InstrumentRegistry

yf.config.debug.hide_exceptions = False
REQUIRED_COLUMNS = ["Open", "High", "Low", "Close", "Volume"]
OUTPUT_COLUMNS = ["date", "open", "high", "low", "close", "volume"]


class YahooHistoricalProvider:
    """Fetch daily historical OHLCV data from Yahoo Finance."""

    def __init__(self, instrument_registry: InstrumentRegistry):
        self.instrument_registry = instrument_registry

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
            raise ValueError(f"Unsupported exchange: {exchange}")

        if start_date > end_date:
            raise ValueError("start_date cannot be after end_date")

        instrument = self.instrument_registry.get_by_exchange_symbol(
            exchange, symbol
        )

        yahoo_symbol = instrument.provider_symbols.get("yahoo")
        if not yahoo_symbol:
            raise ValueError(
                f"No Yahoo Finance symbol configured for {exchange}:{symbol}"
            )

        ticker = yf.Ticker(yahoo_symbol)

        history = ticker.history(
            start=start_date.isoformat(),
            end=(end_date + timedelta(days=1)).isoformat(),
            interval="1d",
            auto_adjust=False,
            actions=False,
        )

        if history.empty:
            return pd.DataFrame(columns=OUTPUT_COLUMNS)

        missing = set(REQUIRED_COLUMNS) - set(history.columns)
        if missing:
            raise ValueError(
                f"Yahoo data missing columns: {sorted(missing)}"
            )

        df = history[REQUIRED_COLUMNS].copy()

        # Convert Yahoo's datetime index into date-only values.
        dates = pd.to_datetime(df.index)
        if dates.tz is not None:
            dates = dates.tz_convert("Asia/Kolkata").tz_localize(None)

        df.insert(0, "date", dates.date)
        df = df.reset_index(drop=True)

        df.columns = df.columns.str.lower()

        for column in OUTPUT_COLUMNS[1:]:
            df[column] = pd.to_numeric(df[column], errors="coerce")

        if df.isnull().any().any():
            raise ValueError("Yahoo data contains missing or invalid values")

        numeric_data = df[OUTPUT_COLUMNS[1:]].to_numpy(dtype=float)
        if not np.isfinite(numeric_data).all():
            raise ValueError("Yahoo data contains non-finite values")

        price_columns = ["open", "high", "low", "close"]

        if (df[price_columns] <= 0).any().any():
            raise ValueError("OHLC prices must be positive")

        if (df["volume"] < 0).any():
            raise ValueError("Volume cannot be negative")

        if (df["high"] < df[["open", "low", "close"]].max(axis=1)).any():
            raise ValueError("Invalid OHLC data: inconsistent high price")

        if (df["low"] > df[["open", "high", "close"]].min(axis=1)).any():
            raise ValueError("Invalid OHLC data: inconsistent low price")

        df = df.sort_values("date").reset_index(drop=True)

        if df["date"].duplicated().any():
            raise ValueError("Duplicate dates found in Yahoo data")

        return df[OUTPUT_COLUMNS]
