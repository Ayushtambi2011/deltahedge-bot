# 07 — External Data Inputs (events, greeks, liquidation)

Three inputs were requested. They are NOT equal in value or reliability. Ranked:

## 1. Greeks (best — use it) · `bot/greeks.py`
Uses the REAL per-strike delta/gamma/theta/vega already in Delta's ticker response to compute
NET position greeks and gate every trade:
- **net delta ≈ 0** — enforces directional neutrality (rejects non-neutral condors).
- **net theta > 0** — confirms you're paid to wait (a credit trade with negative theta is broken).
- **net vega < 0, bounded** — you're short vol; cap the size.
- **net gamma < 0, bounded** — the near-expiry danger; watch it.
Defensible because it uses data you already pull and enforces the hedge itself. No extra cost.

## 2. Event filter (good — use it, filtered) · `bot/events.py`
Free ForexFactory feed (`ff_calendar_thisweek.json`). Filtered to **crypto-relevant high-impact
USD events only** (CPI, FOMC, NFP, ISM, PPI, Unemployment, Avg Hourly Earnings, PCE, Fed speak).
- `is_blackout()` → HOLD new entries in the print window (default −60/+30 min).
- `event_within(8h)` → elevated expected vol → flag regime, advise wider wings.
Why filtered: blanket-blocking every High print would skip most days over European PMIs that
don't move BTC. This week's live movers: ISM (Aug 3), NFP + Unemployment + AHE (Aug 7).

## 3. Liquidation clusters (weakest — HYPOTHESIS only) · `bot/liquidation.py`
**Coinglass's heatmap is a PAID Pro feature.** The public API returns `"API key missing"` and
the on-screen heatmap is an unscrapable canvas. So this input is only available if you:
- buy a Coinglass key (`COINGLASS_API_KEY` in `.env`), OR
- hand-enter levels into `data/liquidation_levels.csv` (price,intensity).
The idea — price gravitates toward big liquidation clusters, so don't place a short strike on
one — is plausible but **unproven**. It's wired as a strike-nudge you must VALIDATE against your
paper log before trusting. Do not treat it as signal yet.

## The overfitting warning (read this)
You added three input layers before a single validated paper trade exists. More inputs is not
more edge — each adds a degree of freedom to fit noise and fool yourself (overfitting +
confirmation bias). Discipline:
- Turn on greeks gates + event filter now (cheap, defensible, low degrees of freedom).
- Keep liquidation-nudging OFF or clearly tagged in the log until data shows it helps.
- After 1–2 months, use the learning loop (docs/05) to test whether each input actually
  improved after-tax expectancy. Keep what pays; delete what doesn't.

## How they plug in (`bot/run_desk.py`)
Entry flow now: event blackout? → HOLD. Else build condor from real premiums → optional
liquidation strike-nudge → greeks neutrality/theta gate → signal shows net greeks + event flag
+ any nudges → log as paper trade. Nothing executed.
