# 09 — Strategy Selector, News Digest & A/B

## The decision tree (`bot/strategy_selector.py`)
```
in event blackout window  -> NO new trade (hold)
major event within hours  -> Long Strangle      (buy vol BEFORE the print)
high IV (>= IV_HIGH)       -> Iron Condor         (sell rich premium)
trending (|move| >= TREND) -> Broken-Wing Butterfly (directional, defined risk)
low IV (<= IV_LOW), else   -> NO trade            (premium too thin)
neutral / mid IV           -> Iron Condor (default)
```
If TWO conditions fire (e.g. high IV AND trending, or event AND high IV) the selector
returns BOTH strategies and the desk fires + logs both as separate paper trades — your
A/B test (request #4). This only happens in paper; live on $1000 you run one at a time.

### Thresholds (TUNE — do not trust as-is)
`IV_HIGH=75, IV_LOW=45, TREND_PCT=0.04, TREND_WINDOW=5` in `strategy_selector.py`.
These are **placeholders**. Absolute IV stands in until ~30 days of recorded chains give a
real IV RANK; trend uses the % move across recent chain snapshots (needs a few days to warm
up — until then "trending" is off and you'll see condor/strangle only). After 1–2 months,
use the learning loop (docs/05) to set these from data, not intuition. More knobs = more ways
to overfit; change them deliberately.

## Event reconciliation
"Major event → Long Strangle" and the event *blackout* are NOT contradictory:
- **Before** the event (hours ahead): open a long strangle to catch the move.
- **During** the print window (−60/+30 min): no NEW entries — too chaotic.
The blackout wins inside its window; the strangle applies in the run-up.

## News digest (`bot/news_digest.py`)
- **Daily:** red-folder (High-impact) **USD** events happening today → Telegram.
- **Weekly:** every **Monday** it also sends the week's red USD events.
Times shown in IST. Scheduled at 07:00 UTC (12:30 IST) by default — change the cron to
`30 1 * * *` for 07:00 IST. Source: ForexFactory (free, no key).

## Broken-Wing Butterfly (`chain_loader.build_broken_wing_butterfly`)
Direction-aware, defined risk: sell 2 body + buy a wide wing (protection) + buy a narrow
"broken" wing. Put-side when trend ≥ 0, call-side when trend < 0. Built from real chain mids.

## What fires where
All of this runs inside `bot/run_desk.py --mode entry`: fetch chain → selector → (optional
liquidation nudge) → greeks gate → signal(s) → log paper trade(s). Nothing executed.
