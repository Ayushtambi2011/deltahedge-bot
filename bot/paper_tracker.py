"""Paper-trade tracker: turns Telegram signals into logged paper trades, settles them
at expiry from recorded spot, and builds data/performance.json for the dashboard.

No real money. This is how you find out, over 1-2 months, which strategy actually works.

Files:
  data/paper_trades.csv   one row per paper trade (open -> settled)
  data/performance.json   per-strategy + overall stats + equity curve (dashboard reads this)

Run nightly (cron) after record_chain.py so settlement spot is available.
"""
import csv
import json
import os
import datetime

DATA = os.path.join(os.path.dirname(__file__), "..", "data")
TRADES = os.path.join(DATA, "paper_trades.csv")
PERF = os.path.join(DATA, "performance.json")
CHAINS = os.path.join(DATA, "chains")

FIELDS = ["id", "opened", "symbol", "strategy", "expiry", "legs_json", "net_credit",
          "max_loss", "qty", "status", "settle_spot", "pnl_gross", "fees", "pnl_net",
          "closed", "context"]

# --- fee model mirrors backtester/config.py (Delta exact) ---
FEE_PCT_NOTIONAL = 0.0001
FEE_CAP_PREMIUM = 0.035
GST = 0.18
CONTRACT_SIZE = {"BTC": 0.001, "ETH": 0.01}
FNO_TAX_RATE = 0.30


def _load(path):
    if not os.path.exists(path):
        return []
    with open(path) as f:
        return list(csv.DictReader(f))


def open_trade(symbol, strategy, expiry, legs, net_credit, max_loss, qty=1, context=None):
    """legs: list of dict(type,strike,side,entry_premium). Append an open paper trade.
    context: dict of entry conditions (IV, greeks, PCR, bias...) stored for the learning engine.
    Rewrites the whole file so a changed header (new columns) stays consistent."""
    os.makedirs(DATA, exist_ok=True)
    rows = _load(TRADES)
    tid = f"{symbol}-{strategy}-{datetime.datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
    row = {"id": tid, "opened": datetime.datetime.utcnow().isoformat(), "symbol": symbol,
           "strategy": strategy, "expiry": expiry, "legs_json": json.dumps(legs),
           "net_credit": net_credit, "max_loss": max_loss, "qty": qty, "status": "open",
           "settle_spot": "", "pnl_gross": "", "fees": "", "pnl_net": "", "closed": "",
           "context": json.dumps(context or {})}
    rows.append(row)
    with open(TRADES, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in FIELDS})
    return tid


def _fee(spot, premium_dollars):
    notional = spot
    raw = min(FEE_PCT_NOTIONAL * notional, FEE_CAP_PREMIUM * max(premium_dollars, 0.0))
    return raw * (1 + GST)


def _settle_spot(symbol, expiry):
    """Best-effort settlement spot: the spot recorded on/after the expiry date."""
    if not os.path.isdir(CHAINS):
        return None
    import glob
    for p in sorted(glob.glob(os.path.join(CHAINS, f"{symbol}_*.csv"))):
        date = os.path.basename(p).split("_")[1].replace(".csv", "")
        if date >= expiry:
            with open(p) as f:
                r = next(csv.DictReader(f), None)
                if r and r.get("spot"):
                    return float(r["spot"])
    return None


def settle_open_trades():
    rows = _load(TRADES)
    today = datetime.date.today().isoformat()
    changed = False
    for r in rows:
        if r["status"] != "open" or r["expiry"] > today:
            continue
        spot = _settle_spot(r["symbol"], r["expiry"])
        if spot is None:
            continue
        legs = json.loads(r["legs_json"])
        mult = CONTRACT_SIZE.get(r["symbol"], 1.0)
        pnl = 0.0
        fees = 0.0
        for leg in legs:
            intrinsic = max(0.0, spot - leg["strike"]) if leg["type"] == "call" \
                else max(0.0, leg["strike"] - spot)
            entry = leg.get("entry_premium", 0.0)
            pnl += leg["side"] * (intrinsic - entry) * mult
            fees += _fee(spot, entry * mult) + _fee(spot, intrinsic * mult)
        r["settle_spot"] = round(spot, 2)
        r["pnl_gross"] = round(pnl, 4)
        r["fees"] = round(fees, 4)
        r["pnl_net"] = round(pnl - fees, 4)
        r["status"] = "settled"
        r["closed"] = today
        changed = True
    if changed:
        with open(TRADES, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=FIELDS)
            w.writeheader()
            w.writerows(rows)
    return rows


def build_performance():
    rows = settle_open_trades()
    settled = [r for r in rows if r["status"] == "settled"]
    strategies = {}
    equity = 0.0
    curve = []
    for r in sorted(settled, key=lambda x: x["closed"] or ""):
        net = float(r["pnl_net"] or 0)
        equity += net
        curve.append({"date": r["closed"], "equity": round(equity, 4)})
        s = strategies.setdefault(r["strategy"], {"trades": 0, "wins": 0, "gross_win": 0.0,
                                                  "gross_loss": 0.0, "net": 0.0})
        s["trades"] += 1
        s["net"] += net
        if net > 0:
            s["wins"] += 1; s["gross_win"] += net
        else:
            s["gross_loss"] += net
    for name, s in strategies.items():
        s["win_rate"] = round(100 * s["wins"] / s["trades"], 1) if s["trades"] else 0
        s["profit_factor"] = round(s["gross_win"] / abs(s["gross_loss"]), 2) if s["gross_loss"] else None
        s["net"] = round(s["net"], 4)
        s["net_after_tax"] = round(s["net"] - FNO_TAX_RATE * max(0.0, s["net"]), 4)
    perf = {
        "updated": datetime.datetime.utcnow().isoformat(),
        "open_positions": sum(1 for r in rows if r["status"] == "open"),
        "total_settled": len(settled),
        "equity_curve": curve,
        "strategies": strategies,
    }
    with open(PERF, "w") as f:
        json.dump(perf, f, indent=2)
    return perf


if __name__ == "__main__":
    p = build_performance()
    print(json.dumps(p, indent=2))
