import pandas as pd
import pytest

from app.data.loader import load_ohlcv_csv


def test_load_valid_csv(tmp_path):
    file_path = tmp_path / "valid.csv"

    pd.DataFrame({
        "date": ["2026-01-02", "2026-01-01"],
        "open": [105, 100],
        "high": [115, 110],
        "low": [100, 95],
        "close": [110, 105],
        "volume": [1200, 1000],
    }).to_csv(file_path, index=False)

    df = load_ohlcv_csv(file_path)

    assert len(df) == 2
    assert list(df.columns) == [
        "date", "open", "high", "low", "close", "volume"
    ]
    # Data should be sorted by date.
    assert df["date"].is_monotonic_increasing
    assert df.iloc[0]["close"] == 105


def test_missing_file():
    with pytest.raises(FileNotFoundError):
        load_ohlcv_csv("nonexistent.csv")


def test_missing_columns(tmp_path):
    file_path = tmp_path / "missing_columns.csv"

    pd.DataFrame({
        "date": ["2026-01-01"],
        "open": [100],
        "close": [105],
    }).to_csv(file_path, index=False)

    with pytest.raises(ValueError, match="Missing required columns"):
        load_ohlcv_csv(file_path)


def test_empty_csv(tmp_path):
    file_path = tmp_path / "empty.csv"
    file_path.write_text(
        "date,open,high,low,close,volume\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="empty"):
        load_ohlcv_csv(file_path)


def test_invalid_numeric_values(tmp_path):
    file_path = tmp_path / "invalid_numeric.csv"

    pd.DataFrame({
        "date": ["2026-01-01"],
        "open": ["invalid"],
        "high": [110],
        "low": [95],
        "close": [105],
        "volume": [1000],
    }).to_csv(file_path, index=False)

    with pytest.raises(ValueError, match="missing or invalid"):
        load_ohlcv_csv(file_path)


def test_negative_volume(tmp_path):
    file_path = tmp_path / "negative_volume.csv"

    pd.DataFrame({
        "date": ["2026-01-01"],
        "open": [100],
        "high": [110],
        "low": [95],
        "close": [105],
        "volume": [-100],
    }).to_csv(file_path, index=False)

    with pytest.raises(ValueError, match="Volume cannot be negative"):
        load_ohlcv_csv(file_path)


def test_invalid_ohlc_data(tmp_path):
    file_path = tmp_path / "invalid_ohlc.csv"

    pd.DataFrame({
        "date": ["2026-01-01"],
        "open": [100],
        "high": [90],
        "low": [95],
        "close": [105],
        "volume": [1000],
    }).to_csv(file_path, index=False)

    with pytest.raises(ValueError, match="high price"):
        load_ohlcv_csv(file_path)


def test_duplicate_dates(tmp_path):
    file_path = tmp_path / "duplicate.csv"

    pd.DataFrame({
        "date": ["2026-01-01", "2026-01-01"],
        "open": [100, 105],
        "high": [110, 115],
        "low": [95, 100],
        "close": [105, 110],
        "volume": [1000, 1200],
    }).to_csv(file_path, index=False)

    with pytest.raises(ValueError, match="Duplicate dates"):
        load_ohlcv_csv(file_path)