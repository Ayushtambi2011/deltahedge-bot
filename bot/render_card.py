"""Render a trade signal as a clean JPEG card (like a shareable infographic) for Telegram.
Uses Pillow + the DejaVu fonts that ship on GitHub's ubuntu runners. Falls back gracefully.
"""
import os
import tempfile

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    Image = None

_FONTDIR = "/usr/share/fonts/truetype/dejavu"
_BOLD = os.path.join(_FONTDIR, "DejaVuSans-Bold.ttf")
_REG = os.path.join(_FONTDIR, "DejaVuSans.ttf")
_MONO = os.path.join(_FONTDIR, "DejaVuSansMono.ttf")

BG = (11, 16, 32)
CARD = (20, 27, 48)
WHITE = (232, 237, 249)
MUT = (138, 151, 184)
GREEN = (52, 211, 153)
RED = (248, 113, 113)
AMBER = (251, 191, 36)


def _font(path, size):
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        return ImageFont.load_default()


def available():
    return Image is not None


def render_signal(asset, strat, exp_type, exp, subtitle, legs_lines, stats, tp_line,
                  sl_line, footer, accent=GREEN):
    """legs_lines: list of "SELL 240x CALL 1950 @ 8.6" strings.
    stats: list of (label, value) tuples. Returns path to a JPEG, or None if PIL missing."""
    if Image is None:
        return None
    W = 900
    pad = 40
    y = 0
    rows = len(legs_lines)
    H = 300 + rows * 46 + len(stats) * 0 + 260
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)

    f_title = _font(_BOLD, 46)
    f_sub = _font(_REG, 26)
    f_leg = _font(_MONO, 30)
    f_lbl = _font(_REG, 24)
    f_val = _font(_BOLD, 34)
    f_small = _font(_REG, 22)

    # header band
    d.rectangle([0, 0, W, 130], fill=accent)
    d.text((pad, 26), f"{asset}  {strat.replace('_',' ').upper()}", font=f_title, fill=(6, 12, 20))
    d.text((pad, 82), f"{exp_type.upper()} · exp {exp}", font=f_sub, fill=(6, 12, 20))
    y = 160

    # subtitle
    d.text((pad, y), subtitle, font=f_sub, fill=MUT)
    y += 50

    # legs box
    box_h = rows * 46 + 24
    d.rounded_rectangle([pad, y, W - pad, y + box_h], radius=16, fill=CARD)
    ly = y + 14
    for line in legs_lines:
        col = RED if line.strip().startswith("SELL") else GREEN
        d.text((pad + 20, ly), line, font=f_leg, fill=col)
        ly += 46
    y += box_h + 30

    # stats row
    n = len(stats)
    if n:
        cw = (W - 2 * pad) // n
        for i, (lbl, val, col) in enumerate(stats):
            x = pad + i * cw
            d.text((x, y), lbl, font=f_lbl, fill=MUT)
            d.text((x, y + 30), val, font=f_val, fill=col)
        y += 90

    # TP / SL
    d.rounded_rectangle([pad, y, W - pad, y + 96], radius=16, fill=CARD)
    d.text((pad + 20, y + 14), tp_line, font=f_sub, fill=GREEN)
    d.text((pad + 20, y + 52), sl_line, font=f_sub, fill=RED)
    y += 126

    # footer
    d.rectangle([0, H - 70, W, H], fill=(40, 12, 12))
    d.text((pad, H - 52), footer, font=f_small, fill=AMBER)

    path = os.path.join(tempfile.gettempdir(), f"signal_{asset}_{strat}.jpg")
    img.convert("RGB").save(path, "JPEG", quality=88)
    return path


if __name__ == "__main__":
    p = render_signal(
        "BTC", "iron_condor", "daily", "2026-08-11",
        "spot 62,730 · IV rank 62% · sell premium",
        ["SELL 240x CALL 65200 @ 180", "BUY  240x CALL 66400 @ 60",
         "SELL 240x PUT 60000 @ 190", "BUY  240x PUT 58800 @ 70"],
        [("Credit", "$24.96", GREEN), ("Max loss", "$99.84", RED), ("POP", "68%", WHITE)],
        "TP: buy back <= $12.48  -> +$12.48",
        "SL: cost hits $49.92  -> -$24.96",
        "PAPER - not executed. Manage as ONE position.",
    )
    print("wrote", p)
