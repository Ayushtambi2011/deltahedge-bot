# 02 — Fees & Cost Drag (EXACT, from Delta fee page, fetched 2026-08-03)

## Options fees on Delta Exchange India
- **Maker AND taker = 0.010% of Notional.** Notional = Spot × contract size × contracts.
  (BTC contract = 0.001 BTC; ETH contract = 0.01 ETH — verify ETH on the venue.)
- **Fee capped at 3.5% of premium.** The cap applies only when the notional-based fee
  exceeds the premium-based fee (i.e. it protects you on low-premium / deep-OTM options).
- **A SHORT option that expires OTM (worthless) pays NO trading fee at expiry** — no premium
  realized, no fee. This directly helps iron condors on winning days.
- **+18% GST** on the calculated fee.

## Worked example (Delta's own)
Buy 300 BTC option contracts, strike $90,000, premium $150, BTC at $90,000:
- Notional = 90,000 × (300 × 0.001) = $27,000
- Premium paid = 0.3 BTC × $150 = $45
- Notional fee = 0.010% × $27,000 = $2.70
- Premium-cap fee = 3.5% × $45 = $1.575  → **cap wins, you pay $1.575** (+18% GST).

## Correction vs first draft
Earlier this doc assumed 0.03% per side. **The real options rate is 0.010%** — meaningfully
lower. Combined with "no fee on OTM expiry," the drag on a condor is smaller than first
modeled. The backtester (`config.py`) now uses the exact numbers.

## Why it still matters on $1,000
Even at 0.010% + cap, a 4-leg condor is up to 8 fills. The backtest shows the strategy
hovering near breakeven on modeled premiums, so fees are still the difference between a
marginal win and a loss. Prefer maker (limit) fills; the OTM-expiry waiver rewards letting
winning shorts expire rather than buying them back.

## Futures (for reference)
- Taker 0.05%, Maker 0.02% of notional, +18% GST.

## Sources
- [Delta Exchange — Fees on Options and Futures Trading](https://www.delta.exchange/support/solutions/articles/80001177864-fees-on-options-and-futures-trading)
