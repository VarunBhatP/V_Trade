
import pandas as pd

from app.data.indicators import calculate_sma, calculate_rsi, calculate_atr


def test_sma():
    result = calculate_sma(pd.Series([10, 20, 30, 40]), 2)
    assert result.iloc[1] == 15


def test_rsi_range():
    prices = pd.Series([100 + i for i in range(30)])
    result = calculate_rsi(prices)

    assert result.dropna().between(0, 100).all()


def test_atr_positive():
    df = pd.DataFrame({
        "high": [110.0] * 20,
        "low": [90.0] * 20,
        "close": [100.0] * 20,
    })

    result = calculate_atr(df)

    assert (result.dropna() >= 0).all()
