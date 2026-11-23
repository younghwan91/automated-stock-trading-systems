# Project Guide

New here? Start with the [README](../README.md).

<!-- toc -->
- [Architecture](#architecture)
- [Development](#development)
<!-- /toc -->

## Architecture

`run_backtest()` (`backtest.py`) is the single high-level entry point:
universe → features/bars → `BacktestEngine` → `Portfolio` → `Metrics`. The CLI
(`asts run|montecarlo|sensitivity|walkforward|list`) and the scripts under
`examples/` are thin callers of the same function.

```mermaid
flowchart LR
    subgraph Entry["Entry points"]
        CLI["asts CLI\n(cli.py)"]
        EX["examples/run_suite.py\nreal_data.py · robustness.py"]
    end

    subgraph Data["Universe"]
        SYN["synthetic.make_universe\n(offline, reproducible)"]
        YHO["yahoo.load_universe\n(yfinance, real prices)"]
    end

    subgraph Prep["Feature prep (backtest.py)"]
        FEAT["features.compute_features"]
        BARS["features.to_bars → Bars"]
    end

    SYS["systems.build_suite\n(System1..7 registry)"]

    ENG["BacktestEngine.run()\n(daily loop: exits → entries → stops → signals)"]

    PF["Portfolio\n(positions, cash, equity curve, closed trades)"]

    subgraph Output["Results"]
        MET["metrics.compute_metrics"]
        PLOT["plotting.plot_tearsheet"]
        AN["analysis: montecarlo, sensitivity, walkforward"]
    end

    CLI --> Data
    EX --> Data
    SYN --> FEAT
    YHO --> FEAT
    FEAT --> BARS
    CLI --> SYS
    EX --> SYS
    BARS --> ENG
    SYS --> ENG
    ENG --> PF
    PF --> MET
    PF --> PLOT
    MET --> AN
```

## Development

```bash
pip install -e ".[dev]" && pytest
```
