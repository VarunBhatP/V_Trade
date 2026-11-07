
from datetime import date
from typing import Protocol

import pandas as pd


class HistoricalDataProvider(Protocol):
    """
    Common interface for historical market data providers.

    Implementations may use Zerodha, CSV files,
    or another supported data source.
    """

    def fetch_daily(
        self,
        *,
        exchange: str,
        symbol: str,
        start_date: date,
        end_date: date,
    ) -> pd.DataFrame:
        """
        Return daily OHLCV data in a standardized format.

        Required columns:
        date, open, high, low, close, volume
        """
        ...
