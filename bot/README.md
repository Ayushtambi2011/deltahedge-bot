# Paper-Trading Signal Bot (alerts only, never trades)

## What it does
Reads BTC/ETH spot + IV (read-only), picks a strategy by regime, computes strikes /
suggested limit prices / size / stop, and **sends you a Telegram message**. It logs each
signal to `../data/signals.csv`. **It does not and cannot place orders.** You place them.

## Setup
```bash
cd bot
pip install -r requirements.txt
cp .env.example .env      # then edit .env
python3 delta_client.py   # smoke-test market-data connectivity
python3 signal_bot.py     # DRY_RUN=true prints to console instead of Telegram
```

### Telegram bot token
1. In Telegram, message **@BotFather** → `/newbot` → get the token.
2. Message your new bot once, then get your chat id (e.g. via @userinfobot).
3. Put both in `.env`. Set `DRY_RUN=false` when ready to receive real alerts.

### Delta API keys
Generate **read-only** keys in your Delta India account (Settings → API Keys). Read-only is
all this bot needs — it never trades. Keep keys in `.env`, never in git.

## Verify before trusting
- Confirm endpoint paths + symbol formats against https://docs.delta.exchange. The client
  has TODOs where the venue's exact field names must be checked.
- The IV is a placeholder (0.60). Wire real IV from the option chain before going live.
- The regime function is a trivial placeholder — replace with a **backtested** signal
  (see ../docs/05_LEARNING_LOOP.md). Until then, it's just running the condor.

## Schedule it (24x7 on a VPS)
On your always-on VPS, cron at your chosen pre-open time (example: 09:00 IST = 03:30 UTC):
```
30 3 * * * cd /path/to/OPTIONS\ STRATEGIES/bot && /usr/bin/python3 signal_bot.py >> ../data/bot.log 2>&1
```
Add a second cron for a heartbeat/health alert so you know if the VPS dies (a silent bot is
worse than no bot). See ../docs/06_SETUP.md.
