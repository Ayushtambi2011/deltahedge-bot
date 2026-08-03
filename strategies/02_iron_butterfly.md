# Iron Butterfly (high-conviction sideways)

## Structure (net credit)
- Sell 1 ATM Call
- Sell 1 ATM Put
- Buy 1 OTM Call (upper wing / hedge)
- Buy 1 OTM Put (lower wing / hedge)

Short strikes both at-the-money → collects more credit than a condor, but the profit zone
is narrower.

## Payoff
- **Max profit** = net credit, if price expires exactly at the ATM strike (rare).
- **Max loss** = (wing width − net credit) × lot, past a wing.
- Narrower breakevens than a condor.

## When to use
- Only on days you strongly expect price to pin near current level (dead-quiet, low realized vol,
  no events). Lower hit rate than a condor, higher payoff when right.

## Parameters
- Wing width (max loss vs. credit).
- Entry/exit timing.
- Profit-take earlier than a condor (the peak is a knife-edge; don't be greedy).

## Risk notes
- Any real move hurts fast because you're short ATM (max gamma/theta).
- Higher variance than the condor. Not a "safe minimum profit" default.

## Fit
Secondary to the condor. Use sparingly, only on strongest quiet-day conviction.
