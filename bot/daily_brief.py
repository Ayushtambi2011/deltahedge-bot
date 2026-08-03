"""Rich daily (and Monday-weekly) brief to Telegram at 07:00 IST.
Combines: US Forex news + market sentiment + order blocks / support-resistance (from Delta
OI) + max pain + liquidation zones (if you supply them). Heatmap image is NOT included —
Coinglass heatmap is paid; we use Delta's own OI positioning instead (free, real).

Run:  python3 daily_brief.py         (weekly section auto-adds on Mondays)
      python3 daily_brief.py --weekly
"""
import argparse
import datetime

import delta_client as dc
import market_intel
import liquidation
import events
import news_digest
from signal_bot import send_telegram, load_dotenv


def _liq_block(asset, spot):
    lv = liquidation.levels(asset)
    if not (isinstance(lv, list) and lv):
        return None
    nc = liquidation.nearest_clusters(spot, lv)
    up = ", ".join(f"{l['price']:.0f}" for l in nc["above"]) or "—"
    dn = ", ".join(f"{l['price']:.0f}" for l in nc["below"]) or "—"
    return f"🧲 Liq above: {up} | below: {dn}"


def asset_block(asset):
    try:
        chain = dc.get_chain(asset, dc.nearest_expiry(asset))
    except Exception as e:
        return f"<b>{asset}</b>: data error ({e})"
    intel = market_intel.analyze(chain)
    if not intel:
        return f"<b>{asset}</b>: no chain"
    spot = intel["spot"]
    lines = [f"<b>{asset}</b> · spot {spot:.0f}",
             f"  Bias: <b>{intel['bias']}</b>  (PCR {intel['pcr']}, skew {intel['skew']})",
             f"  🟩 Resistance (call OI): {', '.join(f'{s:.0f}' for s in intel['resistance'])}",
             f"  🟥 Support (put OI): {', '.join(f'{s:.0f}' for s in intel['support'])}",
             f"  🎯 Max pain: {intel['max_pain']:.0f}"]
    lb = _liq_block(asset, spot)
    if lb:
        lines.append("  " + lb)
    if intel["bias_notes"]:
        lines.append("  · " + "; ".join(intel["bias_notes"]))
    return "\n".join(lines)


def build(weekly=False):
    data = events.fetch()
    parts = [f"📊 <b>DeltaHedge Daily Brief</b> · {datetime.date.today().isoformat()}", ""]
    # 1) US news
    parts.append(news_digest.daily(data))
    parts.append("")
    # 2) market intel per asset
    parts.append("📈 <b>Market Structure</b>")
    for a in ("BTC", "ETH"):
        parts.append(asset_block(a))
    parts.append("")
    # 3) weekly extras on Monday
    if weekly or datetime.date.today().weekday() == 0:
        parts.append(news_digest.weekly(data))
        try:
            import learning_review
            parts.append("")
            parts.append(learning_review.summary_text())
        except Exception:
            pass
    parts.append("\n<i>Educational, not advice. OI-based levels show likely liquidity, not a "
                 "guaranteed direction. Confirm with price action.</i>")
    return "\n".join(parts)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--weekly", action="store_true")
    args = ap.parse_args()
    load_dotenv()
    send_telegram(build(weekly=args.weekly))
    print("daily brief sent")


if __name__ == "__main__":
    main()
