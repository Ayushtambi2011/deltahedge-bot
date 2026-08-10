"""Strategy selector — REGIME-ADAPTIVE (rebuilt after 119-trade review).

Lesson from the data: the desk was structurally LONG volatility in a quiet market and bled.
The fix is to make the posture follow the regime, driven by IV RANK (where current IV sits
vs its own recent history), not a fixed IV threshold:

    IV rank RICH  (>= 0.70)          -> Iron Condor         (SELL premium — best short-vol edge)
    IV rank MID   (0.25 .. 0.70)     -> Iron Condor         (default: sell)
    IV rank CHEAP (<= 0.25) + event  -> Long Strangle       (BUY cheap vol, but only with a catalyst)
    IV rank CHEAP + no event         -> NO TRADE            (don't buy vol without a reason)
    trending                          -> + Broken-Wing Fly  (directional, defined risk)

Net effect: SELL vol by default, BUY vol only when it's cheap AND a catalyst exists.
IV rank needs history to be meaningful — it warms up as data/chains/ accumulates (>=5 days).
NOT tuned to any single week; the signal adapts as IV moves.
"""
import glob
import csv
import os

TREND_PCT = 0.04
TREND_WINDOW = 5
IV_RICH = 0.70          # sell premium aggressively above this rank
IV_CHEAP = 0.25         # only buy vol below this rank (and only with a catalyst)

CHAINS = os.path.join(os.path.dirname(__file__), "..", "data", "chains")


def trend_score(asset):
    files = sorted(glob.glob(os.path.join(CHAINS, f"{asset}_*.csv")))
    if len(files) < 2:
        return None
    spots = []
    for p in files[-(TREND_WINDOW + 1):]:
        with open(p) as f:
            r = next(csv.DictReader(f), None)
            if r and r.get("spot"):
                try:
                    spots.append(float(r["spot"]))
                except ValueError:
                    pass
    if len(spots) < 2:
        return None
    return (spots[-1] - spots[0]) / spots[0]


def _atm_iv(path):
    """ATM IV from one recorded chain snapshot (strike nearest spot with an IV)."""
    try:
        with open(path) as f:
            rows = list(csv.DictReader(f))
    except OSError:
        return None
    if not rows:
        return None
    try:
        spot = float(rows[0].get("spot") or 0)
    except ValueError:
        return None
    if not spot:
        return None
    best, bestd = None, 1e18
    for r in rows:
        iv = r.get("iv")
        if iv in (None, ""):
            continue
        try:
            k = float(r["strike"]); ivf = float(iv); d = abs(k - spot)
        except ValueError:
            continue
        if d < bestd:
            bestd, best = d, ivf
    return best


def iv_rank(asset, current_iv):
    """Percentile (0..1) of current ATM IV vs recorded daily history. None if <5 days."""
    if current_iv is None:
        return None
    hist = []
    for p in sorted(glob.glob(os.path.join(CHAINS, f"{asset}_*.csv"))):
        v = _atm_iv(p)
        if v:
            hist.append(v)
    if len(hist) < 5:
        return None
    below = sum(1 for v in hist if v <= current_iv)
    return round(below / len(hist), 2)


def select(iv, asset, event_soon=False, in_blackout=False):
    """Return list of (strategy, reason). Empty = NO TRADE / HOLD. SELL-vol default."""
    if in_blackout:
        return []
    picks = []
    tr = trend_score(asset)
    trending = tr is not None and abs(tr) >= TREND_PCT
    rank = iv_rank(asset, iv)

    if rank is None:
        picks.append(("iron_condor", "building IV history — default sell (condor)"))
    elif rank >= IV_RICH:
        picks.append(("iron_condor", f"IV rank {rank*100:.0f}% rich — sell premium"))
    elif rank <= IV_CHEAP:
        if event_soon:
            picks.append(("long_strangle", f"IV rank {rank*100:.0f}% cheap + event — buy vol"))
        else:
            return []            # cheap vol, no catalyst -> stand aside (the big fix)
    else:
        picks.append(("iron_condor", f"IV rank {rank*100:.0f}% — default sell"))

    if trending:
        d = "up" if tr > 0 else "down"
        picks.append(("broken_wing_butterfly", f"trending {d} {tr*100:+.1f}% — skewed fly"))
    return _dedupe(picks)


def _dedupe(picks):
    seen, out = set(), []
    for name, reason in picks:
        if name not in seen:
            seen.add(name); out.append((name, reason))
    return out


if __name__ == "__main__":
    for r in ("BTC", "ETH"):
        print(r, "rank:", iv_rank(r, 60), "select:", select(60, r))
