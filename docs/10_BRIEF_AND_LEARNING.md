# 10 — Daily Brief & Learning System

## Daily/Weekly Brief (`bot/daily_brief.py`) · 07:00 IST
One Telegram message each morning with:
- **US news** — red-folder USD events today (ForexFactory, free).
- **Market structure per asset** — from Delta's OWN option OI (free, real):
  - **Bias** (Neutral / Slightly Bearish / …) from PCR + max pain + IV skew.
  - **Resistance** = heaviest call-OI strikes (order blocks above).
  - **Support** = heaviest put-OI strikes (order blocks below).
  - **Max pain** = expiry price that hurts option buyers most (a magnet).
- **Liquidation zones** — only if you supply them (manual CSV or paid Coinglass key).
- **Mondays:** adds the weekly news + the learning-review summary.

### Why not the Coinglass heatmap image?
That heatmap is a **paid** Coinglass feature (the API returned 401/Upgrade). Rather than fake
it, the brief uses **Delta's own OI positioning** — the real order flow on the exchange you
trade. It answers the same question (where are the walls?) with free, first-party data.

## Learning System (`bot/learning_review.py`) · honest, evidence-based
Runs weekly on SETTLED paper trades and writes dated entries to `data/lessons.md`, plus a
Telegram summary. It reports:
- Per-strategy expectancy (win%, profit factor, net) → keep / tighten / retire.
- **Mistakes:** trades that blew through to ~max loss (wings too tight? entered too near an event?).
- **Timing:** which entry hours had the best win rate.

### What it is NOT
It does **not** promise a rising take-profit rate — anything that does is selling overfitting.
It surfaces evidence so YOU adjust the rules (thresholds in `strategy_selector.py`), then you
re-test. Improvement happens only if a real edge exists. Below **15 settled trades** it says
"collecting data" and draws no conclusions — that honesty is the point.

## The loop, end to end
Daily: brief (07:00 IST) → entry signals → monitor alerts → settle at expiry → log.
Weekly: learning review reads the log → lessons.md + Telegram → you tune → repeat.
Every claim is grounded in your own settled trades, not intuition.
