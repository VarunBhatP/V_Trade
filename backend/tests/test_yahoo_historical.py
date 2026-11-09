
from datetime import date, timedelta

import pandas as pd
import pytest

from app.data.instruments import Instrument, InstrumentRegistry
from app.data.providers.yahoo_historical import YahooHistoricalProvider


@pytest.fixture
def registry():
    instruments = InstrumentRegistry()

    instruments.add(
        Instrument(
            instrument_id="NSE:INE002A01018",
            exchange="NSE",
            symbol="RELIANCE",
            company_name="Reliance Industries Ltd",
            isin="INE002A01018",
            provider_symbols={
                "zerodha": "RELIANCE",
                "yahoo": "RELIANCE.NS",
            },
        )
    )

    return instruments


@pytest.fixture
def provider(registry):
    return YahooHistoricalProvider(instrument_registry=registry)


@pytest.fixture
def sample_yahoo_data():
    index = pd.to_datetime([
        "2026-01-05",
        "2026-01-06",
        "2026-01-07",
    ])

    return pd.DataFrame(
        {
            "Open": [1400.0, 1410.0, 1420.0],
            "High": [1420.0, 1430.0, 1440.0],
            "Low": [1390.0, 1400.0, 1410.0],
            "Close": [1410.0, 1420.0, 1430.0],
            "Volume": [100000, 110000, 120000],
            "Adj Close": [1405.0, 1415.0, 1425.0],
        },
        index=index,
    )


def test_fetch_daily_returns_standard_ohlcv(
    provider, monkeypatch, sample_yahoo_data
):
    class FakeTicker:
        def __init__(self, symbol):
            assert symbol == "RELIANCE.NS"

        def history(self, **kwargs):
            return sample_yahoo_data

    monkeypatch.setattr(
        "app.data.providers.yahoo_historical.yf.Ticker",
        FakeTicker,
    )

    result = provider.fetch_daily(
        exchange="NSE",
        symbol="RELIANCE",
        start_date=date(2026, 1, 5),
        end_date=date(2026, 1, 7),
    )

    assert list(result.columns) == [
        "date", "open", "high", "low", "close", "volume"
    ]

    assert len(result) == 3
    assert result["close"].tolist() == [1410.0, 1420.0, 1430.0]
    assert result["volume"].tolist() == [100000, 110000, 120000]


def test_fetch_daily_uses_correct_yahoo_parameters(
    provider, monkeypatch, sample_yahoo_data
):
    captured = {}

    class FakeTicker:
        def __init__(self, symbol):
            captured["symbol"] = symbol

        def history(self, **kwargs):
            captured.update(kwargs)
            return sample_yahoo_data

    monkeypatch.setattr(
        "app.data.providers.yahoo_historical.yf.Ticker",
        FakeTicker,
    )

    provider.fetch_daily(
        exchange="NSE",
        symbol="RELIANCE",
        start_date=date(2026, 1, 5),
        end_date=date(2026, 1, 7),
    )

    assert captured["symbol"] == "RELIANCE.NS"
    assert captured["start"] == "2026-01-05"
    assert captured["end"] == "2026-01-08"
    assert captured["interval"] == "1d"
    assert captured["auto_adjust"] is False
    assert captured["actions"] is False
    assert "raise_errors" not in captured


def test_fetch_daily_includes_end_date(
    provider, monkeypatch, sample_yahoo_data
):
    captured = {}

    class FakeTicker:
        def __init__(self, symbol):
            pass

        def history(self, **kwargs):
            captured.update(kwargs)
            return sample_yahoo_data

    monkeypatch.setattr(
        "app.data.providers.yahoo_historical.yf.Ticker",
        FakeTicker,
    )

    provider.fetch_daily(
        exchange="NSE",
        symbol="RELIANCE",
        start_date=date(2026, 1, 5),
        end_date=date(2026, 1, 7),
    )

    # Yahoo's end parameter is exclusive.
    assert captured["end"] == (
        date(2026, 1, 7) + timedelta(days=1)
    ).isoformat()


def test_fetch_daily_returns_empty_dataframe(
    provider, monkeypatch
):
    class FakeTicker:
        def __init__(self, symbol):
            pass

        def history(self, **kwargs):
            return pd.DataFrame()

    monkeypatch.setattr(
        "app.data.providers.yahoo_historical.yf.Ticker",
        FakeTicker,
    )

    result = provider.fetch_daily(
        exchange="NSE",
        symbol="RELIANCE",
        start_date=date(2026, 1, 5),
        end_date=date(2026, 1, 7),
    )

    assert result.empty
    assert list(result.columns) == [
        "date", "open", "high", "low", "close", "volume"
    ]


def test_fetch_daily_rejects_unknown_instrument(
    provider,
):
    with pytest.raises(KeyError):
        provider.fetch_daily(
            exchange="NSE",
            symbol="UNKNOWN",
            start_date=date(2026, 1, 5),
            end_date=date(2026, 1, 7),
        )


def test_fetch_daily_rejects_missing_columns(
    provider, monkeypatch
):
    invalid_data = pd.DataFrame(
        {
            "Open": [100.0],
            "High": [110.0],
            "Low": [90.0],
            "Close": [105.0],
        },
        index=pd.to_datetime(["2026-01-05"]),
    )

    class FakeTicker:
        def __init__(self, symbol):
            pass

        def history(self, **kwargs):
            return invalid_data

    monkeypatch.setattr(
        "app.data.providers.yahoo_historical.yf.Ticker",
        FakeTicker,
    )

    with pytest.raises(ValueError):
        provider.fetch_daily(
            exchange="NSE",
            symbol="RELIANCE",
            start_date=date(2026, 1, 5),
            end_date=date(2026, 1, 7),
        )


def test_fetch_daily_propagates_yahoo_errors(
    provider, monkeypatch
):
    class FakeTicker:
        def __init__(self, symbol):
            pass

        def history(self, **kwargs):
            raise RuntimeError("Yahoo Finance unavailable")

    monkeypatch.setattr(
        "app.data.providers.yahoo_historical.yf.Ticker",
        FakeTicker,
    )

    with pytest.raises(RuntimeError, match="Yahoo Finance unavailable"):
        provider.fetch_daily(
            exchange="NSE",
            symbol="RELIANCE",
            start_date=date(2026, 1, 5),
            end_date=date(2026, 1, 7),
        )
