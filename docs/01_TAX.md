# 01 — Tax (UPDATED: not the project-killer, but keep documentation)

**Not tax advice. Get your CA to confirm the position IN WRITING for your account.**

## Updated position (Aug 2026)
Earlier draft assumed worst-case VDA treatment. Verified against Delta's own tax FAQ and
multiple CA sources, the **prevailing position is more favourable**:

- Delta Exchange India's stated position: F&O contracts on the platform **do NOT qualify as
  VDA trading** → the **30% flat VDA tax does not apply**.
- Profits are taxed at your **income-tax slab rate** as **business income** (speculative or
  non-speculative under Section 28) — **not** capital gains, and **not** flat 30%.
- **Losses CAN be netted and offset.** This is the key win — it makes an active,
  many-trades strategy viable (unlike VDA, which taxes gross winners with no relief).

## Why this matters
A strategy of many small wins minus occasional losses is **only viable if losses net
against gains.** Under the F&O/business-income treatment they do. That removes the
structural tax problem that would have killed a high-frequency approach.

## The caveats (do not skip)
- **Grey zone, not settled law.** IT Department has issued no clear guidance; it's an
  "arguable position" with litigation risk. 2026 enforcement is tighter (exchanges share
  data with the ITD).
- **File correctly:** business income under **ITR-3**. Keep Delta's **contract
  specifications** and a written CA opinion as documentation.
- **Slab isn't automatically < 30%.** At high total income, top slab + surcharge can
  approach or exceed 30%. The advantage is **loss set-off**, not necessarily a lower rate.
- **Speculative vs non-speculative** classification affects how losses can be set off —
  confirm which applies with your CA.

## Action
- [x] Confirmed prevailing treatment = business income at slab, losses offsettable.
- [ ] Get CA's written opinion citing Delta's contract specs (cover for scrutiny).
- [ ] Set your marginal slab rate in `backtester/config.py` (`FNO_TAX_RATE`).
- [ ] Backtester default tax model is now **FNO** (net-profit taxation with loss offset).

## Sources
- [Delta Exchange — Is 30% VDA tax applicable on trading profits?](https://www.delta.exchange/support/solutions/articles/80001132761-is-there-30-vda-tax-applicable-on-trading-profits-)
- [Delta Exchange — Is loss offsetting available on F&O profits?](https://www.delta.exchange/support/solutions/articles/80001132762-is-loss-offsetting-available-on-profits-that-i-make-via-trading-crypto-futures-and-options-contracts-)
- [Tax2win — Crypto Derivatives, Options and Futures](https://tax2win.in/guide/crypto-derivatives)
- [CoinSwitch — Crypto Futures & Options Tax India 2026](https://coinswitch.co/switch/crypto-futures-derivatives/crypto-futures-options-tax/)
- [CA Delhi India — Crypto Futures Taxation: Business Income or 30% VDA?](https://www.caindelhiindia.com/blog/crypto-futures-taxation/)
