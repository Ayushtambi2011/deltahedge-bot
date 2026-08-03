# 06 — Setup & Deploy (do these in order)

## Phase 0 — Decide if this is even viable (blocking)
- [ ] Read `docs/00_REALITY_CHECK.md`.
- [ ] Get a CA's written answer on tax (`docs/01_TAX.md`). If VDA/no-set-off applies to
      your account, seriously reconsider frequency or the whole approach.
- [ ] Confirm current fees on Delta's fee page (`docs/02_FEES.md`).

## Phase 1 — Backtest (prove edge before risking money)
- [ ] `cd backtester && python3 engine.py --symbol BTC --strategy iron_condor` (runs on synthetic).
- [ ] Get **real** BTC/ETH daily data (and ideally real option-chain history). Put in `data/`.
- [ ] Re-run with `--csv`. Check after-fees AND after-(correct-tax) expectancy over a long window.
- [ ] Walk-forward / out-of-sample. If not positive → stop here. That's a successful result:
      you avoided a losing live deployment.

## Phase 2 — Paper trade (signals only, place manually)
- [ ] `cd bot && cp .env.example .env`, fill Telegram + read-only Delta keys.
- [ ] Run `signal_bot.py` daily (cron). Place trades **manually** in your account.
- [ ] Log fills + outcomes. Compare live results vs. backtest for several weeks.
- [ ] If live expectancy holds after fees + tax → consider Phase 3. If not → stop or retune.

## Phase 3 — 24x7 (only after 1 & 2 pass)
### VPS
- Small always-on cloud instance (~₹300–500/mo). **Free tiers sleep — don't use them for this.**
- `git clone` your project (keep `.env` OUT of git), `pip install -r bot/requirements.txt`.

### Schedule (cron)
```
# pre-open signal (adjust to your time; example 03:30 UTC = 09:00 IST)
30 3 * * * cd ~/options/bot && /usr/bin/python3 signal_bot.py >> ../data/bot.log 2>&1
# nightly review + journal
0 20 * * * cd ~/options/backtester && /usr/bin/python3 review.py results/BTC_iron_condor.csv >> ../data/review.log 2>&1
```

### Reliability (non-negotiable for "no trades missed")
- [ ] **Heartbeat alert:** a cron that pings you daily "bot alive". Silence = investigate.
- [ ] **Error alerts:** wrap the bot so exceptions send a Telegram message, not just a log line.
- [ ] **Idempotency:** don't double-signal if cron double-fires.
- [ ] **Time sync + timezone:** confirm the VPS clock and your expiry/entry times align (IST vs UTC).

## Phase 3.5 — The desk + dashboard (24x7 paper, current build)
On your always-on VPS:
```bash
# cron
30 3  * * *  cd ~/options/bot && python3 run_desk.py --mode entry   >> ../data/desk.log 2>&1
*/10 * * * *  cd ~/options/bot && python3 run_desk.py --mode monitor >> ../data/mon.log 2>&1
0 20 * * *   cd ~/options/bot && python3 paper_tracker.py           >> ../data/perf.log 2>&1
```
Serve the dashboard (behind auth if exposed):
```bash
cd ~/options && python3 -m http.server 8080   # http://<vps>:8080/web/dashboard.html
```
- `run_desk.py --mode entry` records the chain, signals from real premiums, logs paper trades.
- `--mode monitor` sends IV/delta adjustment alerts on open positions.
- `paper_tracker.py` settles expired paper trades and rebuilds the dashboard feed.
- Add a heartbeat cron that Telegrams you daily so a dead VPS is obvious.
- **IV Rank:** the daily `record_chain` snapshots build the IV history needed for real IV-rank
  regime signals. Until ~20–30 days accumulate, regime is a placeholder (docs/05_LEARNING_LOOP.md).

## Phase 4 — Live auto-execution (much later, optional)
Only after months of profitable paper + manual trading. Requires trade-enabled API keys,
hard kill-switches, and full risk filters wired in. Not built here on purpose — automating
the click multiplies the cost of every bug by your whole account.

## What "no cost" can and can't be
- Free: Delta API, Telegram bot, Python, this code.
- Not free and worth paying for: a real VPS, real historical option data, a CA's tax opinion.
  Skimping on these is where small accounts quietly bleed out.
