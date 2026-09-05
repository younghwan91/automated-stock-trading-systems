# Automated Stock Trading Systems (ASTS)

[![CI](https://github.com/younghwan91/automated-stock-trading-systems/actions/workflows/ci.yml/badge.svg)](https://github.com/younghwan91/automated-stock-trading-systems/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![LinkedIn](https://img.shields.io/badge/LinkedIn-younghwan--chae-0A66C2?logo=linkedin&logoColor=white)](https://www.linkedin.com/in/younghwan-chae/)

An educational Python backtester for the **seven non-correlated trading
systems** in Laurens Bensdorp's *Automated Stock Trading Systems* (Lioncrest,
2020). Runs offline on a synthetic universe — no data vendor, no API key.

> ⚠️ **Not investment advice.** Research and education only. See
> [`DISCLAIMER.md`](DISCLAIMER.md).

## Why seven systems

A single edge is fragile. The book's argument is that conceptually different
systems — long and short, trend-following and mean-reversion — draw down at
different times, so running them together smooths the equity curve.

That is the claim this repo tests, and on the synthetic universe it holds: every
individual system lands under MAR 0.6, every combined suite clears 0.95, and max
drawdown drops ~3× against the strongest single system.

![examples/run_suite.py output](docs/images/run_suite.png)

Full table, tear sheet, and the Monte Carlo / sensitivity / walk-forward
checks: **[`docs/results.md`](docs/results.md)**.

## Quick start

```bash
pip install -e .          # core: pandas, numpy, pyyaml
pip install -e ".[data]"  # + yfinance, for real prices

asts list                            # systems and suites
asts run --suite suite7 --synthetic  # all 7, offline
python examples/run_suite.py         # the comparison pictured above
asts run --suite suite6 --symbols AAPL,MSFT,JPM --start 2010-01-01 --end 2019-12-31
```

From Python: `run_backtest(build_suite("suite7"), universe)`.

## What's inside

An event-driven daily engine with next-day execution — limit and market orders,
ATR stops, trailing stops, profit targets, time exits, slippage, commission —
plus Bensdorp position sizing (2% percent-risk capped by 10% percent-size, max
10 positions/system). Rule tables for all seven systems:
[`docs/systems_spec.md`](docs/systems_spec.md). `examples/custom_system.py` adds
an eighth (Donchian breakout) by subclassing `TradingSystem`.

```bash
pip install -e ".[dev]" && pytest    # 31 tests
```

## Limits

- The default universe is **synthetic** — reproducible and survivorship-bias-free
  by construction, but not the market. Read the numbers as evidence the code
  implements the rules, not as performance.
- The `yfinance` loader gives real prices but a survivorship-biased universe:
  delisted names are absent, so those results skew optimistic.
- No live trading, no broker integration, no intraday data.

## Attribution and license

The strategies are Laurens Bensdorp's, described in
*[Automated Stock Trading Systems: A Systematic Approach for Traders to Make
Money in Bull, Bear and Sideways Markets](https://www.tradingmasteryschool.com/)*
(Lioncrest Publishing, 2020). This is an independent reimplementation from the
book's published rule descriptions, for study — no text, code, or data from the
book is reproduced here, and the project is **not** affiliated with or endorsed
by the author or publisher. If the systems interest you, buy the book.

Code is MIT ([`LICENSE`](LICENSE)). Backtested performance does not predict
future results.

---

## ⭐ Found this useful?

If this project helped you, please **[⭐ Star it](https://github.com/younghwan91/automated-stock-trading-systems)** — it boosts discoverability so more developers can find it.

- 🐛 Bugs & questions → [Issues](https://github.com/younghwan91/automated-stock-trading-systems/issues)
- 📈 [Follow @younghwan91](https://github.com/younghwan91) for updates

## Related projects — open-source quant stack

Part of an open-source stack spanning Korean equities, US equities and crypto. Each repository stands on its own.

| Market | Project | What it is |
|---|---|---|
| 🇰🇷 Korean equities | **[kiwoom-client](https://github.com/younghwan91/kiwoom-client)** | Kiwoom Securities REST API client — full domestic-equity endpoint coverage, real-time WebSocket, sync + async (`pip install kiwoom-client`) |
| 🇰🇷 Korean equities | **[krx-fundamentals-client](https://github.com/younghwan91/krx-fundamentals-client)** | Korean corporate fundamentals Python client library — financial statements, valuation, dividends, screening (DART + KRX + Naver) |
| 🇰🇷 Korean equities | **[krx-news-client](https://github.com/younghwan91/krx-news-client)** | Korean market news & disclosure Python client library (DART + Hankyung + TheBell + Toss) |
| 🇰🇷 Korean equities | **[fin-checkup](https://github.com/younghwan91/fin-checkup)** | Telegram alerts for risk disclosures + a DART/SEC financial health checkup — reports measurements and facts, never a recommendation |
| 🇰🇷 Korean equities | **[quant-airflow](https://github.com/younghwan91/quant-airflow)** | Airflow pipeline collecting Korean market data into TimescaleDB — delisted names included, so downstream backtests aren't survivorship-biased |
| 🇰🇷 Korean equities | **[kr-quant](https://github.com/younghwan91/kr-quant)** | KOSPI/KOSDAQ alpha research — walk-forward, random null controls, purged CV and Deflated Sharpe enforced as CI guardrails |
| 🇺🇸 US equities | **[portfolio-research](https://github.com/younghwan91/portfolio-research)** | US equity factor engine — walk-forward gated by Deflated Sharpe and PBO on point-in-time, survivorship-bias-free data (plus tactical ETF allocation: 9 pre-registered, 0 adopted) |
| ₿ Crypto | **[quantbox-engine](https://github.com/younghwan91/quantbox-engine)** | Crypto futures backtest & execution engine — zero lookahead, backtest↔live parity |

## Author

**Younghwan Chae** · [GitHub @younghwan91](https://github.com/younghwan91) · [LinkedIn](https://www.linkedin.com/in/younghwan-chae/)

See the full open-source quant stack on my [profile](https://github.com/younghwan91).
