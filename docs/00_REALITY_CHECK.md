# 00 — Reality Check (read before anything else)

## 1. The "always-win hedge" does not exist
You asked for a position that is *totally hedged and safe* and *profits whether the
market stays sideways OR makes a big move either direction*, for minimum guaranteed profit.

That describes a position with a **positive payoff in every possible outcome at low or
zero cost** — the textbook definition of an **arbitrage**. Liquid options markets are
priced precisely to remove it. The premium you collect for the sideways case is, on
average, exactly what you lose in the big-move case, minus the market maker's edge and
your fees.

- An **iron condor** wins if price stays in a range, loses on a big move.
- A **straddle/strangle** wins on a big move, bleeds to death if it's quiet.
- Run both at once and they cancel — you just pay four sets of fees.

**There is no single daily-expiry structure that collects on both regimes.** What you
actually want is a *regime predictor*: "will tomorrow be quiet or violent?" That is the
real, hard, unsolved problem. Automation does not give it to you for free. Any edge this
system ever has will come from the regime signal — and that is also where it will fail.

## 2. Realistic expectation
A well-run hedged daily-expiry book aims for **small, positive expectancy with capped
drawdowns** — *not* guaranteed daily profit. Expect losing days and losing weeks. The
goal is that wins > losses > fees > taxes **over many trades**. If that inequality does
not hold in backtest, do not go live.

## 3. The three things that decide if this is viable
1. **Tax** (`01_TAX.md`) — likely the biggest risk. If VDA 30%/no-set-off applies, the
   strategy is probably negative-EV. Resolve first.
2. **Fees** (`02_FEES.md`) — ~0.03%/side capped at 3.5% of premium + 18% GST, on ~8
   fills/day. Real drag on a $1000 book.
3. **Edge** (`backtester/`) — does any strategy beat fees+tax on history? Prove it.

## 4. Cognitive traps to name out loud
- **Overconfidence:** "fully automatic 24x7" feels like control. It is not edge.
- **Sunk-cost in advance:** building the live bot before backtesting is committing before
  you have evidence. Don't.
- **Survivorship bias:** the YouTube/Telegram "Delta options bot" wins you see are the
  survivors. The blown accounts don't post.
- **Availability bias:** a few big-move days you remember don't tell you the *base rate*
  of quiet vs. violent days. The backtest does.

Nothing here is financial or tax advice. Verify everything.
