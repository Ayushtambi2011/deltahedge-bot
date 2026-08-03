# Broken-Wing Butterfly (sideways with a lean, low cost)

## Structure (call-side example, can mirror on put side)
- Buy 1 ATM/near Call
- Sell 2 OTM Calls (the body)
- Buy 1 further OTM Call, but place the far wing **closer** than a symmetric fly ("broken wing")

The asymmetry can make the structure a **net credit or near-zero cost**, and removes risk on
one side entirely.

## Payoff
- Defined risk (one side has little or no loss; the other side's loss is capped by the wing).
- Best profit if price drifts toward the body strikes.
- You take a **mild directional bias** — this is not delta-neutral like a condor.

## When to use
- Quiet day *plus* a small directional lean you can justify. Lower fee drag when built for
  near-zero cost.

## Parameters
- Body strike distance from spot.
- Wing skew (how "broken" — controls whether it's a credit and where risk sits).
- Side (call-side for upward lean, put-side for downward).

## Risk notes
- You've traded delta-neutrality for cheaper entry. A move against the lean is the loss case.
- More moving parts than a condor; get the fills right or slippage eats the thin edge.

## Fit
The value/efficiency pick. Good when the condor's fees feel too heavy relative to its credit
and you have a defensible mild bias.
