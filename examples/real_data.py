"""Run a suite on real market data via yfinance (needs the ``data`` extra).

    pip install -e ".[data,plot]"
    python examples/real_data.py

Downloads are cached under ``data/cache/`` as Parquet, so repeat runs are fast
and offline. Edit ``TICKERS`` to taste; ``SPY`` is required as the benchmark and
the catastrophe-hedge instrument.

Survivorship-bias caveat: a hand-picked list of today's liquid names is *not*
the point-in-time universe the book backtests. Treat results as illustrative.
"""

from __future__ import annotations

import warnings

from asts.backtest import run_backtest
from asts.core.engine import BacktestConfig
from asts.metrics import format_metrics
from asts.systems import build_suite

warnings.filterwarnings("ignore")

TICKERS = [
    "SPY",  # benchmark + hedge (required)
    "AAPL", "MSFT", "NVDA", "AMD", "AMZN", "GOOGL", "META", "TSLA",
    "JPM", "BAC", "XOM", "CVX", "JNJ", "PFE", "KO", "PG",
    "HD", "WMT", "DIS", "NFLX", "INTC", "CSCO", "ORCL", "QCOM",
]

START, END = "2012-01-01", "2021-12-31"


def main() -> None:
    from asts.data.yahoo import load_universe

    print(f"Downloading {len(TICKERS)} tickers ({START} → {END})...")
    universe = load_universe(TICKERS, START, END)
    if "SPY" not in universe:
        raise SystemExit("SPY download failed — cannot run (needed as benchmark/hedge).")

    cfg = BacktestConfig(starting_equity=100_000, slippage_pct=0.001)
    out = run_backtest(build_suite("suite6"), universe, market_symbol="SPY", config=cfg)
    print()
    print(format_metrics(out.metrics))
    print(f"\nClosed trades: {len(out.trades)}")

    try:
        from asts.plotting import plot_tearsheet

        bench = universe["SPY"]["close"]
        plot_tearsheet(out.equity, benchmark=bench, title="ASTS suite6 — real data",
                       savepath="results/real_data_tearsheet.png")
        print("Tear sheet -> results/real_data_tearsheet.png")
    except Exception as exc:  # plotting is optional
        print(f"(skipped plot: {exc})")


if __name__ == "__main__":
    main()
