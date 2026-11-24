
import math
from typing import Callable

import pandas as pd

from app.backtesting.models import (
    BacktestConfig,
    BacktestResult,
    EquityPoint,
    Trade,
)


REQUIRED_COLUMNS = {
    "date", "open", "high", "low", "close", "volume"
}


def run_backtest(
    df: pd.DataFrame,
    symbol: str,
    strategy: Callable[[pd.DataFrame], dict] | None = None,
    config: BacktestConfig | None = None,
) -> BacktestResult:
    """
    Run a single-stock, long-only daily backtest.

    Signals are generated after each session's close and
    executed at the next available session's open.
    """

    from app.strategies.trend_following import generate_trend_signal

    if strategy is None:
        strategy = generate_trend_signal

    if config is None:
        config = BacktestConfig()

    if df.empty:
        raise ValueError("Cannot backtest an empty DataFrame")

    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(f"Missing columns: {sorted(missing)}")

    data = df.copy().reset_index(drop=True)

    data["date"] = pd.to_datetime(data["date"], errors="coerce")
    if data["date"].isna().any():
        raise ValueError("Invalid dates in backtesting data")

    if data["date"].duplicated().any():
        raise ValueError("Duplicate dates in backtesting data")

    if not data["date"].is_monotonic_increasing:
        raise ValueError("Backtesting data must be sorted by date")

    for column in ["open", "high", "low", "close", "volume"]:
        data[column] = pd.to_numeric(data[column], errors="coerce")

        if not data[column].map(
            lambda value: math.isfinite(value) if pd.notna(value) else False
        ).all():
            raise ValueError(f"Invalid numeric values in {column}")

    if (data[["open", "high", "low", "close"]] <= 0).any().any():
        raise ValueError("OHLC prices must be positive")

    if (data["volume"] < 0).any():
        raise ValueError("Volume cannot be negative")

    if (
        (data["high"] < data[["open", "close", "low"]].max(axis=1))
        | (data["low"] > data[["open", "close", "high"]].min(axis=1))
    ).any():
        raise ValueError("Inconsistent OHLC data")

    cash = config.initial_cash
    quantity = 0

    entry_date = None
    entry_price = 0.0
    entry_fees = 0.0

    trades = []
    equity_curve = []

    buy_signals = 0
    sell_signals = 0

    pending_signal = None

    fee_rate = config.transaction_cost_bps / 10_000
    slippage_rate = config.slippage_bps / 10_000

    for index, row in data.iterrows():

        current_date = row["date"].date()

        # Execute the previous session's signal at today's open.
        if index > 0 and pending_signal is not None:

            execution_price = float(row["open"])

            if pending_signal == "BUY" and quantity == 0:

                execution_price *= 1 + slippage_rate

                affordable_cash = cash * config.allocation_pct

                quantity_to_buy = math.floor(
                    affordable_cash
                    / (execution_price * (1 + fee_rate))
                )

                if quantity_to_buy > 0:
                    notional = quantity_to_buy * execution_price
                    fees = notional * fee_rate

                    cash -= notional + fees
                    cash = max(cash, 0.0)

                    quantity = quantity_to_buy
                    entry_date = current_date
                    entry_price = execution_price
                    entry_fees = fees

            elif pending_signal == "SELL" and quantity > 0:

                execution_price *= 1 - slippage_rate

                notional = quantity * execution_price
                exit_fees = notional * fee_rate

                cash += notional - exit_fees

                gross_pnl = (
                    execution_price - entry_price
                ) * quantity

                net_pnl = gross_pnl - entry_fees - exit_fees

                invested_amount = (
                    entry_price * quantity + entry_fees
                )

                return_pct = (
                    net_pnl / invested_amount
                ) * 100

                trades.append(
                    Trade(
                        symbol=symbol,
                        entry_date=entry_date,
                        exit_date=current_date,
                        entry_price=entry_price,
                        exit_price=execution_price,
                        quantity=quantity,
                        entry_fees=entry_fees,
                        exit_fees=exit_fees,
                        gross_pnl=gross_pnl,
                        net_pnl=net_pnl,
                        return_pct=return_pct,
                        exit_reason="SELL_SIGNAL",
                    )
                )

                quantity = 0
                entry_date = None
                entry_price = 0.0
                entry_fees = 0.0

        # Value the portfolio at today's closing price.
        close_price = float(row["close"])
        market_value = quantity * close_price
        equity = cash + market_value

        equity_curve.append(
            EquityPoint(
                date=current_date,
                cash=cash,
                market_value=market_value,
                equity=equity,
                position_qty=quantity,
                close=close_price,
            )
        )

        # Generate today's signal using data available up to today's close.
        signal_result = strategy(data.iloc[:index + 1].copy())

        signal = signal_result.get("signal")

        if signal not in {
            "BUY", "SELL", "HOLD", "INSUFFICIENT_DATA"
        }:
            raise ValueError(f"Unsupported strategy signal: {signal}")

        if signal == "BUY":
            buy_signals += 1
        elif signal == "SELL":
            sell_signals += 1

        pending_signal = signal

    final_equity = equity_curve[-1].equity

    total_return_pct = (
        (final_equity - config.initial_cash)
        / config.initial_cash
    ) * 100

    return BacktestResult(
        symbol=symbol,
        strategy=getattr(strategy, "__name__", "custom_strategy"),
        initial_cash=config.initial_cash,
        final_equity=final_equity,
        total_return_pct=total_return_pct,
        trades=trades,
        equity_curve=equity_curve,
        buy_signals=buy_signals,
        sell_signals=sell_signals,
    )
