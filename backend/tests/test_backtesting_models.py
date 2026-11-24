
from datetime import date

import pytest

from app.backtesting.models import (
    BacktestConfig,
    BacktestResult,
    EquityPoint,
    Trade,
)


def test_default_backtest_config():
    config = BacktestConfig()

    assert config.initial_cash == 100_000
    assert config.allocation_pct == 0.95
    assert config.slippage_bps == 0
    assert config.transaction_cost_bps == 0


def test_custom_backtest_config():
    config = BacktestConfig(
        initial_cash=50_000,
        allocation_pct=0.8,
        slippage_bps=5,
        transaction_cost_bps=10,
    )

    assert config.initial_cash == 50_000
    assert config.allocation_pct == 0.8
    assert config.slippage_bps == 5
    assert config.transaction_cost_bps == 10


@pytest.mark.parametrize("cash", [0, -100, float("inf"), float("nan")])
def test_invalid_initial_cash(cash):
    with pytest.raises(ValueError):
        BacktestConfig(initial_cash=cash)


@pytest.mark.parametrize("allocation", [0, -0.1, 1.1, float("nan")])
def test_invalid_allocation(allocation):
    with pytest.raises(ValueError):
        BacktestConfig(allocation_pct=allocation)


@pytest.mark.parametrize("cost", [-1, float("nan"), float("inf")])
def test_invalid_slippage(cost):
    with pytest.raises(ValueError):
        BacktestConfig(slippage_bps=cost)


def test_trade_creation():
    trade = Trade(
        symbol="RELIANCE",
        entry_date=date(2025, 1, 2),
        exit_date=date(2025, 1, 10),
        entry_price=1200,
        exit_price=1250,
        quantity=10,
        entry_fees=5,
        exit_fees=5,
        gross_pnl=500,
        net_pnl=490,
        return_pct=4.08,
        exit_reason="SELL_SIGNAL",
    )

    assert trade.quantity == 10
    assert trade.net_pnl == 490


def test_equity_point_creation():
    point = EquityPoint(
        date=date(2025, 1, 2),
        cash=50_000,
        market_value=50_000,
        equity=100_000,
        position_qty=40,
        close=1250,
    )

    assert point.equity == point.cash + point.market_value


def test_backtest_result_default_lists_are_independent():
    first = BacktestResult("RELIANCE", "trend_following", 100_000, 100_000, 0)
    second = BacktestResult("ABB", "trend_following", 100_000, 100_000, 0)

    first.trades.append(
        Trade(
            symbol="RELIANCE",
            entry_date=date(2025, 1, 2),
            exit_date=date(2025, 1, 3),
            entry_price=100,
            exit_price=110,
            quantity=10,
            entry_fees=0,
            exit_fees=0,
            gross_pnl=100,
            net_pnl=100,
            return_pct=10,
            exit_reason="SELL_SIGNAL",
        )
    )

    assert len(first.trades) == 1
    assert len(second.trades) == 0
