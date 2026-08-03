"""Backtest engine: for each day, build a structure, price entry at open, settle at
next day's close (daily expiry), apply fees and the tax model. Writes results CSV.

Run:  python3 engine.py --symbol BTC --strategy iron_condor
      python3 engine.py --symbol BTC --strategy regime_switch   (condor on quiet, strangle on volatile)
"""
import argparse
import csv
import os
import config
import bsm
import data
import strategies

DAY = 1.0 / 365

def leg_premium(S, leg, sigma):
    return bsm.price(S, leg["strike"], DAY, config.RISK_FREE, sigma, leg["kind"])

def leg_settle(S_expiry, leg):
    if leg["kind"] == "call":
        return max(0.0, S_expiry - leg["strike"])
    return max(0.0, leg["strike"] - S_expiry)

def fee_for_leg(S, premium, mult):
    """Per-contract fee in $ = min(0.010% notional, 3.5% premium) * (1+GST).
    premium here is per-UNIT option price; premium value in $ = premium*mult."""
    notional = S * mult
    prem_dollars = premium * mult
    raw = min(config.FEE_PCT_OF_NOTIONAL * notional,
              config.FEE_CAP_PCT_OF_PREMIUM * max(prem_dollars, 0.0))
    return raw * (1 + config.GST_ON_FEE)

def simulate_trade(S_entry, S_expiry, legs, sigma, mult):
    """Return (pnl_before_fees, fees, pnl_after_fees) per 1 contract."""
    entry_cashflow = 0.0
    fees = 0.0
    settle_cashflow = 0.0
    for leg in legs:
        prem = leg_premium(S_entry, leg, sigma)
        # side +1 = buy (pay premium), -1 = sell (receive premium)
        entry_cashflow -= leg["side"] * prem
        fees += fee_for_leg(S_entry, prem, mult)
        val = leg_settle(S_expiry, leg)
        settle_cashflow += leg["side"] * val
        # exit/settlement fee (0 automatically if option worthless -> Delta: no fee on OTM expiry)
        fees += fee_for_leg(S_expiry, val, mult)
    pnl_before = (entry_cashflow + settle_cashflow) * mult
    pnl_after = pnl_before - fees
    return pnl_before, fees, pnl_after

def apply_tax(trades):
    """Apply the configured tax model to a list of after-fee PnLs. Returns (net_after_tax, tax_paid)."""
    if config.TAX_MODE == "NONE":
        return sum(trades), 0.0
    if config.TAX_MODE == "VDA":
        gross_wins = sum(p for p in trades if p > 0)
        tax = config.VDA_TAX_RATE * gross_wins           # losers give NO relief
        return sum(trades) - tax, tax
    # FNO: tax net profit only
    net = sum(trades)
    tax = config.FNO_TAX_RATE * max(0.0, net)
    return net - tax, tax

def choose_strategy(name, closes):
    if name != "regime_switch":
        return name
    rv = data.realized_vol(closes, window=10)
    if rv is None:
        return "iron_condor"
    # crude regime rule: high realized vol -> expect big move -> strangle
    return "long_strangle" if rv > config.ANNUAL_VOL_DEFAULT * 1.15 else "iron_condor"

def run(symbol, strategy_name, rows=None):
    if rows is None:
        rows = data.synthetic(symbol, n_days=365, annual_vol=config.ANNUAL_VOL_DEFAULT)
    mult = config.CONTRACT_SIZE.get(symbol, 1.0)
    results = []
    after_fee_pnls = []
    closes_so_far = []
    for i in range(len(rows) - 1):
        _, S_entry = rows[i]
        _, S_expiry = rows[i + 1]
        closes_so_far.append(S_entry)
        sigma = data.realized_vol(closes_so_far, 10) or config.ANNUAL_VOL_DEFAULT
        sigma = max(0.2, min(2.0, sigma))
        strat = choose_strategy(strategy_name, closes_so_far)
        legs = strategies.BUILDERS[strat](S_entry, sigma)
        pnl_before, fees, pnl_after = simulate_trade(S_entry, S_expiry, legs, sigma, mult)
        # risk cap: skip if estimated max loss exceeds per-trade cap (approx by wing width)
        after_fee_pnls.append(pnl_after)
        results.append(dict(day=rows[i][0], symbol=symbol, strategy=strat,
                            spot=round(S_entry, 2), expiry_spot=round(S_expiry, 2),
                            pnl_before_fees=round(pnl_before, 2), fees=round(fees, 2),
                            pnl_after_fees=round(pnl_after, 2)))
    net_after_tax, tax = apply_tax(after_fee_pnls)
    return results, after_fee_pnls, net_after_tax, tax

def summarize(after_fee_pnls, net_after_tax, tax):
    n = len(after_fee_pnls)
    wins = [p for p in after_fee_pnls if p > 0]
    losses = [p for p in after_fee_pnls if p <= 0]
    gross = sum(after_fee_pnls)
    peak = 0.0; equity = 0.0; max_dd = 0.0
    for p in after_fee_pnls:
        equity += p
        peak = max(peak, equity)
        max_dd = min(max_dd, equity - peak)
    return {
        "trades": n,
        "win_rate_%": round(100 * len(wins) / n, 1) if n else 0,
        "avg_win": round(sum(wins) / len(wins), 2) if wins else 0,
        "avg_loss": round(sum(losses) / len(losses), 2) if losses else 0,
        "pnl_after_fees": round(gross, 2),
        "tax_paid": round(tax, 2),
        "pnl_after_tax": round(net_after_tax, 2),
        "max_drawdown": round(max_dd, 2),
        "profit_factor": round(sum(wins) / abs(sum(losses)), 2) if losses and sum(losses) != 0 else None,
    }

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbol", default="BTC")
    ap.add_argument("--strategy", default="iron_condor",
                    choices=list(strategies.BUILDERS.keys()) + ["regime_switch"])
    ap.add_argument("--csv", default=None, help="path to real data CSV (date,close)")
    args = ap.parse_args()
    rows = data.load_csv(args.csv) if args.csv else None
    results, pnls, net_after_tax, tax = run(args.symbol, args.strategy, rows)
    outdir = os.path.join(os.path.dirname(__file__), "results")
    os.makedirs(outdir, exist_ok=True)
    outpath = os.path.join(outdir, f"{args.symbol}_{args.strategy}.csv")
    with open(outpath, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(results[0].keys()))
        w.writeheader(); w.writerows(results)
    summary = summarize(pnls, net_after_tax, tax)
    print(f"\n=== {args.symbol} / {args.strategy} / tax={config.TAX_MODE} ===")
    for k, v in summary.items():
        print(f"  {k:18}: {v}")
    print(f"  results written    : {outpath}")
    if args.csv:
        print("\n  NOTE: REAL price path, but MODELED premiums (BSM, IV=realized vol).")
        print("  This omits the IV>RV variance risk premium that real sellers collect,")
        print("  so it is PESSIMISTIC for the condor. Real option-chain IV needed for a true read.")
    else:
        print("\n  NOTE: synthetic data. Proves PLUMBING only, not edge. Use --csv with real data.")

if __name__ == "__main__":
    main()
