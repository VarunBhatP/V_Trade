
from datetime import date

import pytest

from app.backtesting.metrics import calculate_performance_metrics
from app.backtesting.models import (
    BacktestResult,
    EquityPoint,
    Trade,
)


def make_result(equity_values, trades=None):
    dates = [
        date(2025, 1, 1),
        date(2025, 1, 2),
        date(2025, 1, 3),
        date(2025, 1, 4),
    ]

    points = [
        EquityPoint(
            date=dates[index],
            cash=value,
            market_value=0,
            equity=value,
            position_qty=0,
            close=value,
        )
        for index, value in enumerate(equity_values)
    ]

    final_equity = equity_values[-1]

    return BacktestResult(
        symbol="TEST",
        strategy="test_strategy",
        initial_cash=equity_values[0],
        final_equity=final_equity,
        total_return_pct=(
            (final_equity / equity_values[0]) - 1
        ) * 100,
        trades=trades or [],
        equity_curve=points,
    )


def test_total_return():
    result = make_result([100_000, 105_000, 110_000, 120_000])

    metrics = calculate_performance_metrics(result)

    assert metrics["total_return_pct"] == pytest.approx(20.0)


def test_max_drawdown():
    result = make_result([100_000, 120_000, 90_000, 110_000])

    metrics = calculate_performance_metrics(result)

    assert metrics["max_drawdown_pct"] == pytest.approx(25.0)


def test_sharpe_ratio_with_constant_equity():
    result = make_result([100_000, 100_000, 100_000, 100_000])

    metrics = calculate_performance_metrics(result)

    assert metrics["sharpe_ratio"] is None


def test_win_rate_and_profit_factor():
    trades = [
        Trade(
            "TEST", date(2025, 1, 1), date(2025, 1, 2),
            100, 110, 10, 0, 0, 100, 100, 10, "SELL_SIGNAL",
        ),
        Trade(
            "TEST", date(2025, 1, 2), date(2025, 1, 3),
            100, 90, 10, 0, 0, -100, -100, -10, "SELL_SIGNAL",
        ),
        Trade(
            "TEST", date(2025, 1, 3), date(2025, 1, 4),
            100, 120, 10, 0, 0, 200, 200, 20, "SELL_SIGNAL",
        ),
    ]

    result = make_result(
        [100_000, 101_000, 102_000, 103_000],
        trades,
    )

    metrics = calculate_performance_metrics(result)

    assert metrics["total_trades"] == 3
    assert metrics["winning_trades"] == 2
    assert metrics["losing_trades"] == 1
    assert metrics["win_rate_pct"] == pytest.approx(66.6667)
    assert metrics["profit_factor"] == pytest.approx(3.0)
    assert metrics["average_trade_return_pct"] == pytest.approx(20 / 3)


def test_no_trades():
    result = make_result([100_000, 101_000, 102_000, 103_000])

    metrics = calculate_performance_metrics(result)

    assert metrics["total_trades"] == 0
    assert metrics["win_rate_pct"] == 0
    assert metrics["profit_factor"] is None


def test_empty_equity_curve_rejected():
    result = BacktestResult(
        "TEST", "test_strategy", 100_000, 100_000, 0
    )

    with pytest.raises(ValueError, match="empty"):
        calculate_performance_metrics(result)


def test_invalid_risk_free_rate_rejected():
    result = make_result([100_000, 101_000, 102_000, 103_000])

    with pytest.raises(ValueError, match="risk_free_rate"):
        calculate_performance_metrics(result, risk_free_rate=-0.01)
