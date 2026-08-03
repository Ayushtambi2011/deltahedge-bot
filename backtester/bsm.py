"""Black-Scholes-Merton pricing + greeks. Used to synthesize daily-expiry option
prices from a spot series and an IV assumption, so the backtester runs without a
full historical option chain. Replace with real chain data when you have it."""
import math

def _norm_cdf(x):
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))

def _d1(S, K, T, r, sigma):
    if T <= 0 or sigma <= 0:
        return float("inf") if S > K else float("-inf")
    return (math.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))

def price(S, K, T, r, sigma, kind):
    """European option price. kind = 'call' or 'put'. T in years."""
    if T <= 0:
        return max(0.0, S - K) if kind == "call" else max(0.0, K - S)
    d1 = _d1(S, K, T, r, sigma)
    d2 = d1 - sigma * math.sqrt(T)
    if kind == "call":
        return S * _norm_cdf(d1) - K * math.exp(-r * T) * _norm_cdf(d2)
    return K * math.exp(-r * T) * _norm_cdf(-d2) - S * _norm_cdf(-d1)

def delta(S, K, T, r, sigma, kind):
    if T <= 0:
        intrinsic = (S > K) if kind == "call" else (S < K)
        return (1.0 if kind == "call" else -1.0) if intrinsic else 0.0
    d1 = _d1(S, K, T, r, sigma)
    return _norm_cdf(d1) if kind == "call" else _norm_cdf(d1) - 1.0

def implied_vol(mkt_price, S, K, T, r, kind, lo=0.001, hi=5.0):
    """Invert BSM for sigma (decimal) via bisection. Returns None if not solvable."""
    if mkt_price is None or mkt_price <= 0 or T <= 0:
        return None
    intrinsic = max(0.0, S - K) if kind == "call" else max(0.0, K - S)
    if mkt_price < intrinsic - 1e-6:
        return None
    for _ in range(100):
        mid = (lo + hi) / 2
        p = price(S, K, T, r, mid, kind)
        if abs(p - mkt_price) < 1e-6:
            return mid
        if p > mkt_price:
            hi = mid
        else:
            lo = mid
    return (lo + hi) / 2


def strike_for_delta(S, T, r, sigma, target_delta, kind):
    """Find the strike whose |delta| ~= target_delta (bisection). target_delta in (0,0.5)."""
    lo, hi = S * 0.5, S * 1.5
    for _ in range(60):
        mid = (lo + hi) / 2
        d = abs(delta(S, mid, T, r, sigma, kind))
        if kind == "call":
            # higher strike -> lower call delta
            if d > target_delta:
                lo = mid
            else:
                hi = mid
        else:
            # higher strike -> higher put |delta|
            if d > target_delta:
                hi = mid
            else:
                lo = mid
    return round((lo + hi) / 2)
