# Backtest Results — Real BTC Path (first run)

Run date: 2026-08-03. Data: real BTC daily closes, 2026-03-01 → 2026-08-01 (128 daily
expiries), from CryptoDataDownload/Binance. Fees: Delta EXACT (0.010% notional, 3.5%
premium cap, 18% GST, no fee on OTM-expiry). Premiums: **modeled** via Black-Scholes with
IV = trailing realized vol. Per 1 contract (BTC contract = 0.001 BTC).

## Headline
| Strategy | Trades | Win% | Avg win | Avg loss | Profit factor | After-fees PnL | After-tax (FNO) |
|----------|-------:|-----:|--------:|---------:|--------------:|---------------:|----------------:|
| Iron Condor | 128 | 73.4% | $0.20 | −$0.60 | **0.92** | −$1.58 | −$1.58 |
| Long Strangle | 128 | 29.7% | $0.94 | −$0.41 | **0.97** | −$1.06 | −$1.06 |

Profit factor < 1.0 = losing. **Both strategies lost money after fees on this path.**

## Tax check (condor), same trades under each model
| Tax mode | Tax paid | After-tax PnL |
|----------|---------:|--------------:|
| NONE | $0.00 | −$1.57 |
| FNO (net, loss offset) | $0.00 | −$1.57 |
| VDA (30% gross winners) | $5.61 | **−$7.18** |

The VDA column is the trap made concrete: a **losing** book still pays $5.61 tax because
it's charged on gross winners with no loss relief. FNO correctly charges $0 on a net loss.
This is why the tax classification matters (docs/01_TAX.md).

## What this does and does NOT prove
**Proves:** the pipeline runs on real data; the exact Delta fee model is wired; the condor's
shape is real (73% win rate, small wins, bigger losses — high POP, negative expectancy);
and the VDA-vs-FNO tax gap is real.

**Does NOT prove there's no edge**, for three concrete reasons:
1. **Modeled premiums set IV = realized vol.** Real option sellers earn a *variance risk
   premium* (IV typically > RV). Removing it makes this run **pessimistic for the condor** —
   the single biggest reason a real condor might be profitable is excluded here.
2. **Data gaps.** The provider file skips some days; one gap (2026-06-01 → 06-08) is a ~12%
   move treated as one expiry, which blows through condor wings — an artifact, not a real
   daily result. It drags the condor down.
3. **One asset, one regime, 128 days, unoptimized params** (16Δ shorts, 2% wings). Not a
   sample you can conclude from.

## Verdict
On arbitrage-free modeled premiums, both strategies sit slightly negative after fees —
exactly what theory predicts. **Whether a real edge exists depends entirely on real option-
chain IV (the variance risk premium) and on parameter tuning.** Next step is real premium/IV
data, not more synthetic modeling.

## To advance
- Get real historical option-chain data (entry premiums + settlement) — paid providers:
  Amberdata, Laevitas, Tardis/Deribit. This replaces the BSM synthesizer.
- Add ETH via the same pipeline (`data/eth.csv`).
- Log live IV daily to build IV Rank, then re-test condor filtered to high-IV-rank days only
  (where the variance risk premium is largest).
