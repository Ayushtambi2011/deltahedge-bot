"""Gold (XAUUSD) 20/50 EMA trend strategy on the 15-minute chart — Delta India gold perp.

The 3 rules (from the playbook):
  1. DIRECTION  : 20 EMA above 50 EMA -> longs only; 20 below 50 -> shorts only. No clean cross -> no trade.
  2. ENTRY      : after the cross, wait for pullbacks to the EMA zone. Skip 1st & 2nd, take the 3rd clean retest.
                  Confirm the 1H trend agrees (1H 20/50 same direction).
  3. NUMBERS    : SL beyond the 50-EMA structure (recent swing). TP = 2.5x the SL distance. Risk 1% of $1000.
Then hands off — the trade resolves at TP or SL. NO 'step 4'.

This is an AUTOMATED INTERPRETATION of a discretionary chart method — tune the constants below.
Runs from run_desk.py --mode gold (a dedicated ~15-min workflow). Paper only.
"""
import os
import sys
import time
import json
import datetime

sys.path.insert(0, os.path.dirname(__file__))
import delta_client as dc
import paper_tracker
from signal_bot import send_telegram, load_dotenv

# --- config (verify the symbol with gold_test.py) ---
GOLD_SYMBOL = os.environ.get("GOLD_SYMBOL", "XAUUSD")
TP_MULT = 2.5              # TP = 2.5 x SL distance
RISK_PCT = 0.01           # 1% of account
ACCOUNT = 1000.0
SWING_LOOKBACK = 10       # candles used for the SL swing structure
RETESTS_REQUIRED = 3      # enter on the 3rd clean retest
FUT_FEE = 0.0005          # futures taker 0.05%
GST = 0.18
RES_SECS = {"5m": 300, "15m": 900, "1h": 3600, "1d": 86400}


def ema(vals, period):
    if len(vals) < period:
        return [None] * len(vals)
    k = 2 / (period + 1)
    seed = sum(vals[:period]) / period
    out = [None] * (period - 1) + [seed]
    for v in vals[period:]:
        out.append(v * k + out[-1] * (1 - k))
    return out


def candles(symbol, resolution, count=220):
    end = int(time.time())
    start = end - count * RES_SECS[resolution]
    raw = dc.get_candles(symbol, resolution, start, end)
    out = []
    for c in raw:
        try:
            out.append({"t": c.get("time") or c.get("timestamp"),
                        "o": float(c["open"]), "h": float(c["high"]),
                        "l": float(c["low"]), "c": float(c["close"])})
        except (KeyError, TypeError, ValueError):
            continue
    out.sort(key=lambda x: x["t"])
    return out


def trend_dir(cs):
    """+1 long, -1 short, 0 none — from 20/50 EMA of the given candles."""
    closes = [c["c"] for c in cs]
    e20, e50 = ema(closes, 20), ema(closes, 50)
    if not e20 or e20[-1] is None or e50[-1] is None:
        return 0, e20, e50
    return (1 if e20[-1] > e50[-1] else -1), e20, e50


def last_cross(e20, e50):
    """Index of the most recent 20/50 EMA crossover, or None."""
    last = None
    for i in range(1, len(e20)):
        if None in (e20[i], e50[i], e20[i - 1], e50[i - 1]):
            continue
        prev = e20[i - 1] - e50[i - 1]
        cur = e20[i] - e50[i]
        if prev == 0 or (prev < 0) != (cur < 0):
            last = i
    return last


def count_retests(cs, e20, e50, direction, since):
    """Count clean retests of the EMA zone after `since`. Returns (count, index_of_last_retest)."""
    n = 0
    last_idx = None
    armed = True
    for i in range(since, len(cs)):
        if e20[i] is None:
            continue
        c = cs[i]
        if direction > 0:                      # long: dip to 20 EMA, close back above
            touched = c["l"] <= e20[i]
            held = c["c"] > e20[i]
        else:                                  # short: poke 20 EMA, close back below
            touched = c["h"] >= e20[i]
            held = c["c"] < e20[i]
        if armed and touched and held:
            n += 1; last_idx = i; armed = False
        elif not touched:
            armed = True
    return n, last_idx


def scan():
    """Return a signal dict if the 3rd retest just completed on the latest closed candle, else None."""
    c15 = candles(GOLD_SYMBOL, "15m")
    if len(c15) < 60:
        return {"error": "not enough 15m candles (check GOLD_SYMBOL)"}
    direction, e20, e50 = trend_dir(c15)
    if direction == 0:
        return None
    cross = last_cross(e20, e50)
    if cross is None:
        return None
    n, last_idx = count_retests(c15, e20, e50, direction, cross)
    # entry only when the Nth retest completed on the most recent CLOSED candle
    if n < RETESTS_REQUIRED or last_idx != len(c15) - 1:
        return None
    # 1H confirmation
    c1h = candles(GOLD_SYMBOL, "1h", count=120)
    d1h, _, _ = trend_dir(c1h)
    if d1h != direction:
        return None

    entry = c15[-1]["c"]
    lows = [c["l"] for c in c15[-SWING_LOOKBACK:]]
    highs = [c["h"] for c in c15[-SWING_LOOKBACK:]]
    if direction > 0:
        sl = min(min(lows), e50[-1]) * 0.999
        tp = entry + TP_MULT * (entry - sl)
    else:
        sl = max(max(highs), e50[-1]) * 1.001
        tp = entry - TP_MULT * (sl - entry)
    risk_dist = abs(entry - sl)
    if risk_dist <= 0:
        return None
    qty_oz = round((ACCOUNT * RISK_PCT) / risk_dist, 4)          # size so a full SL = 1% ($10)
    notional = entry * qty_oz
    fees = notional * FUT_FEE * (1 + GST) * 2                    # entry + exit
    return {"direction": direction, "entry": round(entry, 2), "sl": round(sl, 2),
            "tp": round(tp, 2), "qty_oz": qty_oz, "risk": round(risk_dist * qty_oz, 2),
            "notional": round(notional, 2), "fees": round(fees, 4),
            "rr": TP_MULT, "e20": round(e20[-1], 2), "e50": round(e50[-1], 2)}


def format_signal(sig):
    d = "LONG" if sig["direction"] > 0 else "SHORT"
    side = "BUY" if sig["direction"] > 0 else "SELL"
    dot = "🟢" if sig["direction"] > 0 else "🔴"
    trend = "20>50 (up)" if sig["direction"] > 0 else "20<50 (down)"
    return "\n".join([
        f"{dot} <b>GOLD 20/50 EMA · 15m · {d}</b>",
        f"XAUUSD {sig['entry']:,.2f} · {trend} · 3rd retest · 1H agrees", "",
        f"  {side} {sig['qty_oz']} oz @ {sig['entry']:,.2f}  (entry)",
        f"  🎯 TP {sig['tp']:,.2f}   (+{sig['rr']}R)",
        f"  🛑 SL {sig['sl']:,.2f}",
        "",
        f"📦 Risk ${sig['risk']:.2f} (1% of $1000) · qty {sig['qty_oz']} oz · notional ${sig['notional']:,.0f}",
        f"Fees est ${sig['fees']:.2f} (futures 0.05% + GST, round-trip) · R:R 1:{sig['rr']}",
        "🔁 Hands off — let it hit TP or SL. Don't add a step 4.",
        "⚠️ PAPER — logged, not executed. Place the futures order yourself.",
    ])


# ---- paper lifecycle for gold (settles at TP/SL, not at expiry) ----
def _open_gold(sig):
    legs = [{"type": "future", "strike": sig["entry"], "side": sig["direction"],
             "entry_premium": sig["entry"], "symbol": GOLD_SYMBOL}]
    ctx = {"entry_spot": sig["entry"], "direction": sig["direction"], "sl": sig["sl"],
           "tp": sig["tp"], "qty_oz": sig["qty_oz"], "e20": sig["e20"], "e50": sig["e50"],
           "why": "20/50 EMA 3rd retest"}
    # store: net_credit unused(0), max_loss = the 1% risk in $
    paper_tracker.open_trade(GOLD_SYMBOL, "gold_ema", "perpetual", legs,
                             0.0, round(sig["risk"], 2), qty=1, context=ctx)


def check_exits(price):
    """Settle any open gold trades whose price has hit TP or SL."""
    rows = paper_tracker._load(paper_tracker.TRADES)
    changed = False
    for r in rows:
        if r.get("strategy") != "gold_ema" or r.get("status") != "open":
            continue
        ctx = json.loads(r.get("context") or "{}")
        d, entry, sl, tp, qty = ctx["direction"], ctx["entry_spot"], ctx["sl"], ctx["tp"], ctx["qty_oz"]
        hit = None
        if d > 0:
            if price <= sl: hit = sl
            elif price >= tp: hit = tp
        else:
            if price >= sl: hit = sl
            elif price <= tp: hit = tp
        if hit is None:
            continue
        pnl = d * (hit - entry) * qty
        fees = (entry + hit) * qty * FUT_FEE * (1 + GST)
        r["settle_spot"] = round(hit, 2); r["pnl_gross"] = round(pnl, 4)
        r["fees"] = round(fees, 4); r["pnl_net"] = round(pnl - fees, 4)
        r["status"] = "settled"; r["closed"] = datetime.date.today().isoformat()
        changed = True
    if changed:
        import csv
        with open(paper_tracker.TRADES, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=paper_tracker.FIELDS, extrasaction="ignore")
            w.writeheader()
            for r in rows:
                w.writerow({k: r.get(k, "") for k in paper_tracker.FIELDS})


def run():
    load_dotenv()
    try:
        c15 = candles(GOLD_SYMBOL, "15m", count=5)
        price = c15[-1]["c"] if c15 else None
    except Exception as e:
        print(f"gold candles fetch failed: {e}"); return
    if price:
        check_exits(price)                       # first, close any TP/SL hits
    sig = scan()
    if not sig:
        print("gold: no setup"); return
    if "error" in sig:
        print("gold:", sig["error"]); return
    # avoid duplicate entry while one is open
    for r in paper_tracker._load(paper_tracker.TRADES):
        if r.get("strategy") == "gold_ema" and r.get("status") == "open":
            print("gold: position already open — skip"); return
    send_telegram(format_signal(sig))
    _open_gold(sig)
    paper_tracker.build_performance()
    print(f"gold: SIGNAL {('LONG' if sig['direction']>0 else 'SHORT')} @ {sig['entry']}")


if __name__ == "__main__":
    run()
