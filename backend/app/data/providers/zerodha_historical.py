
from datetime import date, datetime, time
import logging

import numpy as np
import pandas as pd

from app.brokers.zerodha import zerodha_service


logger = logging.getLogger(__name__)

OHLCV_COLUMNS = ["date", "open", "high", "low", "close", "volume"]


class ZerodhaHistoricalProvider:

    def __init__(self):
        self._instrument_cache = {}

    def _get_instruments(self, exchange: str):
        today = date.today()
        cached = self._instrument_cache.get(exchange)

        # Reuse the instrument master during the same day.
        if cached and cached["date"] == today:
            return cached["instruments"]

        kite = zerodha_service.get_authenticated_client()
        instruments = kite.instruments(exchange)

        self._instrument_cache[exchange] = {
            "date": today,
            "instruments": instruments,
        }

        return instruments

    def _get_instrument_token(self, exchange: str, symbol: str) -> int:
        instruments = self._get_instruments(exchange)

        matches = [
            item for item in instruments
            if item["tradingsymbol"] == symbol
            and item["exchange"] == exchange
            and item["instrument_type"] == "EQ"
        ]

        if not matches:
            raise ValueError(
                f"Equity instrument not found: {exchange}:{symbol}"
            )

        if len(matches) > 1:
            raise ValueError(
                f"Multiple matching instruments found: {exchange}:{symbol}"
            )

        return int(matches[0]["instrument_token"])

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

        if start_date > end_date:
            raise ValueError("start_date cannot be after end_date")

        token = self._get_instrument_token(exchange, symbol)

        kite = zerodha_service.get_authenticated_client()

        records = kite.historical_data(
            instrument_token=token,
            from_date=datetime.combine(start_date, time.min),
            to_date=datetime.combine(end_date, time.max),
            interval="day",
        )

        if not records:
            return pd.DataFrame(columns=OHLCV_COLUMNS)

        df = pd.DataFrame.from_records(records)

        missing = set(OHLCV_COLUMNS) - set(df.columns)
        if missing:
            raise ValueError(
                f"Historical response missing columns: {sorted(missing)}"
            )

        df = df[OHLCV_COLUMNS].copy()

        # Convert timestamps to Indian market time, then remove timezone.
        timestamps = pd.to_datetime(df["date"], errors="raise", utc=True)
        df["date"] = (
            timestamps.dt.tz_convert("Asia/Kolkata")
            .dt.tz_localize(None)
            .dt.normalize()
        )

        numeric_columns = ["open", "high", "low", "close", "volume"]

        for column in numeric_columns:
            df[column] = pd.to_numeric(df[column], errors="coerce")

        values = df[numeric_columns].to_numpy(dtype=float)

        if not np.isfinite(values).all():
            raise ValueError("Historical data contains invalid numeric values")

        if (df[["open", "high", "low", "close"]] <= 0).any().any():
            raise ValueError("Historical data contains non-positive prices")

        if (df["volume"] < 0).any():
            raise ValueError("Historical data contains negative volume")

        if (
            (df["high"] < df[["open", "close", "low"]].max(axis=1))
            | (df["low"] > df[["open", "close"]].min(axis=1))
        ).any():
            raise ValueError("Historical data contains inconsistent OHLC values")

        if df["date"].duplicated().any():
            raise ValueError("Historical data contains duplicate dates")

        return df.sort_values("date").reset_index(drop=True)
