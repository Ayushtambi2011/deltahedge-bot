"""Liquidation-cluster module.

HONEST NOTE: Coinglass's liquidation HEATMAP is a PAID Pro feature. The public API
returned {"code":"30001","msg":"API key missing."} — there is no free endpoint for it,
and the on-screen heatmap is a canvas you cannot scrape. So this module supports:
  (A) a Coinglass API key (env COINGLASS_API_KEY) if you buy one, OR
  (B) a manual CSV you fill from the heatmap: data/liquidation_levels.csv  (price,intensity)

Idea (a HYPOTHESIS to log, not gospel): price tends to gravitate toward large liquidation
clusters (they're magnets). So you generally do NOT want a short strike sitting right on a
big cluster — nudge shorts to sit BEYOND the nearest heavy cluster. Validate against your
paper log before trusting it (docs/05_LEARNING_LOOP.md).
"""
import csv
import os
import requests

LEVELS_CSV = os.path.join(os.path.dirname(__file__), "..", "data", "liquidation_levels.csv")
CG_KEY = os.environ.get("COINGLASS_API_KEY")
# v4 endpoint (from Coinglass docs). Key goes in the CG-API-KEY header.
CG_URL = "https://open-api-v4.coinglass.com/api/futures/liquidation/heatmap/model2"


def from_csv(path=LEVELS_CSV):
    """Manual levels: CSV with columns price,intensity (intensity 0..1 or notional)."""
    if not os.path.exists(path):
        return []
    out = []
    with open(path) as f:
        for r in csv.DictReader(f):
            try:
                out.append({"price": float(r["price"]), "intensity": float(r.get("intensity", 1))})
            except (TypeError, ValueError):
                pass
    return sorted(out, key=lambda x: x["price"])


def from_coinglass(symbol="BTC", exchange="Binance", rng="24h"):
    """v4 heatmap/model2. Requires a PAID key in CG-API-KEY header.
    symbol must be a PAIR e.g. BTCUSDT. Returns parsed [{price,intensity}] or []."""
    if not CG_KEY:
        return None
    pair = symbol if symbol.upper().endswith("USDT") else symbol.upper() + "USDT"
    r = requests.get(CG_URL, params={"exchange": exchange, "symbol": pair, "range": rng},
                     headers={"CG-API-KEY": CG_KEY, "accept": "application/json"}, timeout=25)
    r.raise_for_status()
    return _parse_heatmap(r.json())


def _parse_heatmap(payload):
    """Collapse the heatmap grid into price->intensity levels. The model2 response nests
    liquidation-leverage cells; we sum intensity per price bucket. Verify against your
    live response with test_coinglass.py, then tune keys here if the shape differs."""
    data = payload.get("data") if isinstance(payload, dict) else payload
    if not data:
        return []
    # Common shapes: {"y":[prices], "liq":[[x,yIndex,value],...]} or list of {price,amount}
    try:
        if isinstance(data, dict) and "y" in data and ("liq" in data or "data" in data):
            prices = [float(p) for p in data["y"]]
            cells = data.get("liq") or data.get("data") or []
            agg = {}
            for c in cells:
                yi = int(c[1]); val = float(c[2])
                if 0 <= yi < len(prices):
                    agg[prices[yi]] = agg.get(prices[yi], 0.0) + val
            if agg:
                mx = max(agg.values()) or 1.0
                return sorted(({"price": p, "intensity": round(v / mx, 3)} for p, v in agg.items()),
                              key=lambda x: x["price"])
        if isinstance(data, list):
            out = [{"price": float(d.get("price")), "intensity": float(d.get("amount", d.get("value", 1)))}
                   for d in data if d.get("price")]
            mx = max((o["intensity"] for o in out), default=1.0) or 1.0
            for o in out:
                o["intensity"] = round(o["intensity"] / mx, 3)
            return sorted(out, key=lambda x: x["price"])
    except (KeyError, IndexError, TypeError, ValueError):
        pass
    return []


def levels(symbol="BTC"):
    """Best-effort: paid API if key present, else manual CSV, else empty."""
    if CG_KEY:
        try:
            data = from_coinglass(symbol)
            if data:
                return data  # parse to [{price,intensity}] per your plan schema
        except Exception:
            pass
    return from_csv()


def nearest_clusters(spot, lvls, n=3):
    if not lvls:
        return {"above": [], "below": []}
    above = sorted([l for l in lvls if l["price"] > spot], key=lambda x: x["price"])[:n]
    below = sorted([l for l in lvls if l["price"] < spot], key=lambda x: -x["price"])[:n]
    return {"above": above, "below": below}


def suggest_short_beyond(spot, side, proposed_strike, lvls, buffer_pct=0.003):
    """If a heavy cluster sits between spot and the proposed short strike, suggest moving
    the short just BEYOND the cluster. side='call' (above) or 'put' (below). Returns
    (adjusted_strike, reason) or (proposed_strike, None) if no data / no conflict."""
    if not lvls:
        return proposed_strike, None
    heavy = [l for l in lvls if l["intensity"] >= 0.8]
    if side == "call":
        between = [l for l in heavy if spot < l["price"] <= proposed_strike]
        if between:
            top = max(between, key=lambda x: x["price"])
            return round(top["price"] * (1 + buffer_pct)), f"nudged call short beyond cluster {top['price']}"
    else:
        between = [l for l in heavy if proposed_strike <= l["price"] < spot]
        if between:
            bot = min(between, key=lambda x: x["price"])
            return round(bot["price"] * (1 - buffer_pct)), f"nudged put short beyond cluster {bot['price']}"
    return proposed_strike, None


if __name__ == "__main__":
    lv = levels("BTC")
    print(f"Loaded {len(lv) if isinstance(lv, list) else '?'} liquidation levels "
          f"({'Coinglass key' if CG_KEY else 'manual CSV'})")
    if isinstance(lv, list) and lv:
        print("nearest to 63000:", nearest_clusters(63000, lv))
