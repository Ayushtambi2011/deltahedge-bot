"""News digest to Telegram.
- DAILY: high-impact (RED) USD events happening TODAY.
- WEEKLY: on Mondays, all high-impact USD events for the week.
Source: ForexFactory feed (events.py). No key needed.

Run daily (see deploy/crontab.txt). On Mondays it appends the weekly digest.
Force weekly with:  python3 news_digest.py --weekly
"""
import argparse
import datetime

import events
from signal_bot import send_telegram, load_dotenv

IST = datetime.timezone(datetime.timedelta(hours=5, minutes=30))


def _red_usd(data):
    """High-impact (red) USD events, sorted by time."""
    out = []
    for ev in data:
        if (ev.get("country") or "").upper() == "USD" and (ev.get("impact") == "High"):
            t = events._utc(ev)
            if t:
                out.append({"title": ev["title"], "time": t,
                            "forecast": ev.get("forecast"), "previous": ev.get("previous")})
    return sorted(out, key=lambda e: e["time"])


def _fmt(e):
    ist = e["time"].astimezone(IST)
    fc = f" · f:{e['forecast']}" if e.get("forecast") else ""
    pv = f" p:{e['previous']}" if e.get("previous") else ""
    return f"🔴 {ist.strftime('%a %H:%M IST')} — <b>{e['title']}</b>{fc}{pv}"


def daily(data=None):
    data = data or events.fetch()
    today = datetime.datetime.now(datetime.timezone.utc).date()
    todays = [e for e in _red_usd(data) if e["time"].astimezone(datetime.timezone.utc).date() == today]
    head = f"📅 <b>Daily US news</b> · {today.isoformat()}"
    if not todays:
        return head + "\n\nNo red-folder USD events today. Calm session expected."
    return head + "\n\n" + "\n".join(_fmt(e) for e in todays)


def weekly(data=None):
    data = data or events.fetch()
    allred = _red_usd(data)
    head = "🗓️ <b>Weekly US news digest</b> (red-folder USD)"
    if not allred:
        return head + "\n\nNo high-impact USD events this week."
    return head + "\n\n" + "\n".join(_fmt(e) for e in allred)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--weekly", action="store_true", help="force the weekly digest too")
    args = ap.parse_args()
    load_dotenv()
    data = events.fetch()
    send_telegram(daily(data))
    # Monday (weekday()==0) or forced -> also send the week ahead
    if args.weekly or datetime.date.today().weekday() == 0:
        send_telegram(weekly(data))
    print("news digest sent")


if __name__ == "__main__":
    main()
