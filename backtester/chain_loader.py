"""Load recorded REAL option-chain snapshots and build structures from real premiums.
Consumes files written by bot/record_chain.py (data/chains/{ASSET}_{YYYY-MM-DD}.csv)."""
import csv
import os
import glob


def load_snapshot(path):
    rows = []
    with open(path) as f:
        for r in csv.DictReader(f):
            for k in ("strike", "mark", "mid", "iv", "delta", "oi", "best_bid",
                      "best_ask", "spread", "spot"):
                r[k] = _f(r.get(k))
            rows.append(r)
    return rows


def _f(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def snapshots_for(asset, chains_dir):
    files = sorted(glob.glob(os.path.join(chains_dir, f"{asset}_*.csv")))
    return [(os.path.basename(p).split("_")[1].replace(".csv", ""), p) for p in files]


def _nearest_by_delta(rows, kind, target_abs_delta):
    cands = [r for r in rows if r["type"] == kind and r["delta"] is not None
             and r["mid"] is not None]
    if not cands:
        return None
    return min(cands, key=lambda r: abs(abs(r["delta"]) - target_abs_delta))


def _nearest_by_strike(rows, kind, strike):
    cands = [r for r in rows if r["type"] == kind and r["mid"] is not None]
    if not cands:
        return None
    return min(cands, key=lambda r: abs(r["strike"] - strike))


def build_iron_condor(rows, short_delta=0.16, wing_pct=0.02):
    """Returns legs with REAL entry premiums (mid). side +1 buy, -1 sell."""
    spot = rows[0]["spot"]
    sc = _nearest_by_delta(rows, "call", short_delta)
    sp = _nearest_by_delta(rows, "put", short_delta)
    if not (sc and sp and spot):
        return None
    lc = _nearest_by_strike(rows, "call", sc["strike"] + spot * wing_pct)
    lp = _nearest_by_strike(rows, "put", sp["strike"] - spot * wing_pct)
    if not (lc and lp):
        return None
    return [
        _leg(sc, -1), _leg(lc, +1), _leg(sp, -1), _leg(lp, +1),
    ]


def build_butterfly(rows, offset=500.0, min_rr=4.0):
    """Long CALL butterfly: buy K1, sell 2 center, buy K3 (equal spacing). A debit 'pin' bet:
    max loss = debit, max profit = width - debit. Scans candidate centers OUTWARD from spot
    and returns the CLOSEST-to-spot fly whose reward:risk >= min_rr (the highest-probability
    setup that still pays 1:min_rr). Best 1-3h before expiry when debits are small."""
    spot = rows[0]["spot"]
    if not spot:
        return None
    call_strikes = sorted({r["strike"] for r in rows
                           if r["type"] == "call" and r.get("mid") is not None})
    centers = sorted([k for k in call_strikes if abs(k - spot) <= 3 * offset],
                     key=lambda k: abs(k - spot))
    for c in centers:
        center = _nearest_by_strike(rows, "call", c)
        k1 = _nearest_by_strike(rows, "call", c - offset)
        k3 = _nearest_by_strike(rows, "call", c + offset)
        if not (center and k1 and k3):
            continue
        if k1["strike"] >= c or k3["strike"] <= c:
            continue
        if None in (center["mid"], k1["mid"], k3["mid"]):
            continue
        debit = k1["mid"] - 2 * center["mid"] + k3["mid"]
        width = c - k1["strike"]
        if debit <= 0 or width <= 0:
            continue
        max_profit = width - debit
        if max_profit > 0 and (max_profit / debit) >= min_rr:
            return [_leg(k1, +1), _leg(center, -1), _leg(center, -1), _leg(k3, +1)]
    return None


def build_cheap_strangle(rows, offset=400.0, max_prem=100.0):
    """Buy call at ~spot+offset and put at ~spot-offset, ONLY if BOTH mids <= max_prem.
    A low-cost bet on a big daily move. Returns legs or None if the condition isn't met."""
    spot = rows[0]["spot"]
    if not spot:
        return None
    call = _nearest_by_strike(rows, "call", spot + offset)
    put = _nearest_by_strike(rows, "put", spot - offset)
    if not (call and put) or call["mid"] is None or put["mid"] is None:
        return None
    if call["mid"] <= max_prem and put["mid"] <= max_prem:
        return [_leg(call, +1), _leg(put, +1)]
    return None


def build_long_strangle(rows, target_delta=0.25):
    sc = _nearest_by_delta(rows, "call", target_delta)
    sp = _nearest_by_delta(rows, "put", target_delta)
    if not (sc and sp):
        return None
    return [_leg(sc, +1), _leg(sp, +1)]


def build_broken_wing_butterfly(rows, trend=0.0, body_delta=0.25,
                                wide_pct=0.03, narrow_pct=0.015):
    """Direction-aware broken-wing butterfly (defined risk).
    trend >= 0 (bullish/neutral) -> PUT side (protect the downside with the wide wing).
    trend <  0 (bearish)         -> CALL side.
    Structure: sell 2 body, buy 1 wide wing (further protection), buy 1 narrow wing (broken).
    Real mids used for premiums."""
    spot = rows[0]["spot"]
    if spot is None:
        return None
    side_kind = "put" if trend >= 0 else "call"
    body = _nearest_by_delta(rows, side_kind, body_delta)
    if not body:
        return None
    if side_kind == "put":
        wide = _nearest_by_strike(rows, "put", body["strike"] + spot * wide_pct)   # ATM side (protect)
        narrow = _nearest_by_strike(rows, "put", body["strike"] - spot * narrow_pct)  # broken side
    else:
        wide = _nearest_by_strike(rows, "call", body["strike"] - spot * wide_pct)
        narrow = _nearest_by_strike(rows, "call", body["strike"] + spot * narrow_pct)
    if not (wide and narrow):
        return None
    # sell 2 body (two short legs), buy the two wings
    return [_leg(body, -1), _leg(body, -1), _leg(wide, +1), _leg(narrow, +1)]


def _leg(row, side):
    return {"type": row["type"], "strike": row["strike"], "side": side,
            "entry_premium": row["mid"], "symbol": row["symbol"]}
