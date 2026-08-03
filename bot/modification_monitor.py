"""IV & modification monitor. For each OPEN paper position, pull the live chain and
check whether it needs adjustment; if so, send a Telegram alert. Signal-only.

Triggers (tune in THRESHOLDS):
  - short-leg delta breach  -> position tested, consider roll/close
  - spot within X% of a short strike -> gamma risk near expiry
  - IV spike vs entry -> credit blown out, consider close
Run every 5-15 min while positions are open (cron/loop). See docs/04_ARCHITECTURE.md.
"""
import json
import os
import csv

import delta_client as dc
from signal_bot import send_telegram, load_dotenv

DATA = os.path.join(os.path.dirname(__file__), "..", "data")
TRADES = os.path.join(DATA, "paper_trades.csv")

THRESHOLDS = {
    "short_delta_breach": 0.30,   # short leg |delta| this high => tested
    "spot_near_strike_pct": 0.005,  # spot within 0.5% of a short strike
    "iv_spike_ratio": 1.5,        # current short-leg IV vs entry (needs entry IV logged)
}


def _open_trades():
    if not os.path.exists(TRADES):
        return []
    with open(TRADES) as f:
        return [r for r in csv.DictReader(f) if r.get("status") == "open"]


def check():
    load_dotenv()
    trades = _open_trades()
    if not trades:
        print("No open paper positions."); return
    for tr in trades:
        asset = tr["symbol"]
        try:
            chain = dc.get_chain(asset, None)
        except Exception as e:
            print(f"{asset}: chain fetch failed: {e}"); continue
        if not chain:
            continue
        spot = chain[0]["spot"]
        by_strike = {(r["type"], r["strike"]): r for r in chain}
        legs = json.loads(tr["legs_json"])
        alerts = []
        for leg in legs:
            if leg["side"] != -1:   # only short legs are the risk
                continue
            live = by_strike.get((leg["type"], leg["strike"]))
            d = abs(live["delta"]) if live and live.get("delta") is not None else None
            buyback = live.get("mid") if live else None
            breached = (d is not None and d >= THRESHOLDS["short_delta_breach"]) or \
                       (spot and abs(spot - leg["strike"]) / spot <= THRESHOLDS["spot_near_strike_pct"])
            if breached:
                roll = _suggest_roll(chain, leg["type"], spot)
                dt = f"{d:.2f}" if d is not None else "?"
                block = [f"Tested: SELL {leg['type'].upper()} {leg['strike']:.0f} (Δ {dt})"]
                if roll:
                    block.append(f"  • BUY to close  {leg['type'].upper()} {leg['strike']:.0f} @ ~{buyback}")
                    block.append(f"  • SELL to open  {leg['type'].upper()} {roll['strike']:.0f} @ ~{roll['mid']} (Δ {roll['delta']:.2f})")
                alerts.append("\n".join(block))
        if alerts:
            msg = (f"⚠️ <b>ADJUST · {asset} {tr['strategy'].replace('_',' ').upper()}</b> · spot {spot:,.0f}\n\n"
                   + "\n".join(alerts) +
                   "\n\nApply the roll on the SAME quantity as your position, or CLOSE the whole "
                   "position at your SL.\n⚠️ PAPER — you decide & place it (docs/03).")
            send_telegram(msg)
            print(f"alert sent for {tr['id']}")
        else:
            print(f"{tr['id']}: ok")


def _suggest_roll(chain, kind, spot, target_delta=0.16):
    """Suggest a new short strike further OTM at ~target delta (a roll target)."""
    cands = [r for r in chain if r["type"] == kind and r.get("delta") is not None
             and r.get("mid") is not None]
    if not cands:
        return None
    # further OTM than current: for calls higher strike, for puts lower strike
    cands = [r for r in cands if (r["strike"] > spot if kind == "call" else r["strike"] < spot)]
    if not cands:
        return None
    best = min(cands, key=lambda r: abs(abs(r["delta"]) - target_delta))
    return {"strike": best["strike"], "delta": abs(best["delta"]), "mid": best["mid"]}


if __name__ == "__main__":
    check()
