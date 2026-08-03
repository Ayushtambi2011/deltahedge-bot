# 03 — Risk Management ($1000 account)

## Non-negotiable rules
1. **Only defined-risk structures.** Every position must have a known, capped max loss
   *before* entry. No naked short options. Ever.
2. **Max risk per trade:** 3–5% of capital = **$30–50 max loss** per position on $1000.
3. **Daily stop:** if the day's realized loss hits **8–10% ($80–100)**, stop for the day.
4. **Weekly stop:** down **20% ($200)** in a week → halt, review the log, no new trades
   until you understand why.
5. **Position sizing:** size each structure so its max loss ≤ the per-trade cap. On daily
   options with $1000, that usually means **1 lot / smallest size**, sometimes sitting out.
6. **No revenge trading, no averaging into losers, no removing the hedge.** The hedge is
   the whole point.

## Daily-expiry specific dangers
- **Gamma risk near expiry:** losses accelerate fast as spot approaches your short strike
  on expiry day. Have exit rules by time-of-day, not just price.
- **Theta is a double edge:** it pays you in condors, it bleeds you in strangles. Know
  which side you're on before entry.
- **Liquidity/slippage:** far strikes on daily options can be thin. Use limit orders.
- **Assignment/settlement:** understand Delta's settlement mechanics for expiry day.

## Kill switches (build into the bot)
- Auto-halt signals if account equity < a floor you set.
- Auto-halt if realized loss today ≥ daily stop.
- Heartbeat alert if the bot/VPS goes down (so no trade runs blind).

Capital preservation beats a good entry. A month of small survivable losses is recoverable;
one blown account is not.
