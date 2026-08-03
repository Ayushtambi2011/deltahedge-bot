"""READ-ONLY Delta Exchange India client — built against the REAL /v2/tickers schema
(verified 2026-08-03). NO order-placement method exists here by design.

Confirmed ticker fields per option: symbol, strike_price, contract_type, mark_price,
mark_iv, spot_price, best_bid, best_ask, oi, oi_value, greeks{delta,theta,gamma,vega},
quotes, impact_mid_price, product_id.
Symbol format: {C|P}-{ASSET}-{STRIKE}-{DDMMYY}   e.g. C-BTC-63000-030826

Docs: https://docs.delta.exchange   Base (India): https://api.india.delta.exchange
"""
import os
import sys
import datetime
import requests

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backtester"))
import bsm  # noqa: E402  (for implied-vol fallback when Delta's mark_iv is null)

BASE = os.environ.get("DELTA_BASE_URL", "https://api.india.delta.exchange").rstrip("/")
RISK_FREE = 0.06


def _get(path, params=None):
    r = requests.get(BASE + path, params=params, timeout=20)
    r.raise_for_status()
    return r.json()


def parse_symbol(sym):
    """'C-BTC-63000-030826' -> dict(type='call', asset='BTC', strike=63000, expiry=date)."""
    try:
        t, asset, strike, ddmmyy = sym.split("-")
        d = datetime.date(2000 + int(ddmmyy[4:6]), int(ddmmyy[2:4]), int(ddmmyy[0:2]))
        return {"type": "call" if t.upper() == "C" else "put",
                "asset": asset.upper(), "strike": float(strike), "expiry": d}
    except Exception:
        return None


def get_tickers():
    """All option tickers (calls + puts)."""
    return _get("/v2/tickers", params={"contract_types": "call_options,put_options"}).get("result", [])


def _mid(t):
    bb, ba = t.get("best_bid"), t.get("best_ask")
    try:
        bb, ba = float(bb), float(ba)
        if bb > 0 and ba > 0:
            return (bb + ba) / 2
    except (TypeError, ValueError):
        pass
    # fall back to mark price
    try:
        return float(t.get("mark_price"))
    except (TypeError, ValueError):
        return None


def get_chain(asset="BTC", expiry=None):
    """Return normalized chain rows for one asset (optionally one expiry date).
    Each row: type, strike, expiry, mark, mid, iv, delta, gamma, theta, vega, oi,
    best_bid, best_ask, spread, spot, symbol."""
    rows = []
    for t in get_tickers():
        meta = parse_symbol(t.get("symbol", ""))
        if not meta or meta["asset"] != asset.upper():
            continue
        if expiry and meta["expiry"] != expiry:
            continue
        g = t.get("greeks") or {}
        bb = _f(t.get("best_bid")); ba = _f(t.get("best_ask"))
        rows.append({
            "symbol": t.get("symbol"), "type": meta["type"], "strike": meta["strike"],
            "expiry": meta["expiry"].isoformat(),
            "mark": _f(t.get("mark_price")), "mid": _mid(t), "iv": _f(t.get("mark_iv")),
            "delta": _f(g.get("delta")), "gamma": _f(g.get("gamma")),
            "theta": _f(g.get("theta")), "vega": _f(g.get("vega")),
            "oi": _f(t.get("oi")), "best_bid": bb, "best_ask": ba,
            "spread": (ba - bb) if (bb and ba) else None,
            "spot": _f(t.get("spot_price")),
        })
    _fill_iv(rows)
    return rows


def _fill_iv(rows):
    """Delta's mark_iv is often null. Compute IV (percent) from the mark price via BSM
    inversion so downstream IV logic (selector, skew) actually works."""
    today = datetime.date.today()
    for r in rows:
        if r.get("iv") not in (None, 0):
            continue
        try:
            exp = datetime.date.fromisoformat(r["expiry"])
            days = (exp - today).days
            T = max(days, 0.25) / 365.0          # >=~6h floor for same-day expiry
            sig = bsm.implied_vol(r.get("mid") or r.get("mark"), r["spot"], r["strike"],
                                  T, RISK_FREE, r["type"])
            if sig:
                r["iv"] = round(min(max(sig * 100, 5.0), 500.0), 1)   # percent, bounded
        except (TypeError, ValueError, KeyError):
            pass


def _f(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def expiries(asset="BTC"):
    """Sorted list of available expiry dates for an asset."""
    ds = set()
    for t in get_tickers():
        m = parse_symbol(t.get("symbol", ""))
        if m and m["asset"] == asset.upper():
            ds.add(m["expiry"])
    return sorted(ds)


def nearest_expiry(asset="BTC", on_or_after=None):
    """The soonest expiry >= today (the 'daily' expiry to trade)."""
    on_or_after = on_or_after or datetime.date.today()
    fut = [d for d in expiries(asset) if d >= on_or_after]
    return fut[0] if fut else None


def weekly_expiry(asset="BTC", min_days=4):
    """The nearest expiry at least `min_days` out — used as the 'weekly' expiry
    (distinct from the near daily). Returns None if none that far out."""
    today = datetime.date.today()
    fut = [d for d in expiries(asset) if (d - today).days >= min_days]
    return fut[0] if fut else None


def spot(asset="BTC"):
    ch = get_chain(asset)
    return ch[0]["spot"] if ch else None


def get_candles(symbol, resolution="1d", start=None, end=None):
    """Historical OHLC for a product symbol (underlying or a still-listed option).
    NOTE: expired daily-option products are usually delisted -> not available here.
    That's why real backtest premiums must be RECORDED forward (see record_chain.py)."""
    params = {"symbol": symbol, "resolution": resolution}
    if start:
        params["start"] = start
    if end:
        params["end"] = end
    return _get("/v2/history/candles", params=params).get("result", [])


if __name__ == "__main__":
    try:
        exp = nearest_expiry("BTC")
        print("Nearest BTC expiry:", exp)
        chain = get_chain("BTC", exp)
        print(f"BTC chain rows for {exp}: {len(chain)}")
        if chain:
            c = sorted(chain, key=lambda r: r["strike"])[len(chain)//2]
            print("sample:", c)
            print("spot:", chain[0]["spot"])
    except Exception as e:
        print("API call failed:", e)
        print("Check network/region and DELTA_BASE_URL. Docs: https://docs.delta.exchange")
