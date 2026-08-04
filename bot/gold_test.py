"""Find the Delta gold symbol + confirm the candle feed. Run: python3 gold_test.py
1) sanity-checks BTCUSD candles (is the pipeline working?),
2) asks Delta for all perpetual products and prints any gold/XAU ones,
3) tries candles for each gold symbol found.
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
import delta_client as dc
import gold_strategy as g


def main():
    # 1) pipeline sanity check with a known symbol
    try:
        b = g.candles("BTCUSD", "15m", count=30)
        print(f"[pipeline] BTCUSD 15m -> {len(b)} candles" +
              (f", last={b[-1]['c']}" if b else "  (EMPTY — candle pipeline problem, not the symbol)"))
    except Exception as e:
        print(f"[pipeline] BTCUSD error: {e}")

    # 2) discover gold perpetual symbol(s)
    print("\n[discover] fetching perpetual products…")
    gold_syms = []
    try:
        res = dc._get("/v2/products", params={"contract_types": "perpetual_futures"}).get("result", [])
        for p in res:
            sym = p.get("symbol", "")
            desc = (p.get("description") or "") + " " + (p.get("underlying_asset", {}) or {}).get("symbol", "")
            if "XAU" in sym.upper() or "GOLD" in sym.upper() or "GOLD" in desc.upper() or "XAU" in desc.upper():
                gold_syms.append(sym)
                print(f"   found: {sym}   ({p.get('description','')})")
    except Exception as e:
        print(f"   products fetch failed: {e}")

    if not gold_syms:
        print("   no gold perpetual found via products. Paste this whole output to me.")
        return

    # 3) test candles for each gold symbol
    print("\n[candles] testing gold symbols…")
    for sym in gold_syms:
        try:
            c = g.candles(sym, "15m", count=60)
            if c:
                print(f"✓ {sym}: {len(c)} 15m candles, last close = {c[-1]['c']}")
                print(f"\n>>> Use GOLD_SYMBOL = {sym}")
                return
            print(f"· {sym}: no candles")
        except Exception as e:
            print(f"· {sym}: error {e}")


if __name__ == "__main__":
    main()
