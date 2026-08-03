"""Strategy builders. Each returns a list of legs for a 1-day-to-expiry structure.
A leg = dict(kind, strike, side) where side = +1 (long/buy) or -1 (short/sell).
Entry premium and expiry settlement are computed by the engine."""
import config
import bsm

DAY = 1.0 / 365  # daily expiry ~ 1 day to expiry

def iron_condor(S, sigma):
    sc = bsm.strike_for_delta(S, DAY, config.RISK_FREE, sigma, config.SHORT_DELTA, "call")
    sp = bsm.strike_for_delta(S, DAY, config.RISK_FREE, sigma, config.SHORT_DELTA, "put")
    w = S * config.WING_WIDTH_PCT
    return [
        dict(kind="call", strike=sc, side=-1),
        dict(kind="call", strike=round(sc + w), side=+1),
        dict(kind="put", strike=sp, side=-1),
        dict(kind="put", strike=round(sp - w), side=+1),
    ]

def iron_butterfly(S, sigma):
    atm = round(S)
    w = S * config.WING_WIDTH_PCT * 1.5
    return [
        dict(kind="call", strike=atm, side=-1),
        dict(kind="put", strike=atm, side=-1),
        dict(kind="call", strike=round(atm + w), side=+1),
        dict(kind="put", strike=round(atm - w), side=+1),
    ]

def long_strangle(S, sigma):
    sc = bsm.strike_for_delta(S, DAY, config.RISK_FREE, sigma, 0.25, "call")
    sp = bsm.strike_for_delta(S, DAY, config.RISK_FREE, sigma, 0.25, "put")
    return [
        dict(kind="call", strike=sc, side=+1),
        dict(kind="put", strike=sp, side=+1),
    ]

BUILDERS = {
    "iron_condor": iron_condor,
    "iron_butterfly": iron_butterfly,
    "long_strangle": long_strangle,
}
