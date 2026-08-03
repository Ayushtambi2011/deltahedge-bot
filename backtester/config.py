"""Backtester configuration. Edit these to match reality, then re-run.

IMPORTANT: the tax model here is a SWITCH. Set TAX_MODE after you get a CA's
written answer (see docs/01_TAX.md). It changes the result dramatically.
"""

# --- Capital & sizing (sized to $1,000 / ~Rs 85k; see docs/04_ARCHITECTURE.md) ---
CAPITAL_USD = 1000.0
MAX_RISK_PER_TRADE_USD = 35.0      # realized-loss stop ~3.5% of capital; position max loss <= this
DAILY_STOP_USD = 50.0              # halt for the day at 5% realized loss (~2 bad trades)
WEEKLY_STOP_USD = 150.0            # halt for the week at 15%
MAX_MARGIN_UTIL_PCT = 0.30         # a single position may lock at most 30% of capital as margin
MAX_CONCURRENT_POSITIONS = 1       # one at a time (BTC OR ETH by score) — both = over-leverage at $1k
CONTRACT_MULTIPLIER = 1.0          # set to Delta's actual contract size for BTC/ETH options

# --- Fees (EXACT, from Delta fee page fetched 2026-08-03; see docs/02_FEES.md) ---
# Options maker AND taker = 0.010% of NOTIONAL (Notional = Spot * Qty).
# Fee capped at 3.5% of premium; cap applies only when notional-fee > premium-fee.
# A SHORT option expiring OTM (worthless) pays NO exit fee. +18% GST on the fee.
FEE_PCT_OF_NOTIONAL = 0.0001       # 0.010% options maker/taker
FEE_CAP_PCT_OF_PREMIUM = 0.035     # capped at 3.5% of premium
GST_ON_FEE = 0.18                  # 18% GST on the fee itself

# Delta contract sizes (verify ETH on the venue). Notional = Spot * contract_size * n_contracts.
CONTRACT_SIZE = {"BTC": 0.001, "ETH": 0.01}

# --- Tax model (THE decisive variable) ---
# "FNO"  -> tax on NET profit, losses net against gains (business income at slab) <- DEFAULT
#           This is the prevailing treatment for Delta India F&O (see docs/01_TAX.md).
# "VDA"  -> 30% on GROSS winning trades, NO loss set-off (worst case; kept for stress-testing)
# "NONE" -> ignore tax (only for pre-tax edge inspection)
TAX_MODE = "FNO"
FNO_TAX_RATE = 0.30               # set to YOUR marginal slab rate (+ surcharge if applicable)
VDA_TAX_RATE = 0.30                # only used if you switch to VDA to stress-test

# --- Strategy defaults ---
SHORT_DELTA = 0.16                 # condor short-strike delta target (~84% OTM)
WING_WIDTH_PCT = 0.02              # long wing this far beyond short strike, as % of spot
PROFIT_TAKE = 0.50                 # close credit trades at 50% of max profit
STOP_MULT = 2.0                    # stop at 2x credit loss

# --- Market assumptions for the synthetic pricer (until real data plugged in) ---
ANNUAL_VOL_DEFAULT = 0.60          # ~60% annualized vol proxy for BTC daily options IV
RISK_FREE = 0.06
TRADING_DAYS = 365                 # crypto trades daily
