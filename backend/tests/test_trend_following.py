
import pandas as pd

from app.strategies.trend_following import (
    calculate_sma,
    generate_trend_signal,
)


def test_sma():
    prices = pd.Series([10, 20, 30, 40, 50])
    result = calculate_sma(prices, 3)

    assert result.iloc[2] == 20
    assert result.iloc[4] == 40


def test_insufficient_data():
    df = pd.DataFrame({"close": [100.0] * 100})
    result = generate_trend_signal(df)

    assert result["signal"] == "INSUFFICIENT_DATA"


def test_buy_signal():
    prices = [100.0] * 200 + [150.0] * 49 + [200.0]
    df = pd.DataFrame({"close": prices})

    result = generate_trend_signal(df)

    assert result["signal"] == "BUY"


def test_sell_signal():
    prices = [100.0] * 249 + [80.0]
    df = pd.DataFrame({"close": prices})

    result = generate_trend_signal(df)

    assert result["signal"] == "SELL"
