
from datetime import date

import pandas as pd
import pytest

from app.data.providers.csv_historical import CsvHistoricalProvider


@pytest.fixture
def sample_csv(tmp_path):
    df = pd.DataFrame({
        "date": ["2026-11-03", "2026-11-05", "2026-11-06"],
        "open": [100, 110, 120],
        "high": [105, 115, 125],
        "low": [98, 108, 118],
        "close": [103, 113, 123],
        "volume": [1000, 1200, 1500],
    })

    df.to_csv(tmp_path / "NSE_RELIANCE.csv", index=False)
    return tmp_path


def test_fetch_daily_returns_requested_date_range(sample_csv):
    provider = CsvHistoricalProvider(sample_csv)

    df = provider.fetch_daily(
        exchange="NSE",
        symbol="RELIANCE",
        start_date=date(2026, 11, 4),
        end_date=date(2026, 11, 6),
    )

    assert len(df) == 2
    assert df["close"].tolist() == [113, 123]


def test_fetch_daily_returns_empty_range(sample_csv):
    provider = CsvHistoricalProvider(sample_csv)

    df = provider.fetch_daily(
        exchange="NSE",
        symbol="RELIANCE",
        start_date=date(2026, 11, 1),
        end_date=date(2026, 11, 2),
    )

    assert df.empty
    assert list(df.columns) == [
        "date", "open", "high", "low", "close", "volume"
    ]


def test_missing_file_is_rejected(tmp_path):
    provider = CsvHistoricalProvider(tmp_path)

    with pytest.raises(FileNotFoundError):
        provider.fetch_daily(
            exchange="NSE",
            symbol="UNKNOWN",
            start_date=date(2026, 11, 1),
            end_date=date(2026, 11, 6),
        )


def test_unsupported_exchange_is_rejected(tmp_path):
    provider = CsvHistoricalProvider(tmp_path)

    with pytest.raises(ValueError, match="Only NSE and BSE"):
        provider.fetch_daily(
            exchange="MCX",
            symbol="RELIANCE",
            start_date=date(2026, 11, 1),
            end_date=date(2026, 11, 6),
        )


def test_invalid_date_range_is_rejected(sample_csv):
    provider = CsvHistoricalProvider(sample_csv)

    with pytest.raises(ValueError, match="start_date"):
        provider.fetch_daily(
            exchange="NSE",
            symbol="RELIANCE",
            start_date=date(2026, 11, 7),
            end_date=date(2026, 11, 5),
        )


def test_legacy_nse_filename_is_supported(tmp_path):
    df = pd.DataFrame({
        "date": ["2026-11-05"],
        "open": [100],
        "high": [105],
        "low": [98],
        "close": [103],
        "volume": [1000],
    })

    df.to_csv(tmp_path / "RELIANCE.csv", index=False)

    provider = CsvHistoricalProvider(tmp_path)

    result = provider.fetch_daily(
        exchange="NSE",
        symbol="RELIANCE",
        start_date=date(2026, 11, 5),
        end_date=date(2026, 11, 5),
    )

    assert len(result) == 1
    assert result.iloc[0]["close"] == 103
