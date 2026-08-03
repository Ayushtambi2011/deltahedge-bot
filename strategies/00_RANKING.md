# Strategy Ranking — Daily Expiry, $1000, Defined Risk

Ranked for your stated priority: **capital safety first, small profit second.**
All are defined-risk. None wins in both regimes — that's the point of `docs/00_REALITY_CHECK.md`.

| # | Strategy | Wins when | Loses when | Legs | Best use |
|---|----------|-----------|------------|------|----------|
| 1 | Iron Condor | Sideways / quiet | Big move either side | 4 | Default on low-vol days |
| 2 | Iron Butterfly | Very sideways (pins near ATM) | Any real move | 4 | Highest-conviction quiet day |
| 3 | Broken-Wing Butterfly | Sideways with a directional lean | Move against the lean | 3–4 | Quiet + mild bias, cheap |
| 4 | Long Strangle | Big move either side | Quiet / theta decay | 2 | Only when signal says volatile |
| 5 | Calendar Spread | Quiet now, vol later | Sharp immediate move | 2 | Long-vol at low cost |

## Why #1 beats #2 and #3 as the *default*
- **#1 Iron Condor** has the widest profit zone of the credit structures → highest base-rate
  win probability, which matches "safe with minimum profit." You give up peak profit for a
  bigger margin of error. Best risk-adjusted default.
- **#2 Iron Butterfly** collects more credit but needs price to pin near one strike — narrow
  win zone, lower hit rate. Only when you're unusually confident it's a dead-quiet day.
- **#3 Broken-Wing Butterfly** is the value pick when you have a *mild* directional lean: it
  can be structured for near-zero cost on one wing (lower fee drag), but you're now taking a
  small directional bet.

## The real system
Don't run all five daily. Run the **regime switch**: quiet-signal → #1 (or #2/#3), volatile-
signal → #4 (or #5). #4 and #1 are opposite bets — running both together just pays double
fees and cancels out. The edge is entirely in the regime call (`docs/05_LEARNING_LOOP.md`).

## Recommendation
Start by backtesting **#1 Iron Condor alone** as the baseline. If it can't clear fees+tax on
history, no switch strategy will save it. Add #4 only after the regime signal proves it beats
a coin flip.
