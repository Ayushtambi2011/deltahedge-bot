"""Market intelligence from Delta's OWN option-chain Open Interest — free and real.
This replaces the paid Coinglass heatmap with the actual positioning on the exchange you
trade: OI walls (support/resistance / "order blocks"), max pain, and put/call sentiment.

analyze(chain) takes the normalized chain from delta_client.get_chain() and returns a dict.
"""


def analyze(chain):
    if not chain:
        return None
    spot = chain[0].get("spot")
    calls = [r for r in chain if r["type"] == "call" and r.get("oi")]
    puts = [r for r in chain if r["type"] == "put" and r.get("oi")]
    call_oi = sum(r["oi"] for r in calls)
    put_oi = sum(r["oi"] for r in puts)
    pcr = round(put_oi / call_oi, 2) if call_oi else None

    # OI walls: heaviest call OI = resistance (above), heaviest put OI = support (below)
    resistance = [r["strike"] for r in sorted(calls, key=lambda r: -r["oi"])[:3]]
    support = [r["strike"] for r in sorted(puts, key=lambda r: -r["oi"])[:3]]

    # Max pain: expiry price that minimizes total intrinsic paid to option holders
    strikes = sorted({r["strike"] for r in chain if r.get("oi")})

    def pain(K):
        tot = 0.0
        for r in chain:
            if not r.get("oi"):
                continue
            intr = max(0.0, K - r["strike"]) if r["type"] == "call" else max(0.0, r["strike"] - K)
            tot += r["oi"] * intr
        return tot

    max_pain = min(strikes, key=pain) if strikes else None

    # IV skew: 25-delta put IV vs call IV (fear gauge)
    def iv_at(kind, td):
        cs = [r for r in chain if r["type"] == kind and r.get("delta") is not None and r.get("iv")]
        if not cs:
            return None
        return min(cs, key=lambda r: abs(abs(r["delta"]) - td)).get("iv")
    put_iv = iv_at("put", 0.25)
    call_iv = iv_at("call", 0.25)
    skew = round(put_iv - call_iv, 1) if (put_iv and call_iv) else None

    # Simple bias: combine PCR, spot vs max pain, skew
    bias, notes = _bias(spot, max_pain, pcr, skew)

    return {
        "spot": spot, "pcr": pcr, "max_pain": max_pain,
        "resistance": sorted(resistance, reverse=True), "support": sorted(support, reverse=True),
        "put_iv": put_iv, "call_iv": call_iv, "skew": skew,
        "bias": bias, "bias_notes": notes,
        "call_oi": round(call_oi), "put_oi": round(put_oi),
    }


def _bias(spot, max_pain, pcr, skew):
    score = 0
    notes = []
    if spot and max_pain:
        if max_pain < spot * 0.995:
            score -= 1; notes.append(f"max pain {max_pain:.0f} below spot (gravity down)")
        elif max_pain > spot * 1.005:
            score += 1; notes.append(f"max pain {max_pain:.0f} above spot (gravity up)")
    if pcr is not None:
        if pcr > 1.2:
            score -= 1; notes.append(f"PCR {pcr} high (heavy put OI)")
        elif pcr < 0.7:
            score += 1; notes.append(f"PCR {pcr} low (heavy call OI)")
    if skew is not None and skew > 3:
        score -= 1; notes.append(f"put skew +{skew} (downside fear)")
    label = ("Bullish" if score >= 2 else "Slightly Bullish" if score == 1 else
             "Bearish" if score <= -2 else "Slightly Bearish" if score == -1 else "Neutral")
    return label, notes


if __name__ == "__main__":
    import delta_client as dc
    for a in ("BTC", "ETH"):
        try:
            ch = dc.get_chain(a, dc.nearest_expiry(a))
            print(a, analyze(ch))
        except Exception as e:
            print(a, "failed:", e)
