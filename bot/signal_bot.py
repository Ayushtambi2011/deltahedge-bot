"""Paper-trading signal bot — SENDS ALERTS ONLY. It NEVER places orders.

Flow (see docs/04_ARCHITECTURE.md):
  1. Read BTC/ETH spot + IV proxy from Delta (read-only).
  2. Read regime (quiet/volatile) -> pick strategy.
  3. Build the structure, compute strikes / suggested limit prices / size / stop.
  4. Send you a Telegram message telling you exactly what to place, and when.
  5. Log the signal to ../data/signals.csv.
YOU place the order manually in your Delta account. That is intentional.

Run once:      python3 signal_bot.py
Schedule it:   cron at your chosen pre-open time (see bot/README.md).
"""
import os
import csv
import sys
import datetime
import requests

# make backtester strategy + pricing logic importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backtester"))
import bsm  # noqa: E402

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
DAY = 1.0 / 365
RISK_FREE = 0.06

def env(k, default=None):
    return os.environ.get(k, default)

def load_dotenv():
    path = os.path.join(os.path.dirname(__file__), ".env")
    if os.path.exists(path):
        for line in open(path):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())

import re as _re


def _strip_html(t):
    return _re.sub(r"<[^>]+>", "", t)


def send_telegram(text):
    token = env("TELEGRAM_BOT_TOKEN"); chat = env("TELEGRAM_CHAT_ID")
    if env("DRY_RUN", "true").lower() == "true" or not token or not chat:
        print("[DRY_RUN] would send:\n" + text)
        return
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    # Telegram hard-caps at 4096 chars — split. Then verify delivery; fall back to plain text.
    chunks = [text[i:i + 3800] for i in range(0, len(text), 3800)] or [text]
    for chunk in chunks:
        try:
            r = requests.post(url, json={"chat_id": chat, "text": chunk, "parse_mode": "HTML"},
                              timeout=15)
            if r.status_code != 200:
                # HTML parse failure (stray <,>,&) or similar — resend as plain text
                r2 = requests.post(url, json={"chat_id": chat, "text": _strip_html(chunk)}, timeout=15)
                if r2.status_code != 200:
                    print(f"telegram send failed: {r.status_code} {r.text[:200]}")
                else:
                    print("telegram: sent as plain text (HTML rejected)")
        except Exception as e:
            print("telegram send error:", e)

def regime(realized_vol, iv):
    """Trivial placeholder — REPLACE with a backtested signal (docs/05_LEARNING_LOOP.md)."""
    if realized_vol is None:
        return "quiet"
    return "volatile" if realized_vol > 0.70 else "quiet"

def build_signal(symbol, spot, iv):
    reg = regime(iv, iv)
    legs = []
    if reg == "quiet":
        strat = "iron_condor"
        sc = bsm.strike_for_delta(spot, DAY, RISK_FREE, iv, 0.16, "call")
        sp = bsm.strike_for_delta(spot, DAY, RISK_FREE, iv, 0.16, "put")
        w = round(spot * 0.02)
        legs = [
            ("SELL", "CALL", sc), ("BUY", "CALL", sc + w),
            ("SELL", "PUT", sp),  ("BUY", "PUT", sp - w),
        ]
    else:
        strat = "long_strangle"
        sc = bsm.strike_for_delta(spot, DAY, RISK_FREE, iv, 0.25, "call")
        sp = bsm.strike_for_delta(spot, DAY, RISK_FREE, iv, 0.25, "put")
        legs = [("BUY", "CALL", sc), ("BUY", "PUT", sp)]
    # suggested limit price per leg (mid from BSM; use limit orders, not market)
    priced = []
    for side, kind, strike in legs:
        px = bsm.price(spot, strike, DAY, RISK_FREE, iv, kind.lower())
        priced.append((side, kind, strike, round(px, 2)))
    return strat, reg, priced

def format_msg(symbol, spot, iv, strat, reg, priced):
    now = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    lines = [f"<b>{symbol} daily-expiry signal</b>  ({now})",
             f"regime: <b>{reg}</b>  |  strategy: <b>{strat}</b>",
             f"spot: {spot}  |  IV proxy: {round(iv,2)}", "",
             "Place these as LIMIT orders (verify chain, don't chase):"]
    for side, kind, strike, px in priced:
        lines.append(f"  {side} {kind} {strike}  ~ {px}")
    lines += ["",
              "Size: 1 lot / smallest — max loss must be <= per-trade cap ($40).",
              "Set your stop/exit per docs/03_RISK_MANAGEMENT.md BEFORE entering.",
              "",
              "⚠️ SIGNAL ONLY. This bot did NOT place any order. You place it."]
    return "\n".join(lines)

def log_signal(symbol, spot, iv, strat, reg, priced):
    os.makedirs(DATA_DIR, exist_ok=True)
    path = os.path.join(DATA_DIR, "signals.csv")
    new = not os.path.exists(path)
    with open(path, "a", newline="") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["ts", "symbol", "regime", "strategy", "spot", "iv", "legs"])
        w.writerow([datetime.datetime.utcnow().isoformat(), symbol, reg, strat, spot,
                    round(iv, 3), ";".join(f"{s} {k} {st}@{p}" for s, k, st, p in priced)])

def main():
    load_dotenv()
    symbols = env("SYMBOLS", "BTC,ETH").split(",")
    # NOTE: live spot/IV pull is in delta_client.py; kept decoupled so this runs offline.
    try:
        from delta_client import DeltaReadClient
        client = DeltaReadClient()
    except Exception:
        client = None
    for symbol in [s.strip() for s in symbols]:
        spot = None
        if client:
            try:
                spot = client.spot_price(symbol)
            except Exception as e:
                print(f"spot fetch failed for {symbol}: {e}")
        if not spot:
            spot = 60000.0 if symbol == "BTC" else 3000.0  # offline placeholder
            print(f"[offline] using placeholder spot for {symbol}: {spot}")
        iv = 0.60  # TODO: pull real IV from the chain; placeholder for now
        strat, reg, priced = build_signal(symbol, spot, iv)
        msg = format_msg(symbol, spot, iv, strat, reg, priced)
        send_telegram(msg)
        log_signal(symbol, spot, iv, strat, reg, priced)

if __name__ == "__main__":
    main()
