
from dataclasses import dataclass

import pandas as pd

from app.backtesting.engine import run_backtest
from app.backtesting.metrics import calculate_performance_metrics
from app.backtesting.models import BacktestConfig, BacktestResult


@dataclass
class BacktestReport:
    """Backtest output with its calculated performance metrics."""

    result: BacktestResult
    metrics: dict


def run_backtest_report(
    df: pd.DataFrame,
    symbol: str,
    strategy=None,
    config: BacktestConfig | None = None,
    risk_free_rate: float = 0.0,
) -> BacktestReport:
    """Run a backtest and calculate its performance metrics."""

    result = run_backtest(
        df=df,
        symbol=symbol,
        strategy=strategy,
        config=config,
    )

    metrics = calculate_performance_metrics(
        result=result,
        risk_free_rate=risk_free_rate,
    )

    return BacktestReport(
        result=result,
        metrics=metrics,
    )
