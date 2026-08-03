# Calendar Spread (long vol, cheap — not purely daily)

## Structure (net debit)
- Sell 1 near-expiry option (the daily) at a strike
- Buy 1 later-expiry option (weekly) at the **same strike**

Usually done at-the-money. The short daily decays faster than the long weekly → you profit
from that decay differential while staying long vega.

## Payoff
- **Max loss** ≈ net debit paid (defined, if managed).
- Profits if price stays near the strike **and/or** implied vol rises before the near leg expires.
- Not a pure daily-expiry trade — the long leg is a later expiry. Include it because it's the
  cleanest way to be *long volatility at low cost* without the strangle's theta bleed.

## When to use
- You expect quiet now but a vol pickup soon, or you want cheap long-vega exposure with a
  defined cost.

## Parameters
- Strike (ATM most common).
- Expiry gap (daily vs. next weekly).
- Roll/exit rule when the near leg expires.

## Risk notes
- A sharp *immediate* move away from the strike hurts (both legs move, but the structure's
  edge is near the strike).
- Two different expiries = more complex to manage and to model in backtest.

## Fit
Niche. Use when you want long-vol without paying full strangle theta. Lower priority than
#1–#4 for a first build; include once the core condor/strangle switch is proven.
