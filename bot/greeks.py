"""Position-greeks risk module. Uses REAL per-strike greeks from the Delta chain
(delta, gamma, theta, vega are in the ticker response) to compute NET position greeks
and gate trades. This is the most defensible of the new inputs — it uses data you
already pull, and enforces the hedge you actually want.

For a hedged daily condor you want:
  net delta  ~ 0        (directionally neutral)
  net theta  > 0        (you're paid to wait)
  net vega   < 0 but bounded (short vol; cap the size of the bet)
  net gamma  < 0 but bounded (short gamma; the near-expiry danger)
"""
CONTRACT_SIZE = {"BTC": 0.001, "ETH": 0.01}


def _lookup(chain, kind, strike):
    for r in chain:
        if r["type"] == kind and abs(r["strike"] - strike) < 1e-6:
            return r
    # nearest fallback
    cands = [r for r in chain if r["type"] == kind]
    return min(cands, key=lambda r: abs(r["strike"] - strike)) if cands else None


def net_greeks(legs, chain, mult):
    tot = {"delta": 0.0, "gamma": 0.0, "theta": 0.0, "vega": 0.0}
    for leg in legs:
        row = _lookup(chain, leg["type"], leg["strike"])
        if not row:
            continue
        for g in tot:
            v = row.get(g)
            if v is not None:
                tot[g] += leg["side"] * v * mult
    return tot


# strategies that are LONG volatility / debit — negative theta & non-neutral are BY DESIGN
LONG_VOL = {"long_strangle", "long_straddle", "calendar_spread"}


def check(legs, chain, asset, spot, strategy="iron_condor", caps=None):
    """Return (ok, greeks, warnings). Gates only CREDIT structures on neutrality + positive
    theta. Long-vol structures (strangle etc.) are expected to be non-neutral / negative
    theta, so those are reported as info, not failures."""
    mult = CONTRACT_SIZE.get(asset, 1.0)
    g = net_greeks(legs, chain, mult)
    caps = caps or {}
    delta_usd = g["delta"] * (spot or 0)          # $ of directional exposure
    warnings = []
    if strategy in LONG_VOL:
        # long-vol: just note the profile, never fail it
        if g["theta"] < 0:
            warnings.append(f"long-vol: paying theta {g['theta']:.4f} (expected)")
        return True, g, warnings
    # credit structures: enforce neutrality + positive theta
    max_delta_usd = caps.get("max_delta_usd", 15.0)
    if abs(delta_usd) > max_delta_usd:
        warnings.append(f"not neutral: net delta ${delta_usd:+.2f} (cap ${max_delta_usd})")
    if g["theta"] < 0:
        warnings.append(f"negative theta {g['theta']:.4f} — wrong for a credit trade")
    ok = len(warnings) == 0
    return ok, g, warnings


if __name__ == "__main__":
    # tiny self-test with fake chain
    chain = [
        {"type": "call", "strike": 66000, "delta": 0.16, "gamma": 0.0001, "theta": -5, "vega": 8},
        {"type": "call", "strike": 67200, "delta": 0.06, "gamma": 0.00005, "theta": -2, "vega": 4},
        {"type": "put", "strike": 60000, "delta": -0.16, "gamma": 0.0001, "theta": -5, "vega": 8},
        {"type": "put", "strike": 58800, "delta": -0.06, "gamma": 0.00005, "theta": -2, "vega": 4},
    ]
    legs = [{"type": "call", "strike": 66000, "side": -1}, {"type": "call", "strike": 67200, "side": +1},
            {"type": "put", "strike": 60000, "side": -1}, {"type": "put", "strike": 58800, "side": +1}]
    ok, g, w = check(legs, chain, "BTC", 63000)
    print("net greeks:", {k: round(v, 6) for k, v in g.items()})
    print("ok:", ok, "warnings:", w)
