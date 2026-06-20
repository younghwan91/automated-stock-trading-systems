# Robustness & Validation

A single backtest reports *one* realised path and is silent about luck and
overfitting. The `asts.analysis` package adds three tools that a professional
process requires before trusting a strategy.

## 1. Monte Carlo (`asts montecarlo`)

Resamples the strategy's **daily returns** into thousands of synthetic paths to
estimate the *distribution* of CAGR, maximum drawdown and terminal return — and
the tail risks the point estimate hides.

- **`block` bootstrap** (default): draws contiguous blocks (`--block`, default
  10 days), preserving short-horizon autocorrelation and realistic drawdown
  clustering. A stationary (wrap-around) variant.
- **`iid` bootstrap**: independent draws; simpler but understates drawdowns.

```bash
asts montecarlo --suite suite6 --synthetic --sims 2000 --block 10
```

Reports the 5/25/50/75/95 percentiles plus `P(maxDD worse than -20%/-30%)` and
`P(negative total return)`. Use it to ask *"is my realised −8% drawdown typical,
or did I just get lucky?"*

## 2. Position-sizing sensitivity (`asts sensitivity`)

The book's Chapter 5 thesis made executable: **hold the buy/sell rules fixed and
vary only the sizing levers** (`risk_pct`, `max_pct_size`). The sweep shows CAGR
and max drawdown rising together as sizing gets more aggressive — sizing shapes
the risk/return profile, not the underlying edge.

```bash
asts sensitivity --suite suite6 --synthetic \
    --risk-grid 0.005,0.01,0.02,0.03,0.05 --size-grid 0.05,0.10,0.20
```

Example (synthetic, suite6) — note the monotonic trade-off:

```
CAGR % by (risk_pct × max_pct_size)        Max Drawdown %
              0.05  0.10   0.20                      0.05   0.10   0.20
0.01          3.05  5.21   7.15            0.01     -5.36  -8.96 -12.93
0.02          3.15  6.41  10.35            0.02     -5.35 -10.88 -17.25
0.05          3.15  6.65  12.97            0.05     -5.35 -10.84 -20.86
```

## 3. Walk-forward optimization (`asts walkforward`)

The only honest way to report an *optimized* parameter. Rolling windows tune the
percent-risk lever on an **in-sample** window (objective: MAR or CAGR), then
measure the immediately following **out-of-sample** window the optimiser never
saw. OOS windows are stitched into a bias-free track record, and a fixed-2%
baseline is run alongside.

```bash
asts walkforward --suite suite6 --synthetic --is-years 4 --oos-years 2 \
    --risk-grid 0.005,0.01,0.02,0.03,0.05 --objective mar
```

> **Interpreting the result**: if walk-forward optimization only matches (or even
> trails) the fixed-2% baseline OOS — as it does on the shipped synthetic data —
> that is the *desirable* finding: the edge lives in the systems, not in
> curve-fitting the sizing lever. A large, consistent OOS outperformance from
> optimization would instead be a red flag for overfitting.

## Engine support

Both walk-forward and any custom out-of-sample analysis rely on
`BacktestConfig(trade_start=..., trade_end=...)`: indicators are always computed
over the **full** price history (so lookbacks/warmup are correct), while only the
*trading* calendar is restricted to the requested window.
