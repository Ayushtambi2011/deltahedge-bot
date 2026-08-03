"""Strategy selector — implements the requested decision tree:

    High IV        -> Iron Condor
    Trending       -> Broken-Wing Butterfly
    Major event    -> Long Strangle (entered BEFORE the print; blackout still blocks
                      new entries DURING the print window)
    Low IV         -> No Trade
    Ambiguous      -> return BOTH matching strategies (paper A/B; see request #4)

IMPORTANT (overfitting): the IV/trend THRESHOLDS below are unvalidated placeholders.
Absolute IV is a stand-in until ~30 days of recorded chains give a real IV RANK
(docs/05_LEARNING_LOOP.md). Tune from the log, not from intuition.
"""
import glob
import csv
import os

# --- thresholds (TUNE from data; do not trust as-is) ---
IV_HIGH = 75.0     # ATM IV% above this = "high IV" -> sell premium (condor)
IV_LOW = 45.0      # ATM IV% below this = "low IV" -> premium too thin -> no trade
TREND_PCT = 0.04   # |price change| over the trend window above this = "trending"
TREND_WINDOW = 5   # snapshots (days)

CHAINS = os.path.join(os.path.dirname(__file__), "..", "data", "chains")


def trend_score(asset):
    """Return signed % move over the last TREND_WINDOW recorded chain snapshots.
    Positive = up-trend. None if not enough history yet."""
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


def select(iv, asset, event_soon=False, in_blackout=False):
    """Return list of (strategy, reason). Empty list = NO TRADE / HOLD."""
    if in_blackout:
        return []  # never open a fresh trade during the print window

    picks = []
    tr = trend_score(asset)
    trending = tr is not None and abs(tr) >= TREND_PCT

    # Major event soon -> long strangle (buy vol into the event)
    if event_soon:
        picks.append(("long_strangle", "major event ahead — long vol into the move"))

    # IV regime
    if iv is not None:
        if iv >= IV_HIGH:
            picks.append(("iron_condor", f"high IV {iv:.0f}% — sell rich premium"))
        elif iv <= IV_LOW and not event_soon and not trending:
            # low IV, nothing else -> no trade
            return _dedupe(picks)

    # Trend -> broken-wing butterfly (directional, defined risk)
    if trending:
        direction = "up" if tr > 0 else "down"
        picks.append(("broken_wing_butterfly", f"trending {direction} {tr*100:+.1f}% — skewed fly"))

    # Neutral middle: default to condor if nothing fired and IV isn't low
    if not picks and (iv is None or iv > IV_LOW):
        picks.append(("iron_condor", "neutral / mid IV — default condor"))

    return _dedupe(picks)


def _dedupe(picks):
    seen, out = set(), []
    for name, reason in picks:
        if name not in seen:
            seen.add(name); out.append((name, reason))
    return out


if __name__ == "__main__":
    for iv in (40, 60, 80):
        print(f"IV {iv}: ", select(iv, "BTC", event_soon=False, in_blackout=False))
    print("event: ", select(60, "BTC", event_soon=True))
    print("blackout:", select(80, "BTC", in_blackout=True))
