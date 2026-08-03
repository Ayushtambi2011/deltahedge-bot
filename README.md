# Delta Exchange India — Hedged Daily-Expiry Options System

A research-first project for BTC/ETH daily-expiry options on Delta Exchange India, ~$1000 capital.

## Read this first
Before you deploy anything, read `docs/00_REALITY_CHECK.md`. It explains why the
"always-win hedge" you asked for does not exist, and why **the India tax treatment
may make this whole strategy negative-EV**. That doc could end the project — which is
exactly why it comes first.

## Build order (do NOT skip ahead)
1. **Get a CA's written answer on tax** (VDA 30% no-set-off vs. F&O business income). See `docs/01_TAX.md`.
2. **Backtest** — prove any edge survives fees + tax. See `backtester/`.
3. **Paper-trade** — the Telegram bot sends signals you place manually. See `bot/`.
4. **Live, tiny, manual** — only after 1–3 pass. Not automated at first.

## Folder map
```
docs/         Reality check, tax, fees, risk, architecture, learning loop
strategies/   One spec per strategy (payoff, when to use, risk, fit)
backtester/   Backtesting engine (BSM + REAL-chain loader) + results/
bot/          The desk: Delta client, chain recorder, signal + paper tracker, monitors
web/          dashboard.html — polished paper-trading dashboard
data/         chains/ snapshots, paper_trades.csv, performance.json (dashboard feed)
```

## The desk (24x7 paper trading)
- `bot/run_desk.py --mode entry`  → pull live chain, signal + log paper trades, refresh dashboard feed.
- `bot/run_desk.py --mode monitor` → check open positions, send IV/delta adjustment alerts.
- `bot/record_chain.py` → snapshot the real chain daily (builds your backtest dataset forward).
- `web/dashboard.html` → open in a browser (serve the folder) to see per-strategy paper P&L,
  IV monitor, equity curve, and recent signals. Shows which strategy actually works.
- After 1–2 months of logged paper trades, review per-strategy stats and keep/kill/tune.

### Quickstart
```bash
cd bot && pip install -r requirements.txt
cp .env.example .env            # add Telegram + read-only Delta keys
python3 delta_client.py         # smoke-test live chain
python3 run_desk.py --mode entry
# then serve the dashboard:
cd .. && python3 -m http.server 8080   # open http://localhost:8080/web/dashboard.html
```
Everything is PAPER: signals are logged and sent to Telegram, never executed.

## Honest scope
- I do **not** place live orders. The bot only sends you alerts.
- "24x7" means code on a small VPS you control (~₹300–500/mo). A free tier sleeps and misses trades.
- Nothing here is financial advice. Verify every number yourself.

Generated 2026-08-03.
