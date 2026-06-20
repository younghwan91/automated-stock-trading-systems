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
    if args.plot:
        import pandas as pd

        from .plotting import plot_tearsheet

        benchmark = universe[args.market]["close"].copy()
        benchmark.index = pd.to_datetime(benchmark.index)
        plot_tearsheet(out.equity, benchmark=benchmark, title=f"ASTS — {args.suite}",
                       savepath=args.plot)
        print(f"Tear sheet written to {args.plot}")
    return 0


def cmd_montecarlo(args) -> int:
    from .analysis import monte_carlo_equity

    systems = build_suite(args.suite)
    universe = _build_universe(args)
    out = run_backtest(systems, universe, market_symbol=args.market)
    if not out.trades:
        print("No trades generated; cannot run Monte Carlo.", file=sys.stderr)
        return 1
    mc = monte_carlo_equity(
        out.equity, n_sims=args.sims, method=args.method, block=args.block, seed=args.seed
    )
    print(f"Backtest '{args.suite}': realised CAGR {out.metrics.cagr_pct}%, "
          f"maxDD {out.metrics.max_drawdown_pct}%\n")
    print(mc.summary())
    return 0


def cmd_sensitivity(args) -> int:
    from .analysis.sensitivity import format_sweep, run_sizing_sweep

    universe = _build_universe(args)
    risk_grid = [float(x) for x in args.risk_grid.split(",")]
    size_grid = [float(x) for x in args.size_grid.split(",")]
    print(f"Sizing sweep for '{args.suite}' "
          f"({len(risk_grid)}×{len(size_grid)} grid)...\n")
    df = run_sizing_sweep(args.suite, universe, risk_grid, size_grid, market_symbol=args.market)
    print(format_sweep(df))
    if args.csv:
        df.to_csv(args.csv, index=False)
        print(f"\nFull grid written to {args.csv}")
    return 0


def cmd_walkforward(args) -> int:
    from .analysis import walk_forward

    universe = _build_universe(args)
    risk_grid = [float(x) for x in args.risk_grid.split(",")]
    print(f"Walk-forward for '{args.suite}' "
          f"(IS {args.is_years}y / OOS {args.oos_years}y)...\n")
    wf = walk_forward(
        args.suite, universe, market_symbol=args.market,
        is_years=args.is_years, oos_years=args.oos_years,
        risk_grid=risk_grid, objective=args.objective,
    )
    print(wf.summary())
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


def _add_data_args(sp, default_suite="suite7"):
    """Shared data-selection arguments for every command that needs a universe."""
    sp.add_argument("--suite", default=default_suite,
                    help="system key (s1..s7) or suite (suite3/suite6/suite7)")
    sp.add_argument("--synthetic", action="store_true", help="use offline synthetic data")
    sp.add_argument("--symbols", default="", help="comma-separated tickers (real data)")
    sp.add_argument("--market", default="SPY", help="market/benchmark symbol")
    sp.add_argument("--start", default="2005-01-01")
    sp.add_argument("--end", default="2019-12-31")
    sp.add_argument("--stocks", type=int, default=40, help="synthetic universe size")
    sp.add_argument("--seed", type=int, default=0, help="synthetic RNG seed")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="asts", description="Automated Stock Trading Systems")
    sub = p.add_subparsers(dest="command", required=True)

    r = sub.add_parser("run", help="run a backtest")
    _add_data_args(r)
    r.add_argument("--equity", type=float, default=100_000.0)
    r.add_argument("--slippage", type=float, default=0.0, help="adverse slippage in percent")
    r.add_argument("--commission", type=float, default=0.0, help="flat $ per fill")
    r.add_argument("--csv", default="", help="write equity curve to CSV")
    r.add_argument("--trades-csv", default="", help="write trade ledger to CSV")
    r.add_argument("--plot", default="", help="write a PNG/SVG tear sheet to this path")
    r.set_defaults(func=cmd_run)

    mc = sub.add_parser("montecarlo", help="Monte Carlo resampling of the equity curve")
    _add_data_args(mc)
    mc.add_argument("--sims", type=int, default=2000, help="number of simulations")
    mc.add_argument("--method", default="block", choices=["block", "iid"])
    mc.add_argument("--block", type=int, default=10, help="block size (block bootstrap)")
    mc.set_defaults(func=cmd_montecarlo)

    se = sub.add_parser("sensitivity", help="position-sizing sensitivity sweep (Ch. 5)")
    _add_data_args(se, default_suite="suite6")
    se.add_argument("--risk-grid", default="0.005,0.01,0.02,0.03,0.05")
    se.add_argument("--size-grid", default="0.05,0.10,0.20")
    se.add_argument("--csv", default="", help="write the full grid to CSV")
    se.set_defaults(func=cmd_sensitivity)

    wf = sub.add_parser("walkforward", help="walk-forward optimization & OOS validation")
    _add_data_args(wf, default_suite="suite6")
    wf.add_argument("--is-years", type=float, default=4.0, help="in-sample window (years)")
    wf.add_argument("--oos-years", type=float, default=2.0, help="out-of-sample window (years)")
    wf.add_argument("--risk-grid", default="0.005,0.01,0.02,0.03,0.05")
    wf.add_argument("--objective", default="mar", choices=["mar", "cagr"])
    wf.set_defaults(func=cmd_walkforward)

    ls = sub.add_parser("list", help="list available systems and suites")
    ls.set_defaults(func=cmd_list)
    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
