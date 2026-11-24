
from datetime import date

import pandas as pd
import pytest

from app.backtesting.engine import run_backtest
from app.backtesting.models import BacktestConfig


@pytest.fixture
def sample_data():
    return pd.DataFrame({
        "date": [
            date(2025, 1, 1),
            date(2025, 1, 2),
            date(2025, 1, 3),
            date(2025, 1, 6),
            date(2025, 1, 7),
        ],
        "open":   [10, 10, 10, 12, 14],
        "high":   [11, 11, 12, 13, 15],
        "low":    [9, 9, 9, 11, 13],
        "close":  [10, 10, 11, 12, 15],
        "volume": [100, 100, 100, 100, 100],
    })


def test_buy_and_sell_execute_next_session(sample_data):
    def test_strategy(history):
        if len(history) == 2:
            return {"signal": "BUY"}
        if len(history) == 4:
            return {"signal": "SELL"}
        return {"signal": "HOLD"}

    result = run_backtest(
        sample_data,
        "TEST",
        strategy=test_strategy,
        config=BacktestConfig(initial_cash=1000),
    )

    assert len(result.trades) == 1

    trade = result.trades[0]

    # BUY signal on Jan 2 -> execution at Jan 3 open.
    assert trade.entry_date == date(2025, 1, 3)
    assert trade.entry_price == 10

    # SELL signal on Jan 6 -> execution at Jan 7 open.
    assert trade.exit_date == date(2025, 1, 7)
    assert trade.exit_price == 14

    assert trade.quantity == 95
    assert trade.gross_pnl == 380
    assert trade.net_pnl == 380

    assert result.final_equity == 1380
    assert result.total_return_pct == pytest.approx(38.0)


def test_signal_on_last_day_is_not_executed(sample_data):
    def test_strategy(history):
        if len(history) == len(sample_data):
            return {"signal": "BUY"}
        return {"signal": "HOLD"}

    result = run_backtest(
        sample_data,
        "TEST",
        strategy=test_strategy,
        config=BacktestConfig(initial_cash=1000),
    )

    # No following session exists for execution.
    assert len(result.trades) == 0
    assert result.final_equity == 1000


def test_hold_signals_create_no_trades(sample_data):
    def hold_strategy(history):
        return {"signal": "HOLD"}

    result = run_backtest(
        sample_data,
        "TEST",
        strategy=hold_strategy,
    )

    assert len(result.trades) == 0
    assert result.final_equity == 100_000
    assert len(result.equity_curve) == len(sample_data)


def test_empty_dataframe_rejected():
    empty = pd.DataFrame(
        columns=["date", "open", "high", "low", "close", "volume"]
    )

    with pytest.raises(ValueError, match="empty"):
        run_backtest(empty, "TEST")
