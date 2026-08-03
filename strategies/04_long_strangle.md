# Long Strangle (the volatile-day bet — opposite of the condor)

## Structure (net debit)
- Buy 1 OTM Call
- Buy 1 OTM Put

Same daily expiry. Defined risk = the premium paid (you can only lose what you put in).

## Payoff
- **Max loss** = total premium paid (if price expires between the strikes → both expire worthless).
- **Profit** = unbounded-ish on a big move either direction, minus premium.
- Two breakevens far from spot.

## When to use
- **Only** when your regime signal says *volatile* (expected big move, event, IV cheap vs.
  realized). On daily expiry, theta decay is brutal — a quiet day melts this fast.

## Parameters
- Strike distance (closer = pricier, lower breakeven; farther = cheaper, needs bigger move).
- Entry timing (buy before the expected catalyst, not after).
- Hard time-stop: if the move hasn't come by a set time, cut it — don't donate to theta.

## Risk notes
- This is the **inverse** of the condor. Running both simultaneously cancels and doubles fees.
- Most days are not big-move days; expect a low hit rate with occasional large wins. Sizing
  discipline matters — max loss still ≤ per-trade cap.

## Fit
The other half of the regime switch. Its entire value depends on the regime signal being
better than a coin flip. If the signal is noise, this strategy just bleeds premium.
