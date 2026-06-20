"""Command-line interface: ``asts run ...`` and ``asts list``.

Examples
--------
    # Offline, reproducible synthetic backtest of the full 7-system suite
    asts run --suite suite7 --synthetic

    # A single system
    asts run --suite s1 --synthetic --stocks 60

    # Real data via yfinance (requires the optional `data` extra)
    asts run --suite suite6 --symbols AAPL,MSFT,NVDA,AMD,SPY \
        --start 2010-01-01 --end 2019-12-31
"""

from __future__ import annotations

import argparse
import sys

from .backtest import run_backtest
from .core.engine import BacktestConfig
from .metrics import format_metrics
from .systems import SYSTEM_REGISTRY, build_suite


def _build_universe(args):
    if args.synthetic or not args.symbols:
        from .data.synthetic import make_universe

        return make_universe(
            n_stocks=args.stocks,
            start=args.start,
            end=args.end,
            seed=args.seed,
            market_symbol=args.market,
        )
    from .data.yahoo import load_universe

    symbols = [s.strip().upper() for s in args.symbols.split(",") if s.strip()]
    if args.market not in symbols:
        symbols.append(args.market)
    return load_universe(symbols, args.start, args.end)


def cmd_run(args) -> int:
    systems = build_suite(args.suite)
    universe = _build_universe(args)
    if args.market not in universe:
        print(f"error: market symbol {args.market!r} not in universe", file=sys.stderr)
        return 2

    cfg = BacktestConfig(
        starting_equity=args.equity,
        slippage_pct=args.slippage / 100.0,
        commission_per_trade=args.commission,
    )
    print(f"Running '{args.suite}' on {len(universe)} symbols "
          f"({len(systems)} system(s))...")
    out = run_backtest(systems, universe, market_symbol=args.market, config=cfg)

    print()
    print(format_metrics(out.metrics))
    print(f"\nClosed trades: {len(out.trades)}")

    if args.csv:
        out.equity.to_csv(args.csv)
        print(f"Equity curve written to {args.csv}")
    if args.trades_csv:
        import pandas as pd

        pd.DataFrame([t.__dict__ for t in out.trades]).to_csv(args.trades_csv, index=False)
        print(f"Trade ledger written to {args.trades_csv}")
    return 0


def cmd_list(args) -> int:
    print("Systems:")
    for key, cls in SYSTEM_REGISTRY.items():
        print(f"  {key}: {cls.name}")
    print("\nSuites:")
    print("  suite3: Systems 1, 3 (long) + 2 (short)            [Chapter 7]")
    print("  suite6: Systems 1, 3, 4, 5 (long) + 2, 6 (short)   [Chapter 9]")
    print("  suite7: suite6 + System 7 catastrophe hedge        [Chapter 10]")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="asts", description="Automated Stock Trading Systems")
    sub = p.add_subparsers(dest="command", required=True)

    r = sub.add_parser("run", help="run a backtest")
    r.add_argument("--suite", default="suite7",
                   help="system key (s1..s7) or suite (suite3/suite6/suite7)")
    r.add_argument("--synthetic", action="store_true", help="use offline synthetic data")
    r.add_argument("--symbols", default="", help="comma-separated tickers (real data)")
    r.add_argument("--market", default="SPY", help="market/benchmark symbol")
    r.add_argument("--start", default="2005-01-01")
    r.add_argument("--end", default="2019-12-31")
    r.add_argument("--stocks", type=int, default=40, help="synthetic universe size")
    r.add_argument("--seed", type=int, default=0, help="synthetic RNG seed")
    r.add_argument("--equity", type=float, default=100_000.0)
    r.add_argument("--slippage", type=float, default=0.0, help="adverse slippage in percent")
    r.add_argument("--commission", type=float, default=0.0, help="flat $ per fill")
    r.add_argument("--csv", default="", help="write equity curve to CSV")
    r.add_argument("--trades-csv", default="", help="write trade ledger to CSV")
    r.set_defaults(func=cmd_run)

    ls = sub.add_parser("list", help="list available systems and suites")
    ls.set_defaults(func=cmd_list)
    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
