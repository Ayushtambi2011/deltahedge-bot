"""Price data loader.

Default: generates a synthetic BTC/ETH daily series (GBM) so the backtester runs
immediately. This is for PLUMBING TESTS ONLY — synthetic data cannot tell you if a
strategy has real edge.

To use REAL data: drop a CSV in ../data/ with columns: date,close  (daily closes)
and call load_csv(path). Get free daily OHLC from any exchange API or data provider,
or pull it from Delta's own API (see docs/04_ARCHITECTURE.md).
"""
import csv
import math
import random

def load_csv(path):
    rows = []
    with open(path) as f:
        for r in csv.DictReader(f):
            rows.append((r["date"], float(r["close"])))
    return rows

def synthetic(symbol="BTC", n_days=365, start=60000.0, annual_vol=0.60, seed=42):
    """GBM daily closes. Purely for testing the engine, NOT for edge conclusions."""
    random.seed(seed if symbol == "BTC" else seed + 1)
    if symbol == "ETH":
        start = 3000.0
    dt = 1.0 / 365
    mu = 0.0
    closes = [start]
    for _ in range(n_days - 1):
        z = random.gauss(0, 1)
        ret = (mu - 0.5 * annual_vol ** 2) * dt + annual_vol * math.sqrt(dt) * z
        closes.append(closes[-1] * math.exp(ret))
    rows = [(f"D{i:04d}", round(c, 2)) for i, c in enumerate(closes)]
    return rows

def realized_vol(closes, window=10):
    """Trailing annualized realized vol from a list of closes (most recent last)."""
    if len(closes) < window + 1:
        return None
    rets = [math.log(closes[i] / closes[i - 1]) for i in range(len(closes) - window, len(closes))]
    m = sum(rets) / len(rets)
    var = sum((x - m) ** 2 for x in rets) / max(1, len(rets) - 1)
    return math.sqrt(var * 365)
