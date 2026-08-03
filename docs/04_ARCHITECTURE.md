# 04 — System Architecture (reviewed, sized to $1,000)

Supersedes the first draft. Incorporates the review of your proposed design.
Capital assumption: **$1,000 (~₹85k).** At this size, key constraint: **one position at
a time** (BTC or ETH, whichever scores higher — not both), margin ≤ ~30% of account.

## What "24x7" really means
An always-on **VPS you control** (~₹300–500/mo). Not a laptop, not a free tier (they sleep
and miss trades). I do not place orders; the bot only alerts you.

## The AI layer — decided: OFFLINE rule-tuner only
The "AI Decision Layer" from the draft is **removed from the live path.** Reason: an LLM/model
in the live decision is non-deterministic, unbacktestable, and slow — the worst place for a
black box is between market data and your money on daily expiries.

Instead, AI runs **nightly, offline**, on your trade log: it scores strategies/thresholds by
after-tax expectancy and *proposes* parameter edits. You approve → the change is versioned.
Live decisions stay 100% deterministic and backtestable.

## Reviewed flow
```
Delta API (read-only)
      │
      ▼
Market Collector          entry scan 1–2×/day at fixed times;
      │                   5-min scan ONLY while a position is open
      ▼
State Store   <-- logs daily IV so you can BUILD IV Rank yourself (Delta won't give it)
      │
      ▼
Deterministic Rules + Scoring     (all thresholds come FROM the backtest, not a blog)
      ├── IV / IV-Rank check
      ├── regime read (quiet/volatile) — UNPROVEN until backtested
      ├── strike select (16Δ / 5Δ)
      ▼
Risk & Margin Filter      max loss ≤ per-trade cap; margin ≤ 30%; one position at a time
      ▼
Event & Liquidity Filter  skip FOMC/CPI/crypto events, wide spreads, thin premium  <-- highest ROI
      ▼
Signal   (shows BACKTESTED EV after fees+tax, NOT just POP)
      ▼
Telegram → you place the order manually
      ▼
Trade Logger → Nightly Learning Loop → proposes threshold edits → you approve
```

## Component verdicts (from the review)
- **Market Scanner:** keep, but split cadence — entry 1–2×/day, 5-min only for open positions.
- **Strategy Selector:** keep structure, delete the words "no guesswork." Thresholds are
  hypotheses until backtested.
- **Strike Selector (16Δ/5Δ):** keep as-is. Clean and deterministic.
- **Position Sizing:** size to MARGIN UTILIZATION (≤30%), not just max loss. One position at a time.
- **Adjustment / Rolling:** DEFER. Backtest "roll vs. take the stop" first — rolling a loser
  often turns defined risk into bigger risk (sunk-cost in trade form). Default = clean stop.
- **Event/Liquidity filters:** keep — best feature. Add crypto-native events + spread/premium gates.
- **Learning loop:** keep, offline only, informs never trades.
- **IV Rank:** you must LOG IV daily to compute it. It won't arrive ready-made.

## Fix the alert (the POP trap)
The draft alert leads with "Probability of Profit 72%." POP is NOT edge — a high win rate with
a 3:1 loss:gain is roughly break-even. Using the draft's own numbers ($27 credit, $82 max loss,
72% POP): EV = 0.72×27 − 0.28×82 = **−$3.52 before fees.** Every alert must show **backtested
expectancy after fees + tax** next to POP. If that's negative, don't send the signal.

## Sizing for $1,000 (₹85k)
- Per-trade realized-loss stop: ~$25–35 (2.5–3.5%).
- Daily stop: ~$50 (5%) → halts after ~2 bad trades.
- Weekly stop: ~$150 (15%).
- Margin per position: ≤ ~$300 (30%).
- Positions at once: **1** (BTC or ETH by score). Both = over-leverage at this size.

## Still upstream of everything: the tax gate
None of this matters if VDA/no-set-off applies (`docs/01_TAX.md`). Get the CA answer first.
