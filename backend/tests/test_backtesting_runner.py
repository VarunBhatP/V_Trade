
from datetime import date

import pandas as pd
import pytest

from app.backtesting.models import BacktestConfig
from app.backtesting.runner import run_backtest_report


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
        "open": [10, 10, 10, 12, 14],
        "high": [11, 11, 12, 13, 15],
        "low": [9, 9, 9, 11, 13],
        "close": [10, 10, 11, 12, 15],
        "volume": [100, 100, 100, 100, 100],
    })


def test_runner_returns_result_and_metrics(sample_data):
    def strategy(history):
        if len(history) == 2:
            return {"signal": "BUY"}
        if len(history) == 4:
            return {"signal": "SELL"}
        return {"signal": "HOLD"}

    report = run_backtest_report(
        df=sample_data,
        symbol="TEST",
        strategy=strategy,
        config=BacktestConfig(initial_cash=1000),
    )

    assert report.result.symbol == "TEST"
    assert len(report.result.trades) == 1
    assert report.result.final_equity == pytest.approx(1380)

    assert report.metrics["total_return_pct"] == pytest.approx(38)
    assert report.metrics["total_trades"] == 1
    assert report.metrics["winning_trades"] == 1
    assert report.metrics["win_rate_pct"] == 100


def test_runner_supports_no_trade_strategy(sample_data):
    def strategy(history):
        return {"signal": "HOLD"}

    report = run_backtest_report(
        df=sample_data,
        symbol="TEST",
        strategy=strategy,
    )

    assert report.result.trades == []
    assert report.metrics["total_trades"] == 0
    assert report.metrics["profit_factor"] is None
