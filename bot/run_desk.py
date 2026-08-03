"""DeltaHedge desk orchestrator — the 24x7 entry point.

Each run:
  1. Pull the live BTC/ETH nearest-expiry chain (real premiums, IV, greeks).
  2. Record a snapshot (builds your real dataset forward).
  3. Pick strategy from IV regime, build the structure from REAL mids.
  4. Send a Telegram signal + log it as a PAPER trade.
  5. Rebuild data/performance.json for the dashboard.
NO orders are placed. Signal + log only.

Entry run (cron, 1-2x/day):   python3 run_desk.py --mode entry
Monitor run (cron, every 10m): python3 run_desk.py --mode monitor
"""
import argparse
import json
import os
import sys
import statistics

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backtester"))
import delta_client as dc
import record_chain
import paper_tracker
import modification_monitor
import events
import greeks
import liquidation
import market_intel
import strategy_selector
from signal_bot import send_telegram, load_dotenv
import chain_loader

BUILDERS = {
    "iron_condor": lambda chain, trend: chain_loader.build_iron_condor(chain),
    "long_strangle": lambda chain, trend: chain_loader.build_long_strangle(chain),
    "broken_wing_butterfly": lambda chain, trend: chain_loader.build_broken_wing_butterfly(chain, trend or 0.0),
}

CONTRACT_SIZE = {"BTC": 0.001, "ETH": 0.01}


def atm_iv(chain):
    spot = chain[0]["spot"]
    near = sorted((r for r in chain if r["iv"]), key=lambda r: abs(r["strike"] - spot))[:6]
    ivs = [r["iv"] for r in near if r["iv"]]
    return statistics.median(ivs) if ivs else None


def pick_regime(iv, event_soon):
    # Placeholder until IV RANK is built from recorded history (docs/05_LEARNING_LOOP.md).
    # Event-aware: a crypto-mover in the next few hours => elevated expected vol.
    if event_soon:
        return "event-risk", "iron_condor"   # sell richer premium but flag; wider wings advised
    if iv is None:
        return "quiet", "iron_condor"
    return ("volatile", "iron_condor") if iv > 90 else ("quiet", "iron_condor")


def _pnl_at(legs, terminal, credit, mult):
    """Expiry PnL of the structure at a terminal spot (piecewise-linear)."""
    settle = 0.0
    for leg in legs:
        intr = max(0.0, terminal - leg["strike"]) if leg["type"] == "call" \
            else max(0.0, leg["strike"] - terminal)
        settle += leg["side"] * intr
    return credit + settle * mult


def credit_and_maxloss(legs, mult, spot):
    """Generic for any defined-risk structure. Max loss = min PnL over the kink points
    (all strikes) plus the tails (0 and 3x spot)."""
    credit = sum(-leg["side"] * (leg.get("entry_premium") or 0) for leg in legs) * mult
    terminals = sorted({l["strike"] for l in legs} | {0.0, (spot or 0) * 3})
    worst = min(_pnl_at(legs, t, credit, mult) for t in terminals)
    max_loss = -worst if worst < 0 else 0.0
    return credit, max_loss


def max_profit(legs, credit, mult, spot):
    terminals = sorted({l["strike"] for l in legs} | {0.0, (spot or 0) * 3})
    best = max(_pnl_at(legs, t, credit, mult) for t in terminals)
    return best


def breakevens(legs, credit, mult, spot):
    if not spot:
        return []
    lo, hi, steps = spot * 0.5, spot * 1.6, 700
    bes, prev = [], None
    for i in range(steps + 1):
        t = lo + (hi - lo) * i / steps
        p = _pnl_at(legs, t, credit, mult)
        if prev is not None and (prev < 0) != (p < 0):
            bes.append(round(t))
        prev = p
    return bes


def pop_estimate(legs, chain):
    """Rough probability of profit from option deltas. Credit structures: 1 - sum|short delta|.
    Debit (long) structures: sum|long delta|. Approximate, for context only."""
    def dlt(l):
        row = greeks._lookup(chain, l["type"], l["strike"])
        return abs(row["delta"]) if row and row.get("delta") is not None else 0.0
    shorts = [l for l in legs if l["side"] < 0]
    net = sum(-l["side"] * (l.get("entry_premium") or 0) for l in legs)
    if net > 0 and shorts:                       # credit
        return max(0.0, 1.0 - sum(dlt(l) for l in shorts))
    longs = [l for l in legs if l["side"] > 0]   # debit / long vol
    return min(1.0, sum(dlt(l) for l in longs))


# --- account sizing ---
ACCOUNT_USD = 1000.0
RESERVE_PCT = 0.30              # keep 30% of account FREE for later modifications/rolls
MARGIN_PER_TRADE = 100.0       # $ margin budget allocated to a single signal


def size_qty(max_loss_per_contract):
    """Contracts sized so this trade's margin (~max loss) fits MARGIN_PER_TRADE."""
    if not max_loss_per_contract or max_loss_per_contract <= 0:
        return 1
    return max(1, int(MARGIN_PER_TRADE / max_loss_per_contract))


def tp_sl_prices(credit):
    """Actual NET PREMIUM price to close at, not a '50%/2x' formula.
    Credit trade: buy-to-close cheap = profit. Debit trade: sell high = profit."""
    if credit > 0:
        return round(0.5 * credit, 4), round(2 * credit, 4), "buy-to-close"
    debit = -credit
    return round(2 * debit, 4), round(0.5 * debit, 4), "sell-to-close"


def already_open(asset, strat, exp_s):
    for r in paper_tracker._load(paper_tracker.TRADES):
        if (r.get("status") == "open" and r.get("symbol") == asset
                and r.get("strategy") == strat and r.get("expiry") == exp_s):
            return True
    return False


def format_signal(asset, strat, exp, exp_type, legs, chain, iv, intel, mult, why,
                  soon, liq_notes, warns, ng, credit, max_loss):
    spot = chain[0]["spot"]
    mp = max_profit(legs, credit, mult, spot)
    bes = breakevens(legs, credit, mult, spot)
    pop = pop_estimate(legs, chain)
    dot = "🟢" if credit > 0 else "🟡"
    lines = [f"{dot} <b>{asset} {strat.replace('_',' ').upper()}</b> · {exp_type.upper()} · exp {exp}",
             f"spot {spot:,.0f} · ATM IV {iv:.0f}% · <i>{why}</i>" if iv else f"spot {spot:,.0f} · <i>{why}</i>",
             ""]
    for l in legs:
        s = "SELL" if l["side"] < 0 else "BUY "
        lines.append(f"  {s} {l['type'].upper()} {l['strike']:.0f} @ {l['entry_premium']}")
    qty = size_qty(max_loss)
    tp, sl, action = tp_sl_prices(credit)
    net_lbl = "credit" if credit > 0 else "debit"
    reserve = round(ACCOUNT_USD * RESERVE_PCT)
    tot_credit = abs(credit) * qty
    tot_ml = max_loss * qty
    lines += ["",
              f"📦 <b>Qty {qty} contracts</b> · est. margin ${tot_ml:,.0f} · ${reserve} kept free for mods",
              f"Per-contract: {net_lbl} {round(abs(credit),4)} · max loss {round(max_loss,4)} · max profit {round(mp,4)}",
              f"Position: {net_lbl} ${tot_credit:,.2f} · max loss ${tot_ml:,.2f}",
              f"Breakevens {' – '.join(f'{b:,.0f}' for b in bes) if bes else '—'}",
              f"POP ~ {pop*100:.0f}%",
              f"🎯 TP {action} @ net {tp} · 🛑 SL @ net {sl}",
              f"Net Δ {ng['delta']:+.3f} Γ {ng['gamma']:+.4f} Θ {ng['theta']:+.1f} V {ng['vega']:+.1f}"]
    if intel:
        lines.append(f"Context: support {intel['support'][0]:.0f} / resist {intel['resistance'][0]:.0f} "
                     f"/ max pain {intel['max_pain']:.0f} · bias {intel['bias']}")
    if soon:
        lines.append("⚡ event: " + ", ".join(e["title"] for e in soon[:2]))
    if liq_notes:
        lines.append("🧲 " + "; ".join(liq_notes))
    if warns:
        lines.append("⚠️ " + "; ".join(warns))
    lines.append("⚠️ PAPER — logged, not executed. Place as LIMIT orders.")
    return "\n".join(lines)


def entry_run():
    load_dotenv()
    # --- event context (shared across assets) ---
    try:
        ffdata = events.fetch()
    except Exception as e:
        ffdata = None
        print(f"events feed failed: {e}")
    blackout, bl_ev = events.is_blackout(data=ffdata) if ffdata else (False, None)
    soon = events.event_within(8, data=ffdata) if ffdata else []
    if blackout:
        msg = (f"⛔ <b>Entry HOLD — event blackout</b>\n{bl_ev['title']} "
               f"({bl_ev['country']} {bl_ev['impact']}) at {bl_ev['time_utc'].strftime('%H:%M UTC')}.\n"
               "No new entries in the print window. Wait for the dust to settle.")
        send_telegram(msg)
        print("Entry skipped: event blackout —", bl_ev["title"])
        return

    for asset in ("BTC", "ETH"):
        mult = CONTRACT_SIZE.get(asset, 1.0)
        trend = strategy_selector.trend_score(asset)
        lvls = liquidation.levels(asset)
        try:
            record_chain.record(asset)              # snapshot once per asset (nearest expiry)
        except Exception as e:
            print(f"{asset}: record failed: {e}")

        # trade BOTH the daily and the weekly expiry (request: daily + weekly)
        expiries = [("daily", dc.nearest_expiry(asset))]
        wk = dc.weekly_expiry(asset)
        if wk and wk != expiries[0][1]:
            expiries.append(("weekly", wk))

        for exp_type, exp in expiries:
            if not exp:
                continue
            exp_s = exp.isoformat()
            try:
                chain = dc.get_chain(asset, exp)
            except Exception as e:
                print(f"{asset} {exp_type}: chain fetch failed: {e}"); continue
            if not chain:
                print(f"{asset} {exp_type}: empty chain"); continue
            iv = atm_iv(chain)
            spot = chain[0]["spot"]
            intel = market_intel.analyze(chain)

            picks = strategy_selector.select(iv, asset, event_soon=bool(soon), in_blackout=False)
            if not picks:
                print(f"{asset} {exp_type}: NO TRADE"); continue

            for strat, why in picks:
                strat_label = strat if exp_type == "daily" else strat + "_wk"
                if already_open(asset, strat_label, exp_s):   # no duplicate signals for the same setup
                    print(f"{asset} {exp_type}: {strat_label} already open — skip"); continue
                legs = BUILDERS[strat](chain, trend)
                if not legs:
                    print(f"{asset} {exp_type}: could not build {strat}"); continue

                liq_notes = []
                if isinstance(lvls, list) and lvls:
                    for l in legs:
                        if l["side"] == -1:
                            nk, note = liquidation.suggest_short_beyond(spot, l["type"], l["strike"], lvls)
                            if note:
                                l["strike"] = nk; liq_notes.append(note)

                ok, ng, warns = greeks.check(legs, chain, asset, spot, strategy=strat)
                credit, max_loss = credit_and_maxloss(legs, mult, spot)
                msg = format_signal(asset, strat, exp, exp_type, legs, chain, iv, intel,
                                    mult, why, soon, liq_notes, warns, ng, credit, max_loss)
                send_telegram(msg)
                paper_tracker.open_trade(asset, strat_label, exp_s, legs,
                                         round(credit, 4), round(max_loss, 4))
                print(f"{asset} {exp_type}: signalled {strat_label} (greeks_ok={ok}) — {why}")
    perf = paper_tracker.build_performance()
    print(f"performance.json updated · settled={perf['total_settled']} open={perf['open_positions']}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["entry", "monitor"], default="entry")
    args = ap.parse_args()
    if args.mode == "monitor":
        modification_monitor.check()
    else:
        entry_run()


if __name__ == "__main__":
    main()
