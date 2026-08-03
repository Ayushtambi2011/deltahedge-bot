"""Nightly-style review: reads a results CSV and prints per-strategy stats after
fees, then after tax under all three tax models so you can see the tax impact.
Run:  python3 review.py results/BTC_iron_condor.csv
"""
import csv, sys, os
sys.path.insert(0, os.path.dirname(__file__))
import config
from engine import apply_tax, summarize

def load(path):
    with open(path) as f:
        return [float(r["pnl_after_fees"]) for r in csv.DictReader(f)]

def main():
    if len(sys.argv) < 2:
        print("usage: python3 review.py results/<file>.csv"); return
    pnls = load(sys.argv[1])
    print(f"\nReview: {sys.argv[1]}  ({len(pnls)} trades)")
    for mode in ("NONE", "FNO", "VDA"):
        config.TAX_MODE = mode
        net, tax = apply_tax(pnls)
        s = summarize(pnls, net, tax)
        print(f"\n  tax_mode={mode}")
        print(f"    after-fees PnL : {s['pnl_after_fees']}")
        print(f"    tax paid       : {s['tax_paid']}")
        print(f"    after-tax PnL  : {s['pnl_after_tax']}")
    print("\n  If VDA after-tax PnL is negative while FNO is positive, your tax")
    print("  classification alone decides viability. See docs/01_TAX.md.")

if __name__ == "__main__":
    main()
