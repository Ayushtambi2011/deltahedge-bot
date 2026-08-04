"""Confirm the Delta gold symbol + candle feed work. Run locally: python3 gold_test.py
Tries a few likely symbols and prints which one returns 15-min candles."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
import delta_client as dc
import gold_strategy as g

CANDIDATES = [os.environ.get("GOLD_SYMBOL", "XAUUSD"), "XAUUSD", "XAUUSDT", "XAU_USDT", "GOLD"]

def main():
    seen = set()
    for sym in CANDIDATES:
        if sym in seen:
            continue
        seen.add(sym)
        try:
            g.GOLD_SYMBOL = sym
            c = g.candles(sym, "15m", count=60)
            if c:
                print(f"✓ {sym}: got {len(c)} 15m candles. last close = {c[-1]['c']}")
                d, e20, e50 = g.trend_dir(c)
                print(f"   direction: {'LONG' if d>0 else 'SHORT' if d<0 else 'none'} "
                      f"(20EMA {round(e20[-1],2) if e20[-1] else '-'} vs 50EMA {round(e50[-1],2) if e50[-1] else '-'})")
                print(f"\nUse this symbol. Set GOLD_SYMBOL={sym} in the desk-gold workflow if not XAUUSD.")
                return
            else:
                print(f"· {sym}: no candles")
        except Exception as e:
            print(f"· {sym}: error {e}")
    print("\n✗ None worked — paste me the output and I'll find the right symbol.")

if __name__ == "__main__":
    main()
