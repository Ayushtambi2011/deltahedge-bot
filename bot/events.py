"""Economic-event filter using the ForexFactory weekly JSON feed (free, no key).
Feed: https://nfs.faireconomy.media/ff_calendar_thisweek.json
Fields: title, country, date (ISO, US-Eastern -04:00), impact, forecast, previous.

We only care about events that actually move CRYPTO (BTC/ETH vs USD). Blanket-blocking
every High-impact print would skip most days over European PMIs that don't move BTC.
"""
import datetime
import json
import os
import re
import requests

FEED = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
CACHE = os.path.join(os.path.dirname(__file__), "..", "data", "ff_calendar.json")

# USD prints (and Fed events) that reliably move crypto:
CRYPTO_MOVERS = re.compile(
    r"(CPI|FOMC|Federal Funds|Interest Rate|Non-?Farm|Unemployment Rate|"
    r"Average Hourly Earnings|ISM|PPI|Powell|Fed Chair|PCE)", re.I)


def _utc(ev):
    # date like "2026-08-03T10:00:00-04:00"
    try:
        return datetime.datetime.fromisoformat(ev["date"]).astimezone(datetime.timezone.utc)
    except Exception:
        return None


def fetch(use_cache_on_fail=True):
    try:
        r = requests.get(FEED, timeout=20)
        r.raise_for_status()
        data = r.json()
        os.makedirs(os.path.dirname(CACHE), exist_ok=True)
        with open(CACHE, "w") as f:
            json.dump(data, f)
        return data
    except Exception as e:
        if use_cache_on_fail and os.path.exists(CACHE):
            with open(CACHE) as f:
                return json.load(f)
        raise e


def crypto_events(data=None, min_impact=("High",)):
    """Return crypto-relevant events sorted by time (UTC)."""
    data = data or fetch()
    out = []
    for ev in data:
        country = (ev.get("country") or "").upper()
        title = ev.get("title") or ""
        impact = ev.get("impact") or ""
        named = bool(CRYPTO_MOVERS.search(title))
        # keep USD high-impact, OR any explicitly-named mover (CPI/FOMC/PPI even if Medium)
        keep = (country == "USD" and (impact in min_impact or named)) or (named and impact != "Low")
        if not keep:
            continue
        t = _utc(ev)
        if t:
            out.append({"title": title, "country": country, "impact": impact,
                        "time_utc": t, "forecast": ev.get("forecast"), "previous": ev.get("previous")})
    return sorted(out, key=lambda e: e["time_utc"])


def next_event(now=None, data=None):
    now = now or datetime.datetime.now(datetime.timezone.utc)
    fut = [e for e in crypto_events(data) if e["time_utc"] >= now]
    return fut[0] if fut else None


def is_blackout(now=None, pre_min=60, post_min=30, data=None):
    """True if we're within [pre_min before, post_min after] a crypto-mover event.
    Use to SKIP new entries or force a wider/strangle setup around the print."""
    now = now or datetime.datetime.now(datetime.timezone.utc)
    for e in crypto_events(data):
        start = e["time_utc"] - datetime.timedelta(minutes=pre_min)
        end = e["time_utc"] + datetime.timedelta(minutes=post_min)
        if start <= now <= end:
            return True, e
    return False, None


def event_within(hours=8, now=None, data=None):
    """Is there a crypto-mover in the next `hours`? -> elevated expected vol today."""
    now = now or datetime.datetime.now(datetime.timezone.utc)
    horizon = now + datetime.timedelta(hours=hours)
    hits = [e for e in crypto_events(data) if now <= e["time_utc"] <= horizon]
    return hits


if __name__ == "__main__":
    evs = crypto_events()
    print(f"Crypto-relevant events this week: {len(evs)}")
    for e in evs:
        print(f"  {e['time_utc'].isoformat()}  {e['country']} {e['impact']:6} {e['title']}")
    bl, e = is_blackout()
    print("\nBlackout now:", bl, (e['title'] if e else ""))
    soon = event_within(8)
    print(f"Movers in next 8h: {[e['title'] for e in soon]}")
