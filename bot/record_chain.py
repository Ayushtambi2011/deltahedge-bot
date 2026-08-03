"""Record a daily snapshot of the nearest-expiry BTC/ETH option chain to data/chains/.

WHY: Delta's API serves the LIVE chain, not a historical archive of expired daily options.
The only free way to get REAL backtest premiums is to record the chain forward, once a day.
Run this via cron at (or near) your intended entry time. After ~20-30 days you have a real
dataset the backtester can use (backtester/real_backtest.py).

Run: python3 record_chain.py
Cron: 30 3 * * *  cd .../bot && python3 record_chain.py >> ../data/record.log 2>&1
"""
import csv
import os
import datetime
import delta_client as dc

FIELDS = ["ts", "asset", "type", "strike", "expiry", "mark", "mid", "iv",
          "delta", "gamma", "theta", "vega", "oi", "best_bid", "best_ask",
          "spread", "spot", "symbol"]

OUTDIR = os.path.join(os.path.dirname(__file__), "..", "data", "chains")


def record(asset):
    exp = dc.nearest_expiry(asset)
    if not exp:
        print(f"{asset}: no expiry found"); return None
    chain = dc.get_chain(asset, exp)
    ts = datetime.datetime.utcnow().isoformat()
    os.makedirs(OUTDIR, exist_ok=True)
    path = os.path.join(OUTDIR, f"{asset}_{datetime.date.today().isoformat()}.csv")
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        for r in chain:
            row = dict(r); row["ts"] = ts; row["asset"] = asset
            w.writerow({k: row.get(k) for k in FIELDS})
    print(f"{asset}: recorded {len(chain)} rows for expiry {exp} -> {path}")
    return path


if __name__ == "__main__":
    for a in ("BTC", "ETH"):
        try:
            record(a)
        except Exception as e:
            print(f"{a}: record failed: {e}")
