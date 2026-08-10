"""Realistic intraday TP/SL settlement for OPTIONS positions.

Instead of holding every trade to expiry (the old, harsh model), this re-prices each open
option position from the LIVE chain every run and closes it the moment the net premium hits
the TP or SL — capturing IV changes, delta drift and time decay, i.e. how you'd actually
trade it. Run from run_desk.py --mode monitor (every 15 min).

TP/SL match the signal message:
  credit trade : TP when buy-back cost <= 0.5x credit ; SL when >= 2x credit
  debit  trade : TP when value >= 2x debit ; SL when value <= 0.5x debit
"""
import csv
import datetime
import json

import delta_client as dc
import paper_tracker as pt

CONTRACT_SIZE = {"BTC": 0.001, "ETH": 0.01}
FEE_PCT_NOTIONAL = 0.0001
FEE_CAP_PREMIUM = 0.035
GST = 0.18
TP_CREDIT, SL_CREDIT = 0.5, 2.0
TP_DEBIT, SL_DEBIT = 2.0, 0.5


def _fee(spot, prem_dollars):
    raw = min(FEE_PCT_NOTIONAL * (spot or 0), FEE_CAP_PREMIUM * max(prem_dollars, 0.0))
    return raw * (1 + GST)


def check():
    rows = pt._load(pt.TRADES)
    opens = [r for r in rows if r.get("status") == "open" and r.get("strategy") != "gold_ema"]
    if not opens:
        print("option exits: no open option positions"); return
    chains = {}
    changed = 0
    today = datetime.date.today().isoformat()

    for r in opens:
        asset, exp = r["symbol"], r["expiry"]
        key = (asset, exp)
        if key not in chains:
            try:
                ed = datetime.date.fromisoformat(exp)
                ch = dc.get_chain(asset, ed)
                chains[key] = {(c["type"], c["strike"]): c for c in ch}
            except Exception as e:
                print(f"exits: chain fetch failed {asset} {exp}: {e}")
                chains[key] = {}
        cmap = chains[key]
        if not cmap:
            continue

        legs = json.loads(r["legs_json"])
        mult = CONTRACT_SIZE.get(asset, 1.0)
        v_now, fees, priced = 0.0, 0.0, True
        for leg in legs:
            row = cmap.get((leg["type"], leg["strike"]))
            mid = row.get("mid") if row else None
            if mid is None:
                priced = False; break
            v_now += leg["side"] * mid * mult
            fees += _fee(row.get("spot"), mid * mult)
        if not priced:
            continue

        credit = float(r.get("net_credit") or 0)     # per-contract $, +=credit / -=debit
        hit = None
        if credit > 0:                                # credit structure
            cost_to_close = -v_now
            if cost_to_close <= TP_CREDIT * credit:
                hit = ("TP", credit - cost_to_close)
            elif cost_to_close >= SL_CREDIT * credit:
                hit = ("SL", credit - cost_to_close)
        else:                                         # debit / long-vol structure
            debit = -credit
            if debit > 0 and v_now >= TP_DEBIT * debit:
                hit = ("TP", v_now - debit)
            elif debit > 0 and v_now <= SL_DEBIT * debit:
                hit = ("SL", v_now - debit)

        if hit:
            reason, pnl = hit
            r["pnl_gross"] = round(pnl, 4)
            r["fees"] = round(fees, 4)
            r["pnl_net"] = round(pnl - fees, 4)
            r["status"] = "settled"
            r["closed"] = today
            try:
                ctx = json.loads(r.get("context") or "{}")
                ctx["exit"] = reason
                r["context"] = json.dumps(ctx)
            except json.JSONDecodeError:
                pass
            changed += 1

    if changed:
        with open(pt.TRADES, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=pt.FIELDS, extrasaction="ignore")
            w.writeheader()
            for r in rows:
                w.writerow({k: r.get(k, "") for k in pt.FIELDS})
        pt.build_performance()
        print(f"option exits: {changed} closed at TP/SL")
    else:
        print("option exits: none hit TP/SL yet")


if __name__ == "__main__":
    check()
