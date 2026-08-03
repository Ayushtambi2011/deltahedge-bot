# Trading Journal

The learning loop appends dated entries here. Read it weekly; decide keep/kill/tune.

## Columns tracked in data/trades.csv
date, symbol, strategy, regime_signal, strikes, entry_prices, size, credit_debit,
max_loss, fees_est, exit_reason, pnl_gross, pnl_after_fees, tax_est, realized_vol, notes

## 2026-08-03 — project set up
- Docs, 5 strategy specs, backtester, and paper-signal bot created.
- Backtester runs on synthetic data (plumbing verified). Next: plug real BTC/ETH data.
- BLOCKING: CA tax opinion (VDA vs F&O). This decides viability. See docs/01_TAX.md.
- No live capital deployed. No orders placed.
