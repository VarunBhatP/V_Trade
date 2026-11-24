
from dataclasses import dataclass, field
from datetime import date
import math


@dataclass(frozen=True)
class BacktestConfig:
    """Configuration for one backtesting run."""

    initial_cash: float = 100_000.0
    allocation_pct: float = 0.95
    slippage_bps: float = 0.0
    transaction_cost_bps: float = 0.0

    def __post_init__(self):
        if not math.isfinite(self.initial_cash) or self.initial_cash <= 0:
            raise ValueError("initial_cash must be a positive finite number")

        if (
            not math.isfinite(self.allocation_pct)
            or not 0 < self.allocation_pct <= 1
        ):
            raise ValueError("allocation_pct must be between 0 and 1")

        if not math.isfinite(self.slippage_bps) or self.slippage_bps < 0:
            raise ValueError("slippage_bps cannot be negative")

        if (
            not math.isfinite(self.transaction_cost_bps)
            or self.transaction_cost_bps < 0
        ):
            raise ValueError("transaction_cost_bps cannot be negative")


@dataclass
class Trade:
    """A completed long-only trade."""

    symbol: str
    entry_date: date
    exit_date: date
    entry_price: float
    exit_price: float
    quantity: int
    entry_fees: float
    exit_fees: float
    gross_pnl: float
    net_pnl: float
    return_pct: float
    exit_reason: str


@dataclass
class EquityPoint:
    """Portfolio valuation at the end of a trading session."""

    date: date
    cash: float
    market_value: float
    equity: float
    position_qty: int
    close: float


@dataclass
class BacktestResult:
    """Complete output of a backtesting run."""

    symbol: str
    strategy: str
    initial_cash: float
    final_equity: float
    total_return_pct: float
    trades: list[Trade] = field(default_factory=list)
    equity_curve: list[EquityPoint] = field(default_factory=list)
    buy_signals: int = 0
    sell_signals: int = 0
