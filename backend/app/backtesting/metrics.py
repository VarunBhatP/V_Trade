
import math

import numpy as np

from app.backtesting.models import BacktestResult


def calculate_performance_metrics(
    result: BacktestResult,
    risk_free_rate: float = 0.0,
) -> dict:
    """
    Calculate performance metrics from a completed backtest.

    risk_free_rate is an annual decimal rate.
    Example: 0.06 means 6% annually.
    """

    if not math.isfinite(risk_free_rate) or risk_free_rate < 0:
        raise ValueError("risk_free_rate must be a non-negative finite number")

    if not result.equity_curve:
        raise ValueError("Equity curve cannot be empty")

    equity = np.array(
        [point.equity for point in result.equity_curve],
        dtype=float,
    )

    if not np.isfinite(equity).all() or (equity <= 0).any():
        raise ValueError("Equity values must be positive and finite")

    # Daily portfolio returns.
    daily_returns = np.diff(equity) / equity[:-1]

    # CAGR: annualized growth based on calendar time.
    first_date = result.equity_curve[0].date
    last_date = result.equity_curve[-1].date
    elapsed_days = (last_date - first_date).days

    cagr = None
    if elapsed_days > 0:
        years = elapsed_days / 365.25
        cagr = (
            (equity[-1] / result.initial_cash) ** (1 / years) - 1
        ) * 100

    # Maximum drawdown.
    running_peak = np.maximum.accumulate(equity)
    drawdowns = (equity - running_peak) / running_peak
    max_drawdown_pct = abs(float(drawdowns.min())) * 100

    # Annualized Sharpe ratio using daily returns.
    sharpe_ratio = None

    if len(daily_returns) >= 2:
        daily_risk_free = (
            (1 + risk_free_rate) ** (1 / 252) - 1
        )

        excess_returns = daily_returns - daily_risk_free
        daily_std = float(np.std(excess_returns, ddof=1))

        if daily_std > 0:
            sharpe_ratio = (
                float(np.mean(excess_returns))
                / daily_std
            ) * np.sqrt(252)

    # Completed trade statistics.
    trades = result.trades
    total_trades = len(trades)

    winning_trades = [
        trade for trade in trades if trade.net_pnl > 0
    ]
    losing_trades = [
        trade for trade in trades if trade.net_pnl < 0
    ]

    win_rate_pct = (
        len(winning_trades) / total_trades * 100
        if total_trades else 0.0
    )

    gross_profit = sum(
        trade.net_pnl for trade in winning_trades
    )
    gross_loss = abs(sum(
        trade.net_pnl for trade in losing_trades
    ))

    profit_factor = (
        gross_profit / gross_loss
        if gross_loss > 0
        else None
    )

    average_trade_return_pct = (
        sum(trade.return_pct for trade in trades) / total_trades
        if total_trades else 0.0
    )

    return {
        "total_return_pct": result.total_return_pct,
        "cagr_pct": cagr,
        "max_drawdown_pct": max_drawdown_pct,
        "sharpe_ratio": sharpe_ratio,
        "total_trades": total_trades,
        "winning_trades": len(winning_trades),
        "losing_trades": len(losing_trades),
        "win_rate_pct": win_rate_pct,
        "profit_factor": profit_factor,
        "average_trade_return_pct": average_trade_return_pct,
    }
