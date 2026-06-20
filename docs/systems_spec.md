# Systems Specification

Faithful transcription of the seven trading systems from *Automated Stock
Trading Systems* (Laurens Bensdorp, 2020), as implemented in `src/asts/systems/`.
Each system is described by the **12 ingredients**: objective, beliefs, trading
universe, filter, setup, ranking, entry, stop-loss, re-entry, profit protection,
profit taking, position sizing.

Common to all systems unless noted: universe = all NYSE/NASDAQ/AMEX listed
stocks; re-entry = next day if conditions still hold; position sizing = 2%
percent-risk and 10% percent-size cap, max 10 positions per system.

---

## System 1 — Long Trend High Momentum  *(trend, long)*
| Ingredient | Rule |
|---|---|
| Filter | Avg dollar volume(20) > $50M; price ≥ $5 |
| Setup | SPY close > SMA100 (index uptrend); stock SMA25 > SMA50 |
| Ranking | Highest 200-day rate of change |
| Entry | Next day market on open |
| Stop-loss | 5 × ATR(20) below entry |
| Profit protection | 25% trailing stop |
| Profit taking | None — ride the trend |

## System 2 — Short RSI Thrust  *(mean reversion, short)*
| Ingredient | Rule |
|---|---|
| Filter | Price ≥ $5; avg dollar volume(20) > $25M; ATR%(10) ≥ 3% |
| Setup | RSI(3) > 90; the last two closes each higher than the prior close |
| Ranking | Highest ADX(7) |
| Entry | Sell short limit 4% above prior close |
| Stop-loss | 3 × ATR(10) above entry |
| Profit taking | +4% (close-based) → next MOC; else time exit after 2 days |

## System 3 — Long Mean Reversion Selloff  *(mean reversion, long)*
| Ingredient | Rule |
|---|---|
| Filter | Price ≥ $1; avg volume(50) ≥ 1M shares; ATR%(10) ≥ 5% |
| Setup | Close > SMA150; 3-day drop ≥ 12.5% |
| Ranking | Biggest 3-day drop |
| Entry | Buy limit 7% below prior close |
| Stop-loss | 2.5 × ATR(10) below entry |
| Profit taking | +4% (close-based) → next MOC; else time exit after 3 days |

## System 4 — Long Trend Low Volatility  *(trend, long)*
| Ingredient | Rule |
|---|---|
| Filter | Avg dollar volume(50) > $100M; historic volatility(100) ∈ [10%, 40%] |
| Setup | SPY close > SMA200 (index uptrend); stock close > SMA200 |
| Ranking | Lowest RSI(4) (most oversold) |
| Entry | Next day market on open |
| Stop-loss | 1.5 × ATR(40) below entry |
| Profit protection | 20% trailing stop |
| Profit taking | None |

## System 5 — Long Mean Reversion High ADX Reversal  *(mean reversion, long)*
| Ingredient | Rule |
|---|---|
| Filter | Avg volume(50) ≥ 500k shares; avg dollar volume(50) ≥ $2.5M; ATR%(10) > 4% |
| Setup | Close > SMA100 + 1×ATR(10); ADX(7) > 55; RSI(3) < 50 |
| Ranking | Highest ADX(7) |
| Entry | Buy limit 3% below prior close |
| Stop-loss | 3 × ATR(10) below entry |
| Profit taking | +1×ATR(10) (close-based) → next MOO; else time exit after 6 days |

## System 6 — Short Mean Reversion High Six-Day Surge  *(mean reversion, short)*
| Ingredient | Rule |
|---|---|
| Filter | Price ≥ $5; avg dollar volume(50) ≥ $10M |
| Setup | 6-day gain ≥ 20%; last two closes each higher than the prior close |
| Ranking | Biggest 6-day gain |
| Entry | Sell short limit 5% above prior close |
| Stop-loss | 3 × ATR(10) above entry |
| Profit taking | +5% (close-based) → next MOC; else time exit after 3 days |

## System 7 — The Catastrophe Hedge  *(trend, short — SPY only)*
| Ingredient | Rule |
|---|---|
| Universe | SPY only (or an equivalent derivative) |
| Filter | None |
| Setup | SPY close = lowest close of the last 50 days |
| Entry | Next day market on open |
| Stop-loss | 3 × ATR(40) above entry |
| Profit protection | Cover when SPY close = highest close of last 70 days → next MOO |
| Position sizing | Percent-of-equity (single instrument); allocation-scaled in a suite |

> System 7 is **expected to lose money** on a bullish backtest. It is insurance
> against down-momentum regimes (1929/1987/2008) where the mean-reversion shorts
> have no overbought setup to trade.

---

## Suites (capital allocation)

Long and short books run **simultaneously** (up to 100% long + 100% short), so
long allocations sum to 1.0 and short allocations sum to 1.0 independently.

| Suite | Long | Short |
|---|---|---|
| `suite3` (Ch. 7) | S1 50%, S3 50% | S2 100% |
| `suite6` (Ch. 9) | S1 25%, S4 25%, S3 25%, S5 25% | S2 50%, S6 50% |
| `suite7` (Ch. 10) | S1 25%, S4 25%, S3 25%, S5 25% | S2 40%, S6 40%, **S7 20%** |

## Implementation notes / deviations

- **Execution**: every order created at the close of day *D* fills on day *D+1*
  (the book's "next day" convention). Limit orders fill only if the day's range
  touches the limit; protective stops activate the day *after* entry.
- **Wilder smoothing** is used for RSI, ATR and ADX (α = 1/period).
- **"ATR > 4%" (System 5 filter)** is interpreted as ATR%(10) > 4, consistent
  with how the book normalises volatility across price levels elsewhere.
- The reported numbers will **not** match the book exactly: the book backtests
  the real 1995–2019 US equity universe with survivorship-bias-free data; this
  repo ships a synthetic universe so it can run offline. Plug a real data feed
  (`asts.data.yahoo`) in for closer comparison. The *qualitative* behaviour —
  trend systems with low win-rate/high payoff, mean-reversion with high
  win-rate/low payoff, near-zero benchmark correlation for the combined suite,
  and a large drawdown reduction from diversification — reproduces faithfully.
