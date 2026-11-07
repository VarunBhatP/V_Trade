
import pandas as pd


def calculate_sma(prices: pd.Series, period: int) -> pd.Series:
    if period <= 0:
        raise ValueError("Period must be positive")

    return prices.rolling(
        window=period,
        min_periods=period,
    ).mean()


def calculate_rsi(prices: pd.Series, period: int = 14) -> pd.Series:
    if period <= 0:
        raise ValueError("Period must be positive")

    delta = prices.diff()

    gains = delta.clip(lower=0)
    losses = -delta.clip(upper=0)

    avg_gain = gains.ewm(
        alpha=1 / period,
        min_periods=period,
        adjust=False,
    ).mean()

    avg_loss = losses.ewm(
        alpha=1 / period,
        min_periods=period,
        adjust=False,
    ).mean()

    relative_strength = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + relative_strength))

    # Handle periods with no losses or no price movement.
    rsi = rsi.mask((avg_loss == 0) & (avg_gain > 0), 100)
    rsi = rsi.mask((avg_loss == 0) & (avg_gain == 0), 50)

    return rsi


def calculate_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    if period <= 0:
        raise ValueError("Period must be positive")

    required = {"high", "low", "close"}
    if not required.issubset(df.columns):
        raise ValueError(f"Data must contain: {sorted(required)}")

    previous_close = df["close"].shift(1)

    true_range = pd.concat(
        [
            df["high"] - df["low"],
            (df["high"] - previous_close).abs(),
            (df["low"] - previous_close).abs(),
        ],
        axis=1,
    ).max(axis=1)

    return true_range.ewm(
        alpha=1 / period,
        min_periods=period,
        adjust=False,
    ).mean()
