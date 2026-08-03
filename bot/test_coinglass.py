"""Local Coinglass key test — RUN THIS ON YOUR MACHINE (never paste the key in chat).

1. Put your key in bot/.env:   COINGLASS_API_KEY=your_key_here
2. cd bot && python3 test_coinglass.py

It reports: does the key authenticate? does your plan include the heatmap? and what the
response shape looks like — so we can finalize parsing in liquidation.py if needed.
It prints only the response STRUCTURE and a few price levels, never your key.
"""
import json
import os
import sys

# load .env
envp = os.path.join(os.path.dirname(__file__), ".env")
if os.path.exists(envp):
    for line in open(envp):
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

import requests

KEY = os.environ.get("COINGLASS_API_KEY", "").strip()
URL = "https://open-api-v4.coinglass.com/api/futures/liquidation/heatmap/model2"


def main():
    if not KEY:
        print("✗ No COINGLASS_API_KEY found in bot/.env — add it and retry."); sys.exit(1)
    print(f"Key loaded (…{KEY[-4:]}). Calling heatmap/model2 for Binance BTCUSDT 24h…\n")
    try:
        r = requests.get(URL, params={"exchange": "Binance", "symbol": "BTCUSDT", "range": "24h"},
                         headers={"CG-API-KEY": KEY, "accept": "application/json"}, timeout=25)
    except Exception as e:
        print("✗ Request failed:", e); sys.exit(1)

    print("HTTP", r.status_code)
    try:
        j = r.json()
    except Exception:
        print("Non-JSON response:", r.text[:400]); sys.exit(1)

    code = j.get("code")
    if code not in (None, "0", 0):
        print(f"✗ API says code={code} msg={j.get('msg')}")
        print("  (30001=key missing, 40001/auth=plan doesn't include this endpoint, etc.)")
        sys.exit(1)

    data = j.get("data", j)
    print("✓ Authenticated. Response top-level keys:", list(j.keys()))
    if isinstance(data, dict):
        print("  data keys:", list(data.keys()))
        for k, v in data.items():
            print(f"    {k}: {type(v).__name__}", (f"len={len(v)}" if hasattr(v, '__len__') else v))
    elif isinstance(data, list):
        print(f"  data is a list of {len(data)}; first item:", json.dumps(data[0])[:300] if data else "—")

    # try our parser
    sys.path.insert(0, os.path.dirname(__file__))
    import liquidation
    lv = liquidation._parse_heatmap(j)
    print(f"\nParser produced {len(lv)} price levels.")
    if lv:
        top = sorted(lv, key=lambda x: -x["intensity"])[:6]
        print("Heaviest clusters:")
        for l in top:
            print(f"    {l['price']:>10,.0f}   intensity {l['intensity']}")
        print("\n✓ Working. run_desk.py will now use live Coinglass levels automatically.")
    else:
        print("\n⚠ Parser got 0 levels — the response shape differs from the default.")
        print("  Paste ONLY the 'data keys' / structure lines above back to me (NOT your key)")
        print("  and I'll adjust liquidation._parse_heatmap to match.")


if __name__ == "__main__":
    main()
