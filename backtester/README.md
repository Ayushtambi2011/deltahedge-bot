# Backtester

## Run
```bash
cd backtester
python3 engine.py --symbol BTC --strategy iron_condor
python3 engine.py --symbol BTC --strategy regime_switch
python3 review.py results/BTC_iron_condor.csv
```

## Files
- `config.py` — capital, fees, **TAX_MODE switch**, strategy params. Edit this first.
- `bsm.py` — Black-Scholes pricer/greeks (synthesizes option prices).
- `data.py` — synthetic GBM series + `load_csv()` for real data + realized-vol.
- `strategies.py` — iron condor, iron butterfly, long strangle builders.
- `engine.py` — simulates entry→expiry, applies fees + tax, writes `results/`.
- `review.py` — re-scores a results file under NONE/FNO/VDA tax to show tax impact.

## Read the output correctly
1. **Synthetic data only proves the plumbing works.** GBM has no real vol clustering,
   no fat tails, no IV skew. Do NOT conclude a strategy has edge from synthetic runs.
2. **The dollar magnitudes are unscaled** (1 notional unit, no position sizing to $1000).
   They show the *shape* — condor = many small wins, rare large losses — not your real PnL.
3. **The lesson that IS real:** switch `TAX_MODE` between `FNO` and `VDA` and watch the
   after-tax number. Under `VDA`, tax is charged on **gross winning trades even when the
   book loses overall** — that's the trap in `docs/01_TAX.md`, reproduced in code.

## To get real conclusions
1. Put real BTC/ETH daily closes in `../data/btc.csv` as `date,close`.
2. Better: replace the BSM synthesizer with **real historical option-chain prices** (entry
   premiums + settlement). Synthetic pricing understates skew and slippage.
3. Run walk-forward, out-of-sample. See `docs/05_LEARNING_LOOP.md`.
4. Only if after-fees AND after-(correct)-tax expectancy is positive over a long sample
   should you paper-trade. Otherwise stop.
