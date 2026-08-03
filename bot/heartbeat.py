"""Daily heartbeat / digest. Sends ONE Telegram message a day so you always know the
desk is alive, plus a summary of yesterday's activity. If it goes silent, your VPS is down.

Run once a day via cron (see deploy/crontab.txt).
"""
import csv
import datetime
import json
import os

from signal_bot import send_telegram, load_dotenv

DATA = os.path.join(os.path.dirname(__file__), "..", "data")


def _read_perf():
    p = os.path.join(DATA, "performance.json")
    if os.path.exists(p):
        with open(p) as f:
            return json.load(f)
    return {}


def _count_today(fname, col="ts"):
    p = os.path.join(DATA, fname)
    today = datetime.date.today().isoformat()
    if not os.path.exists(p):
        return 0
    n = 0
    with open(p) as f:
        for r in csv.DictReader(f):
            v = r.get(col) or r.get("opened") or ""
            if v.startswith(today):
                n += 1
    return n


def main():
    load_dotenv()
    perf = _read_perf()
    strat = perf.get("strategies", {})
    net = round(sum(s.get("net_after_tax", s.get("net", 0)) for s in strat.values()), 4)
    best = max(strat.items(), key=lambda kv: kv[1].get("net_after_tax", 0), default=(None, {}))
    sigs_today = _count_today("signals.csv")
    trades_today = _count_today("paper_trades.csv", "opened")
    open_pos = perf.get("open_positions", 0)

    lines = [f"🟢 <b>DeltaHedge daily</b> · {datetime.date.today().isoformat()}",
             "Desk is alive.", "",
             f"Signals today: {max(sigs_today, trades_today)}",
             f"Open paper positions: {open_pos}",
             f"Settled total: {perf.get('total_settled', 0)}",
             f"Net P&L (after tax): {net:+.4f} /contract"]
    if best[0]:
        lines.append(f"Best strategy so far: {best[0].replace('_',' ').title()} "
                     f"({best[1].get('net_after_tax',0):+.4f})")
    if max(sigs_today, trades_today) == 0:
        lines.append("\n⚠️ No signals generated today — check desk.log if a trade was expected.")
    lines.append("\nPaper only · no orders placed.")
    send_telegram("\n".join(lines))
    print("heartbeat sent")


if __name__ == "__main__":
    main()
