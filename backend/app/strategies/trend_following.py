
import pandas as pd

from app.data.indicators import calculate_sma


def generate_trend_signal(df: pd.DataFrame) -> dict:
    if "close" not in df.columns:
        raise ValueError("Data must contain a close column")

    if df.empty:
        raise ValueError("Market data is empty")

    data = df.copy()
    data["sma_50"] = calculate_sma(data["close"], 50)
    data["sma_200"] = calculate_sma(data["close"], 200)

    latest = data.iloc[-1]

    if pd.isna(latest["sma_50"]) or pd.isna(latest["sma_200"]):
        return {
            "signal": "INSUFFICIENT_DATA",
            "reason": "At least 200 trading days are required",
        }

    close = float(latest["close"])
    sma_50 = float(latest["sma_50"])
    sma_200 = float(latest["sma_200"])

    if close > sma_50 and close > sma_200:
        signal = "BUY"
        reason = "Price is above both moving averages"
    elif close < sma_50:
        signal = "SELL"
        reason = "Price has fallen below the 50-day SMA"
    else:
        signal = "HOLD"
        reason = "No new entry or exit condition is met"

    return {
        "signal": signal,
        "reason": reason,
        "close": round(close, 2),
        "sma_50": round(sma_50, 2),
        "sma_200": round(sma_200, 2),
        "date": str(latest["date"]) if "date" in data.columns else None,
    }
