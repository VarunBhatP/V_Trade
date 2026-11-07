
from datetime import date, datetime

import pandas as pd
import pytest

from app.data.providers.zerodha_historical import (
    ZerodhaHistoricalProvider,
)
import app.data.providers.zerodha_historical as historical_module


class FakeKite:
    def __init__(self):
        self.instrument_calls = 0
        self.history_calls = 0

    def instruments(self, exchange):
        self.instrument_calls += 1
        return [
            {
                "tradingsymbol": "RELIANCE",
                "exchange": "NSE",
                "instrument_type": "EQ",
                "instrument_token": 12345,
            },
            {
                "tradingsymbol": "RELIANCE",
                "exchange": "NSE",
                "instrument_type": "FUT",
                "instrument_token": 99999,
            },
        ]

    def historical_data(self, **kwargs):
        self.history_calls += 1
        return [
            {
                "date": datetime.fromisoformat("2026-11-05T09:15:00+05:30"),
                "open": 1500,
                "high": 1550,
                "low": 1490,
                "close": 1530,
                "volume": 100000,
            },
            {
                "date": datetime.fromisoformat("2026-11-06T09:15:00+05:30"),
                "open": 1530,
                "high": 1570,
                "low": 1520,
                "close": 1560,
                "volume": 120000,
            },
        ]


@pytest.fixture
def fake_kite(monkeypatch):
    kite = FakeKite()
    monkeypatch.setattr(
        historical_module.zerodha_service,
        "get_authenticated_client",
        lambda: kite,
    )
    return kite


def test_fetch_daily_returns_valid_ohlcv(fake_kite):
    provider = ZerodhaHistoricalProvider()

    df = provider.fetch_daily(
        exchange="NSE",
        symbol="RELIANCE",
        start_date=date(2026, 11, 5),
        end_date=date(2026, 11, 6),
    )

    assert list(df.columns) == [
        "date", "open", "high", "low", "close", "volume"
    ]
    assert len(df) == 2
    assert df["close"].tolist() == [1530, 1560]
    assert df["date"].is_monotonic_increasing
    assert fake_kite.history_calls == 1


def test_instrument_lookup_uses_equity_token(fake_kite):
    provider = ZerodhaHistoricalProvider()

    token = provider._get_instrument_token("NSE", "RELIANCE")

    assert token == 12345


def test_instrument_master_is_cached_for_same_day(fake_kite):
    provider = ZerodhaHistoricalProvider()

    provider._get_instruments("NSE")
    provider._get_instruments("NSE")

    assert fake_kite.instrument_calls == 1


def test_unsupported_exchange_is_rejected(fake_kite):
    provider = ZerodhaHistoricalProvider()

    with pytest.raises(ValueError):
        provider.fetch_daily(
            exchange="MCX",
            symbol="RELIANCE",
            start_date=date(2026, 11, 5),
            end_date=date(2026, 11, 6),
        )


def test_invalid_date_range_is_rejected(fake_kite):
    provider = ZerodhaHistoricalProvider()

    with pytest.raises(ValueError):
        provider.fetch_daily(
            exchange="NSE",
            symbol="RELIANCE",
            start_date=date(2026, 11, 7),
            end_date=date(2026, 11, 5),
        )


def test_missing_instrument_is_rejected(fake_kite):
    provider = ZerodhaHistoricalProvider()

    with pytest.raises(ValueError, match="Equity instrument not found"):
        provider._get_instrument_token("NSE", "UNKNOWN")


def test_empty_historical_response_returns_empty_dataframe(fake_kite):
    fake_kite.historical_data = lambda **kwargs: []

    provider = ZerodhaHistoricalProvider()

    df = provider.fetch_daily(
        exchange="NSE",
        symbol="RELIANCE",
        start_date=date(2026, 11, 5),
        end_date=date(2026, 11, 6),
    )

    assert df.empty
    assert list(df.columns) == [
        "date", "open", "high", "low", "close", "volume"
    ]

def test_missing_columns_are_rejected(fake_kite):
    fake_kite.historical_data = lambda **kwargs: [
        {
            "date": datetime.fromisoformat("2026-11-05T09:15:00+05:30"),
            "open": 1500,
            "high": 1550,
            "low": 1490,
            "close": 1530,
            # volume deliberately missing
        }
    ]

    provider = ZerodhaHistoricalProvider()

    with pytest.raises(ValueError, match="missing columns"):
        provider.fetch_daily(
            exchange="NSE",
            symbol="RELIANCE",
            start_date=date(2026, 11, 5),
            end_date=date(2026, 11, 6),
        )


def test_non_finite_values_are_rejected(fake_kite):
    fake_kite.historical_data = lambda **kwargs: [
        {
            "date": datetime.fromisoformat("2026-11-05T09:15:00+05:30"),
            "open": 1500,
            "high": 1550,
            "low": 1490,
            "close": float("nan"),
            "volume": 100000,
        }
    ]

    provider = ZerodhaHistoricalProvider()

    with pytest.raises(ValueError, match="invalid numeric"):
        provider.fetch_daily(
            exchange="NSE",
            symbol="RELIANCE",
            start_date=date(2026, 11, 5),
            end_date=date(2026, 11, 6),
        )


def test_inconsistent_ohlc_is_rejected(fake_kite):
    fake_kite.historical_data = lambda **kwargs: [
        {
            "date": datetime.fromisoformat("2026-11-05T09:15:00+05:30"),
            "open": 1500,
            "high": 1490,
            "low": 1480,
            "close": 1495,
            "volume": 100000,
        }
    ]

    provider = ZerodhaHistoricalProvider()

    with pytest.raises(ValueError, match="inconsistent OHLC"):
        provider.fetch_daily(
            exchange="NSE",
            symbol="RELIANCE",
            start_date=date(2026, 11, 5),
            end_date=date(2026, 11, 6),
        )


def test_duplicate_candle_dates_are_rejected(fake_kite):
    candle = {
        "date": datetime.fromisoformat("2026-11-05T09:15:00+05:30"),
        "open": 1500,
        "high": 1550,
        "low": 1490,
        "close": 1530,
        "volume": 100000,
    }

    fake_kite.historical_data = lambda **kwargs: [candle, candle.copy()]

    provider = ZerodhaHistoricalProvider()

    with pytest.raises(ValueError, match="duplicate dates"):
        provider.fetch_daily(
            exchange="NSE",
            symbol="RELIANCE",
            start_date=date(2026, 11, 5),
            end_date=date(2026, 11, 6),
        )


def test_multiple_matching_equity_instruments_are_rejected(fake_kite):
    fake_kite.instruments = lambda exchange: [
        {
            "tradingsymbol": "RELIANCE",
            "exchange": "NSE",
            "instrument_type": "EQ",
            "instrument_token": 12345,
        },
        {
            "tradingsymbol": "RELIANCE",
            "exchange": "NSE",
            "instrument_type": "EQ",
            "instrument_token": 67890,
        },
    ]

    provider = ZerodhaHistoricalProvider()

    with pytest.raises(ValueError, match="Multiple matching"):
        provider._get_instrument_token("NSE", "RELIANCE")
