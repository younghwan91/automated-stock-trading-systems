"""Technical indicators used by the trading systems.

All functions operate on :class:`pandas.Series` / :class:`pandas.DataFrame`
columns and return a Series aligned to the input index. Smoothing for RSI,
ATR and ADX follows J. Welles Wilder's original method (an EMA with
``alpha = 1 / period``), which is what the book's reference platform uses.

The functions are deliberately pure and stateless so they can be unit-tested
in isolation and reused by every system without surprises.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def sma(series: pd.Series, period: int) -> pd.Series:
    """Simple moving average."""
    return series.rolling(window=period, min_periods=period).mean()


def roc(series: pd.Series, period: int) -> pd.Series:
    """Rate of change in percent over ``period`` bars: (P_t / P_{t-n} - 1) * 100."""
    return (series / series.shift(period) - 1.0) * 100.0


def _wilder_smoothing(series: pd.Series, period: int) -> pd.Series:
    """Wilder's smoothing == EWMA with alpha = 1/period (no bias correction)."""
    return series.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()


def true_range(high: pd.Series, low: pd.Series, close: pd.Series) -> pd.Series:
    """The classic True Range: max of the three candidate ranges."""
    prev_close = close.shift(1)
    tr = pd.concat(
        [
            high - low,
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr


def atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    """Average True Range (Wilder)."""
    tr = true_range(high, low, close)
    return _wilder_smoothing(tr, period)


def atr_percent(
    high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14
) -> pd.Series:
    """ATR expressed as a percentage of the closing price.

    This normalises volatility across stocks of very different price levels,
    which is exactly how the book defines several of its filters.
    """
    return atr(high, low, close, period) / close * 100.0


def rsi(close: pd.Series, period: int = 14) -> pd.Series:
    """Relative Strength Index (Wilder smoothing of gains/losses)."""
    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = (-delta).clip(lower=0.0)
    avg_gain = _wilder_smoothing(gain, period)
    avg_loss = _wilder_smoothing(loss, period)
    rs = avg_gain / avg_loss
    out = 100.0 - (100.0 / (1.0 + rs))
    # When there are no losses the RSI is 100 by definition.
    out = out.where(avg_loss != 0.0, 100.0)
    # When there are no gains and no losses (flat), RSI is undefined -> 50.
    out = out.where(~((avg_gain == 0.0) & (avg_loss == 0.0)), 50.0)
    return out


def adx(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    """Average Directional Index (Wilder).

    Returns the ADX line only (not +DI / -DI), which is all the systems need.
    """
    up_move = high.diff()
    down_move = -low.diff()

    plus_dm = pd.Series(
        np.where((up_move > down_move) & (up_move > 0.0), up_move, 0.0), index=high.index
    )
    minus_dm = pd.Series(
        np.where((down_move > up_move) & (down_move > 0.0), down_move, 0.0), index=high.index
    )

    tr = true_range(high, low, close)
    atr_w = _wilder_smoothing(tr, period)

    plus_di = 100.0 * _wilder_smoothing(plus_dm, period) / atr_w
    minus_di = 100.0 * _wilder_smoothing(minus_dm, period) / atr_w

    dx = 100.0 * (plus_di - minus_di).abs() / (plus_di + minus_di)
    dx = dx.replace([np.inf, -np.inf], np.nan).fillna(0.0)
    return _wilder_smoothing(dx, period)


def historic_volatility(close: pd.Series, period: int = 100, trading_days: int = 252) -> pd.Series:
    """Annualised historical volatility in percent.

    Standard deviation of daily log returns over ``period`` bars, scaled by
    ``sqrt(trading_days)`` and expressed as a percentage.
    """
    log_ret = np.log(close / close.shift(1))
    vol = log_ret.rolling(window=period, min_periods=period).std(ddof=1)
    return vol * np.sqrt(trading_days) * 100.0


def avg_dollar_volume(close: pd.Series, volume: pd.Series, period: int) -> pd.Series:
    """Average daily dollar volume (close * volume) over ``period`` bars."""
    return (close * volume).rolling(window=period, min_periods=period).mean()


def avg_volume(volume: pd.Series, period: int) -> pd.Series:
    """Average share volume over ``period`` bars."""
    return volume.rolling(window=period, min_periods=period).mean()


def rolling_return(close: pd.Series, period: int) -> pd.Series:
    """Fractional return over ``period`` bars: P_t / P_{t-n} - 1 (not percent)."""
    return close / close.shift(period) - 1.0
