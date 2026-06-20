import numpy as np
import pandas as pd
import pytest

from asts import indicators as ind


@pytest.fixture
def close():
    return pd.Series([10, 11, 12, 11, 13, 14, 13, 15, 16, 15, 17, 18], dtype=float)


def test_sma_basic(close):
    s = ind.sma(close, 3)
    assert np.isnan(s.iloc[1])
    assert s.iloc[2] == pytest.approx((10 + 11 + 12) / 3)


def test_roc(close):
    r = ind.roc(close, 2)
    assert r.iloc[2] == pytest.approx((12 / 10 - 1) * 100)


def test_rsi_bounds(close):
    r = ind.rsi(close, 3).dropna()
    assert ((r >= 0) & (r <= 100)).all()


def test_rsi_all_gains_is_100():
    up = pd.Series(np.arange(1, 30, dtype=float))
    r = ind.rsi(up, 3).dropna()
    assert r.iloc[-1] == pytest.approx(100.0)


def test_atr_positive():
    n = 40
    high = pd.Series(np.linspace(10, 20, n) + 0.5)
    low = pd.Series(np.linspace(10, 20, n) - 0.5)
    cl = pd.Series(np.linspace(10, 20, n))
    a = ind.atr(high, low, cl, 14).dropna()
    assert (a > 0).all()


def test_adx_range():
    n = 60
    rng = np.random.default_rng(0)
    cl = pd.Series(100 + np.cumsum(rng.normal(0, 1, n)))
    high = cl + 1
    low = cl - 1
    a = ind.adx(high, low, cl, 7).dropna()
    assert ((a >= 0) & (a <= 100)).all()


def test_historic_volatility_positive():
    rng = np.random.default_rng(1)
    cl = pd.Series(100 * np.exp(np.cumsum(rng.normal(0, 0.01, 200))))
    hv = ind.historic_volatility(cl, 100).dropna()
    assert (hv > 0).all()
