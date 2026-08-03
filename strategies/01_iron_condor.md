# Iron Condor (default, sideways)

## Structure (net credit)
- Sell 1 OTM Call (short call, nearer strike)
- Buy 1 further OTM Call (long call, the hedge/cap)
- Sell 1 OTM Put (short put, nearer strike)
- Buy 1 further OTM Put (long put, the hedge/cap)

All same daily expiry. The bought wings cap your loss → **defined risk**.

## Payoff
- **Max profit** = net credit received, if price expires between the two short strikes.
- **Max loss** = (wing width − net credit) × lot size, if price blows past a long strike.
- Breakevens = short call strike + credit, and short put strike − credit.

## When to use
- Low expected volatility (quiet-signal day), IV rank moderate-to-high (you're selling pricey premium).

## Parameters to tune (in backtest)
- Short strike delta (e.g. ~0.15–0.20 delta = ~80–85% OTM probability).
- Wing width (controls max loss vs. credit; wider = more credit, more risk).
- Entry time and exit time on expiry day.
- Profit-take (e.g. close at 50% of max credit) and stop (e.g. 1.5–2× credit loss).

## Risk notes
- Loses on a big move either direction — the price of its wide, high-probability profit zone.
- Gamma spikes near expiry; define a time-based exit, don't hold to the bell blindly.
- Keep max loss ≤ per-trade cap ($30–50). Size accordingly.

## Fit to your goal
Best match for "safe with minimum profit" on quiet days. Highest base-rate win probability
of the credit structures. This is the baseline everything else is measured against.
