# 05 — Learning Loop (keep improving from wins AND failures)

The point: every trade — win or loss — becomes data that tunes future decisions. No magic
AI that "learns to beat the market." A disciplined feedback loop that (a) tracks which
strategy works in which regime and (b) stops doing what loses.

## What gets logged per trade (`data/trades.csv`)
`date, symbol, strategy, regime_signal, strikes, entry_prices, size, credit_debit,
max_loss, fees_est, exit_reason, pnl_gross, pnl_after_fees, tax_est, realized_vol,
notes`

## Nightly review (automated, `backtester/review.py`)
1. Compute per-strategy stats: win rate, avg win, avg loss, expectancy **after fees + tax**,
   max drawdown, profit factor.
2. Break stats down **by regime** (was the day actually quiet or violent vs. what the
   signal predicted?). This is how you learn if your regime read is any good.
3. Flag strategies with negative after-tax expectancy over a rolling window → **auto-disable**.
4. Append a dated summary to `data/journal.md`.

## The regime signal (where edge lives or dies)
Start simple and honest:
- Inputs: recent realized volatility, current IV vs. realized (IV rank), overnight
  gap size, day-of-week, funding, big scheduled events.
- Output: `quiet` / `volatile` / `no-trade`.
- **Backtest the signal's hit rate BEFORE trusting it.** If it can't beat a coin flip at
  predicting next-day regime, your condor/strangle switch is noise and you should just run
  one defined-risk structure and accept its base rate.

## Guardrails against fooling yourself
- **Walk-forward only.** Never tune on the same data you evaluate on.
- **Out-of-sample test** before any parameter change goes live.
- **Track the counterfactual:** log what the *other* strategy would have done, so you learn
  regime accuracy, not just realized PnL.
- **Confirmation bias check:** the review script reports losers as loudly as winners.

## Cadence
- Nightly: auto-review + journal entry.
- Weekly: you read `data/journal.md`, decide keep/kill/tune.
- Monthly: re-run full backtest with the newest data; compare live vs. backtest expectancy.
  Large divergence = live edge is decaying or slippage is worse than modeled.
