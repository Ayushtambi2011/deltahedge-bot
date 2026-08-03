"""Learning review — the HONEST 'keep learning' system. No magic, no promise of rising TP.
It reads SETTLED paper trades and reports, with evidence, what is and isn't working:
per-strategy expectancy, timing (entry-hour) performance, and recurring mistakes (trades that
blew through to max loss). It writes dated lessons to data/lessons.md and can Telegram a
weekly summary. You approve any rule change — the system informs decisions, it doesn't trade.

Needs data. Below MIN_TRADES settled it just says 'collecting'.
Run weekly:  python3 learning_review.py
"""
import csv
import datetime
import os

DATA = os.path.join(os.path.dirname(__file__), "..", "data")
TRADES = os.path.join(DATA, "paper_trades.csv")
LESSONS = os.path.join(DATA, "lessons.md")
MIN_TRADES = 15


def _settled():
    if not os.path.exists(TRADES):
        return []
    out = []
    with open(TRADES) as f:
        for r in csv.DictReader(f):
            if r.get("status") == "settled" and r.get("pnl_net") not in (None, ""):
                try:
                    r["pnl_net"] = float(r["pnl_net"]); r["max_loss"] = float(r.get("max_loss") or 0)
                    out.append(r)
                except ValueError:
                    pass
    return out


def _stats(rows):
    n = len(rows)
    wins = [r for r in rows if r["pnl_net"] > 0]
    losses = [r for r in rows if r["pnl_net"] <= 0]
    gw = sum(r["pnl_net"] for r in wins)
    gl = sum(r["pnl_net"] for r in losses)
    return {
        "n": n, "win_rate": round(100 * len(wins) / n, 1) if n else 0,
        "avg_win": round(gw / len(wins), 4) if wins else 0,
        "avg_loss": round(gl / len(losses), 4) if losses else 0,
        "net": round(gw + gl, 4),
        "profit_factor": round(gw / abs(gl), 2) if gl else None,
    }


def _by(rows, key):
    groups = {}
    for r in rows:
        groups.setdefault(key(r), []).append(r)
    return {k: _stats(v) for k, v in groups.items()}


def analyze():
    rows = _settled()
    if len(rows) < MIN_TRADES:
        return {"ready": False, "n": len(rows)}
    overall = _stats(rows)
    by_strat = _by(rows, lambda r: r["strategy"])
    by_hour = _by(rows, lambda r: (r.get("opened") or "")[11:13] or "??")
    # mistakes: trades that blew to near max loss (the hedge failed to contain it)
    blowups = [r for r in rows if r["max_loss"] and r["pnl_net"] <= -0.9 * r["max_loss"]]
    lessons = []
    for s, st in sorted(by_strat.items(), key=lambda kv: kv[1]["net"]):
        if st["n"] >= 5 and (st["profit_factor"] or 0) < 1:
            lessons.append(f"❌ {s}: {st['n']} trades, PF {st['profit_factor']}, net {st['net']} — "
                           f"losing after fees. Tighten its trigger or retire it.")
        elif st["n"] >= 5 and (st["profit_factor"] or 0) >= 1.2:
            lessons.append(f"✅ {s}: {st['n']} trades, PF {st['profit_factor']}, net {st['net']} — "
                           f"working; keep and consider more weight.")
    if blowups:
        lessons.append(f"⚠️ {len(blowups)} trade(s) hit ~max loss — review whether entries were "
                       f"too close to events or wings too narrow (docs/03).")
    # timing insight
    best_hours = sorted((h for h in by_hour if by_hour[h]["n"] >= 3),
                        key=lambda h: -by_hour[h]["win_rate"])[:2]
    if best_hours:
        lessons.append("🕒 Best entry hours (UTC): " +
                       ", ".join(f"{h} ({by_hour[h]['win_rate']}%)" for h in best_hours))
    return {"ready": True, "overall": overall, "by_strategy": by_strat,
            "by_hour": by_hour, "blowups": len(blowups), "lessons": lessons}


def summary_text():
    a = analyze()
    if not a["ready"]:
        return f"🧠 <b>Learning</b>: collecting data ({a['n']}/{MIN_TRADES} settled). Lessons unlock soon."
    o = a["overall"]
    lines = [f"🧠 <b>Learning review</b> — {o['n']} settled trades",
             f"Win {o['win_rate']}% · PF {o['profit_factor']} · net {o['net']}"]
    lines += a["lessons"][:6]
    return "\n".join(lines)


def write_lessons():
    a = analyze()
    os.makedirs(DATA, exist_ok=True)
    stamp = datetime.date.today().isoformat()
    with open(LESSONS, "a") as f:
        f.write(f"\n\n## {stamp} — learning review\n")
        if not a["ready"]:
            f.write(f"Collecting data: {a['n']}/{MIN_TRADES} settled trades. No conclusions yet.\n")
            return a
        o = a["overall"]
        f.write(f"Overall: {o['n']} trades, win {o['win_rate']}%, PF {o['profit_factor']}, net {o['net']}.\n\n")
        f.write("Per strategy:\n")
        for s, st in sorted(a["by_strategy"].items(), key=lambda kv: -kv[1]["net"]):
            f.write(f"- {s}: {st['n']} trades, win {st['win_rate']}%, PF {st['profit_factor']}, net {st['net']}\n")
        f.write("\nLessons:\n")
        for l in a["lessons"]:
            f.write(f"- {l}\n")
    return a


if __name__ == "__main__":
    from signal_bot import send_telegram, load_dotenv
    load_dotenv()
    a = write_lessons()
    print(summary_text())
    try:
        send_telegram(summary_text())
    except Exception as e:
        print("telegram send skipped:", e)
