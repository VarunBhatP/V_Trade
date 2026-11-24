
from pathlib import Path

from app.backtesting.models import BacktestConfig
from app.backtesting.runner import run_backtest_report
from app.data.loader import load_ohlcv_csv


PROJECT_ROOT = Path(__file__).resolve().parents[1]

DATA_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "yahoo_20y"
    / "NSE_RELIANCE.csv"
)

def main():
    if not DATA_FILE.exists():
        raise FileNotFoundError(f"Historical data not found: {DATA_FILE}")

    df = load_ohlcv_csv(DATA_FILE)

    print("\n========== INPUT DATA ==========")
    print(f"Symbol: RELIANCE")
    print(f"Candles: {len(df)}")
    print(f"First date: {df['date'].iloc[0]}")
    print(f"Last date: {df['date'].iloc[-1]}")

    config = BacktestConfig(
        initial_cash=100_000,
        allocation_pct=0.95,
        slippage_bps=0,
        transaction_cost_bps=0,
    )

    report = run_backtest_report(
        df=df,
        symbol="RELIANCE",
        config=config,
    )

    result = report.result
    metrics = report.metrics

    print("\n========== BACKTEST RESULTS ==========")
    print(f"Strategy: {result.strategy}")
    print(f"Initial cash: ₹{result.initial_cash:,.2f}")
    print(f"Final equity: ₹{result.final_equity:,.2f}")
    print(f"Total return: {result.total_return_pct:.2f}%")

    print("\n========== PERFORMANCE METRICS ==========")

    for name, value in metrics.items():
        if value is None:
            print(f"{name}: N/A")
        elif isinstance(value, float):
            print(f"{name}: {value:.4f}")
        else:
            print(f"{name}: {value}")

    print("\n========== TRADE SUMMARY ==========")
    print(f"Completed trades: {len(result.trades)}")
    print(f"BUY signals: {result.buy_signals}")
    print(f"SELL signals: {result.sell_signals}")

    if result.trades:
        print("\nFirst 5 trades:")
        for trade in result.trades[:5]:
            print(
                f"{trade.entry_date} -> {trade.exit_date} | "
                f"Buy: ₹{trade.entry_price:.2f} | "
                f"Sell: ₹{trade.exit_price:.2f} | "
                f"Qty: {trade.quantity} | "
                f"Net P&L: ₹{trade.net_pnl:.2f}"
            )

        print("\nLast 5 trades:")
        for trade in result.trades[-5:]:
            print(
                f"{trade.entry_date} -> {trade.exit_date} | "
                f"Net P&L: ₹{trade.net_pnl:.2f}"
            )

    last_point = result.equity_curve[-1]

    print("\n========== FINAL POSITION ==========")
    print(f"Cash: ₹{last_point.cash:,.2f}")
    print(f"Shares held: {last_point.position_qty}")
    print(f"Market value: ₹{last_point.market_value:,.2f}")
    print(f"Final equity: ₹{last_point.equity:,.2f}")


if __name__ == "__main__":
    main()
