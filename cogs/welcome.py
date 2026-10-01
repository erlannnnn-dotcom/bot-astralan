import asyncio
import math
import random
from datetime import datetime, timedelta, timezone
from functools import lru_cache, partial
from io import BytesIO
from typing import Optional

import discord
import numpy as np
from discord.ext import commands
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont, ImageOps

# ══════════════════════════════════════════════════════════════════════════════
#  KONFIGURASI
# ══════════════════════════════════════════════════════════════════════════════
WELCOME_CHANNEL_ID = 1497149920006639718
LEAVE_CHANNEL_ID   = 1497151497983623320   # ganti kalau channel leave beda

SERVER_NAME = "Astralan"
SKIP_BOTS   = True                          # True = akun bot tidak dikirimi notif
UTC_OFFSET  = 7                             # WIB = UTC+7

BG_PATH      = "welcome_bg.png"             # logo Astralan (PNG transparan, 3264x3264)
FONT_BOLD    = "fonts/LEMONMILK-Bold.otf"
FONT_REGULAR = "fonts/LEMONMILK-Regular.otf"
FONT_ITALIC  = "fonts/LEMONMILK-RegularItalic.otf"

W, H = 1280, 720                            # 16:9
CX, CY, D = 640, 228, 220                   # pusat & diameter avatar

THEMES = {
    "welcome": dict(
        acc=(150, 120, 255), acc2=(90, 190, 255), glow=(110, 70, 255),
        neb=((90, 50, 220), (40, 110, 230)), seed=7, badge="+",
        label="W E L C O M E",
        sub="Astrans baru telah bergabung",
        side_label="M E M B E R",
        side_sub="Anggota baru Server",
        status="• JOINED",
        footer_msg="Semoga betah dan jangan lupa baca #rules",
        name_grad=((255, 255, 255), (200, 170, 255)),
        embed_color=0x9B45FF,
        filename="welcome.png",
    ),
    "leave": dict(
        acc=(214, 120, 255), acc2=(255, 120, 220), glow=(200, 70, 235),
        neb=((170, 50, 200), (230, 70, 160)), seed=3, badge="-",
        label="G O O D B Y E",
        sub="Satu Astrans telah meninggalkan Server",
        side_label="S I S A   M E M B E R",
        side_sub="Terima kasih telah singgah",
        status="• LEFT",
        footer_msg="Sampai jumpa lagi, semoga bertemu di Server lain",
        name_grad=((255, 255, 255), (255, 200, 245)),
        embed_color=0xC44BE0,
        filename="goodbye.png",
    ),
}

MONTHS = ["JAN", "FEB", "MAR", "APR", "MEI", "JUN", "JUL", "AGU", "SEP", "OKT", "NOV", "DES"]


# ══════════════════════════════════════════════════════════════════════════════
#  HELPER GAMBAR
# ══════════════════════════════════════════════════════════════════════════════
@lru_cache(maxsize=64)
def _font(path: str, size: int):
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        try:
            return ImageFont.load_default(size)
        except TypeError:
            return ImageFont.load_default()


def _fit(draw, text, path, start, minimum, max_w):
    """Kecilkan font sampai teks muat; kalau masih kepanjangan, dipotong pakai '...'."""
    size = start
    while size >= minimum:
        f = _font(path, size)
        if draw.textlength(text, font=f) <= max_w:
            return f, text
        size -= 2
    f = _font(path, minimum)
    while len(text) > 1 and draw.textlength(text + "...", font=f) > max_w:
        text = text[:-1]
    return f, text + "..."


def _prep_logo(path: str) -> Image.Image:
    logo = Image.open(path).convert("RGBA")
    bbox = logo.getchannel("A").getbbox()
    return logo.crop(bbox) if bbox else logo


def _lg(logo: Image.Image, w: int) -> Image.Image:
    return logo.resize((w, int(logo.height * w / logo.width)), Image.LANCZOS)


def _blob(img, xy, r, col, a, blur):
    l = Image.new("RGBA", img.size, (0, 0, 0, 0))
    x, y = xy
    ImageDraw.Draw(l).ellipse((x - r, y - r, x + r, y + r), fill=(*col, a))
    img.alpha_composite(l.filter(ImageFilter.GaussianBlur(blur)))


def _stars(img, n, col, seed):
    rnd = random.Random(seed)
    g = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(g)
    for _ in range(n):
        x, y = rnd.randint(0, W), rnd.randint(0, H - 80)
        s = rnd.choice([1, 1, 1, 2, 2, 3])
        d.ellipse((x - s, y - s, x + s, y + s), fill=(*col, rnd.randint(80, 230)))
    img.alpha_composite(g.filter(ImageFilter.GaussianBlur(0.6)))
    g = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(g)
    for _ in range(4):  # sparkle 4 arah
        x, y = rnd.randint(40, W - 40), rnd.randint(25, H - 60)
        l = rnd.randint(10, 20)
        if x < 300 and y < 120:  # jangan menimpa logo di pojok kiri atas
            x += 300
        d.polygon([(x, y - l), (x + 2, y - 2), (x + l, y), (x + 2, y + 2),
                   (x, y + l), (x - 2, y + 2), (x - l, y), (x - 2, y - 2)], fill=(255, 255, 255, 200))
    img.alpha_composite(g.filter(ImageFilter.GaussianBlur(0.5)))


def _clouds(col, seed, scale, alpha, cut, mask):
    """Awan nebula dari fractal noise."""
    rs = np.random.RandomState(seed)
    n = np.zeros((H, W), float)
    amp, tot = 1.0, 0.0
    for k in range(5):
        h, w = max(2, int(H / scale * 2 ** k)), max(2, int(W / scale * 2 ** k))
        a = Image.fromarray((rs.rand(h, w) * 255).astype("uint8")).resize((W, H), Image.BICUBIC)
        n += np.asarray(a, float) * amp
        tot += amp
        amp *= 0.5
    n = np.clip((n / tot / 255 - cut) / (1 - cut), 0, 1) ** 1.3
    n = n * np.asarray(mask, float) / 255
    layer = Image.new("RGBA", (W, H), (*col, 0))
    layer.putalpha(Image.fromarray((n * alpha).astype("uint8")))
    return layer


def _radial(cx, cy, rx, ry):
    y, x = np.mgrid[0:H, 0:W]
    v = np.clip(1 - np.sqrt(((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2), 0, 1)
    return Image.fromarray((v * 255).astype("uint8"))


def _gtext(img, xy, text, font, top, bot, glow, blur=16, anchor="lm"):
    m = Image.new("L", img.size, 0)
    ImageDraw.Draw(m).text(xy, text, font=font, fill=255, anchor=anchor)
    bb = m.getbbox()
    if not bb:
        return
    g = Image.new("RGBA", img.size, (0, 0, 0, 0))
    g.paste((*glow, 255), mask=m)
    img.alpha_composite(g.filter(ImageFilter.GaussianBlur(blur)))
    ramp = Image.new("L", (1, 256))
    ramp.putdata(list(range(256)))
    ramp = ramp.resize((img.width, max(1, bb[3] - bb[1])), Image.BILINEAR)
    col = ImageOps.colorize(ramp, black=top, white=bot).convert("RGBA")
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    layer.paste(col, (0, bb[1]))
    layer.putalpha(m)
    img.alpha_composite(layer)


def _chip(img, x, y, text, font, col, fill_a=60, pad=16, h=38):
    d = ImageDraw.Draw(img)
    w = int(d.textlength(text, font=font) + pad * 2)
    lay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(lay).rounded_rectangle(
        (x, y, x + w, y + h), radius=h // 2, fill=(*col, fill_a), outline=(*col, 200), width=2
    )
    img.alpha_composite(lay)
    ImageDraw.Draw(img).text((x + pad, y + h / 2 + 1), text, font=font, fill=(245, 238, 255, 255), anchor="lm")
    return w


def _circle(img: Image.Image, size: int) -> Image.Image:
    ss = 3
    img = img.convert("RGBA").resize((size, size), Image.LANCZOS)
    m = Image.new("L", (size * ss, size * ss), 0)
    ImageDraw.Draw(m).ellipse((0, 0, size * ss - 1, size * ss - 1), fill=255)
    img.putalpha(m.resize((size, size), Image.LANCZOS))
    return img


def _placeholder_avatar(size: int) -> Image.Image:
    a = Image.new("RGBA", (size, size), (120, 90, 220, 255))
    dr = ImageDraw.Draw(a)
    dr.ellipse((size * .33, size * .2, size * .67, size * .55), fill=(238, 228, 255, 255))
    dr.ellipse((size * .18, size * .58, size * .82, size * 1.2), fill=(238, 228, 255, 255))
    return a


# ══════════════════════════════════════════════════════════════════════════════
#  BAGIAN KARTU YANG TETAP (dibuat sekali, di-cache)
# ══════════════════════════════════════════════════════════════════════════════
def _build_static(logo: Image.Image, kind: str) -> Image.Image:
    t = THEMES[kind]
    acc, acc2, glow = t["acc"], t["acc2"], t["glow"]
    n1, n2 = t["neb"]
    ss = 3

    bg = Image.new("RGBA", (W, H), (4, 2, 14, 255))
    bg.alpha_composite(_clouds(n1, 11 if kind == "welcome" else 5, 260, 255, .36, _radial(300, 120, 900, 520)))
    bg.alpha_composite(_clouds(n2, 23, 300, 235, .38, _radial(1050, 520, 800, 480)))
    bg.alpha_composite(_clouds(acc, 41, 160, 110, .50, _radial(640, 300, 700, 420)))

    # sinar dari atas
    rays = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    rd = ImageDraw.Draw(rays)
    for i, a_ in enumerate([-520, -330, -170, -40, 40, 170, 330, 520]):
        w = 22 + (i % 3) * 14
        rd.polygon([(CX - 4, -20), (CX + 4, -20), (CX + a_ + w, H), (CX + a_ - w, H)],
                   fill=(*acc2, 13 + (i % 2) * 7))
    bg.alpha_composite(rays.filter(ImageFilter.GaussianBlur(6)))

    # logo raksasa
    wm = _lg(logo, 1000)
    if kind == "leave":  # geser ke magenta
        r_, g_, b_, a_ = wm.split()
        r_ = ImageChops.add(r_, r_.point(lambda v: int(v * .5)))
        b_ = b_.point(lambda v: int(v * .8))
        wm = Image.merge("RGBA", (r_, g_, b_, a_))
    pos = (CX - wm.width // 2, CY - wm.height // 2 + 95)
    big = wm.copy()
    big.putalpha(wm.getchannel("A").point(lambda v: int(v * .5)))
    bg.alpha_composite(big.filter(ImageFilter.GaussianBlur(28)), pos)
    wm.putalpha(wm.getchannel("A").point(lambda v: int(v * .22)))
    bg.alpha_composite(wm.filter(ImageFilter.GaussianBlur(1)), pos)

    _stars(bg, 170, (225, 210, 255), t["seed"])

    # horizon planet
    pc, pr = (640, 1610), 900
    pl = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(pl).ellipse((pc[0] - pr - 14, pc[1] - pr - 14, pc[0] + pr + 14, pc[1] + pr + 14), fill=(*acc, 170))
    bg.alpha_composite(pl.filter(ImageFilter.GaussianBlur(22)))
    pl = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    pd = ImageDraw.Draw(pl)
    pd.ellipse((pc[0] - pr - 3, pc[1] - pr - 3, pc[0] + pr + 3, pc[1] + pr + 3), fill=(*acc2, 255))
    pd.ellipse((pc[0] - pr, pc[1] - pr + 3, pc[0] + pr, pc[1] + pr + 3), fill=(5, 3, 16, 255))
    bg.alpha_composite(pl)

    # bintang jatuh
    for sx, sy, L in [(120, 90, 200), (930, 60, 170)]:
        sm = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        sd = ImageDraw.Draw(sm)
        for i in range(L):
            k = i / L
            sd.ellipse((sx + i * 1.9 - 2, sy + i * .62 - 1, sx + i * 1.9 + 2, sy + i * .62 + 1),
                       fill=(255, 255, 255, int(230 * k ** 2)))
        bg.alpha_composite(sm.filter(ImageFilter.GaussianBlur(0.8)))

    # partikel debu
    r = random.Random(9)
    pt = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    pd = ImageDraw.Draw(pt)
    for _ in range(36):
        x, y, s = r.randint(0, W), r.randint(0, H), r.choice([2, 3, 4])
        pd.ellipse((x - s, y - s, x + s, y + s), fill=(*r.choice([acc, acc2, (255, 255, 255)]), r.randint(90, 200)))
    bg.alpha_composite(pt.filter(ImageFilter.GaussianBlur(1.6)))

    # vignette
    vg = _radial(W / 2, H / 2, W * .75, H * .95).point(lambda v: 255 - min(255, int(v * 1.6)))
    v2 = Image.new("RGBA", (W, H), (3, 1, 10, 0))
    v2.putalpha(vg.point(lambda v: int(v * .5)))
    bg.alpha_composite(v2)

    # garis cahaya horizontal
    st_ = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    sd_ = ImageDraw.Draw(st_)
    for x in range(120, W - 120):
        a = int(230 * max(0, 1 - abs(x - CX) / (W / 2 - 120)) ** 2)
        sd_.line([(x, CY), (x, CY + 1)], fill=(*acc2, a))
    bg.alpha_composite(st_.filter(ImageFilter.GaussianBlur(6)))
    bg.alpha_composite(st_)

    # panel kaca kiri & kanan
    def glass(box):
        x0, y0, x1, y1 = box
        c = bg.crop(box).filter(ImageFilter.GaussianBlur(16))
        c = Image.alpha_composite(c, Image.new("RGBA", c.size, (8, 4, 26, 125)))
        m = Image.new("L", c.size, 0)
        ImageDraw.Draw(m).rounded_rectangle((0, 0, c.width - 1, c.height - 1), radius=22, fill=255)
        bg.paste(c, (x0, y0), m)
        ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        od_ = ImageDraw.Draw(ov)
        od_.rounded_rectangle(box, radius=22, outline=(*acc, 120), width=2)
        for x in range(x0 + 22, x1 - 22):
            od_.point((x, y0 + 1), fill=(255, 255, 255, int(150 * (1 - abs(x - (x0 + x1) / 2) / ((x1 - x0) / 2)))))
        for k in range(4):
            od_.line([(x0 + 22, y0 + 3 + k), (x1 - 22, y0 + 3 + k)], fill=(255, 255, 255, max(0, 14 - k * 4)))
        bg.alpha_composite(ov)

    glass((64, CY - 88, 372, CY + 112))
    glass((908, CY - 88, 1216, CY + 112))

    # glow di belakang avatar
    _blob(bg, (CX, CY), D // 2 + 25, glow, 255, 50)

    # ring orbit
    R = D // 2 + 30
    o = Image.new("RGBA", (2 * R * ss, 2 * R * ss), (0, 0, 0, 0))
    od = ImageDraw.Draw(o)
    box = (0, 0, 2 * R * ss - 1, 2 * R * ss - 1)
    od.ellipse(box, outline=(*acc, 150), width=2 * ss)
    od.arc(box, 200, 320, fill=(*acc2, 255), width=5 * ss)
    od.arc(box, 20, 70, fill=(255, 255, 255, 255), width=5 * ss)
    bg.alpha_composite(o.resize((2 * R, 2 * R), Image.LANCZOS), (CX - R, CY - R))

    # ring putus-putus
    R3 = D // 2 + 62
    o = Image.new("RGBA", (2 * R3 * ss, 2 * R3 * ss), (0, 0, 0, 0))
    od = ImageDraw.Draw(o)
    for k in range(0, 360, 6):
        od.arc((0, 0, 2 * R3 * ss - 1, 2 * R3 * ss - 1), k, k + 2, fill=(*acc, 120), width=2 * ss)
    bg.alpha_composite(o.resize((2 * R3, 2 * R3), Image.LANCZOS), (CX - R3, CY - R3))

    # tick kompas
    d = ImageDraw.Draw(bg)
    R4 = D // 2 + 84
    for k in range(0, 360, 5):
        L = 12 if k % 30 == 0 else 5
        c, s_ = math.cos(math.radians(k)), math.sin(math.radians(k))
        d.line([(CX + R4 * c, CY + R4 * s_), (CX + (R4 + L) * c, CY + (R4 + L) * s_)],
               fill=(*acc, 180 if k % 30 == 0 else 80), width=2 if k % 30 == 0 else 1)

    # titik planet
    for ang, r_, c in [(-35, R3, acc2), (150, R3, (255, 255, 255)), (65, R, acc), (-110, R, acc2), (215, R3, acc)]:
        px, py = CX + r_ * math.cos(math.radians(ang)), CY + r_ * math.sin(math.radians(ang))
        _blob(bg, (px, py), 9, c, 255, 6)
        ImageDraw.Draw(bg).ellipse((px - 5, py - 5, px + 5, py + 5), fill=(255, 255, 255, 255))

    # ring gradien (conic)
    R2 = D // 2 + 10
    N = 2 * R2 * ss
    yy, xx = np.mgrid[0:N, 0:N]
    rr = np.hypot(xx - N / 2 + .5, yy - N / 2 + .5)
    an = (np.degrees(np.arctan2(yy - N / 2 + .5, xx - N / 2 + .5)) + 360) % 360 / 360
    stops, pos_ = [acc, acc2, (255, 255, 255), acc2, acc], [0, .3, .5, .75, 1]
    ch = [np.interp(an, pos_, [c[k] for c in stops]) for k in range(3)]
    ma = ((rr <= R2 * ss) & (rr >= (R2 - 8) * ss)).astype(float)
    ring = Image.fromarray(np.dstack(ch + [ma * 255]).astype("uint8"), "RGBA")
    bg.alpha_composite(ring.resize((2 * R2, 2 * R2), Image.LANCZOS), (CX - R2, CY - R2))

    # garis HUD penghubung panel
    d = ImageDraw.Draw(bg)

    def hud(x0, x1, y):
        n = abs(x1 - x0)
        for i in range(n):
            a = int(200 * (1 - i / n))
            x = x0 + i * (1 if x1 > x0 else -1)
            d.line([(x, y), (x, y + 1)], fill=(*acc, a))
        d.polygon([(x0, y - 5), (x0 + 5, y), (x0, y + 5), (x0 - 5, y)], fill=(255, 255, 255, 255))

    hud(CX - R4 - 26, CX - R4 - 26 - 52, CY)
    hud(CX + R4 + 26, CX + R4 + 26 + 52, CY)

    # teks panel (statis)
    lx, rx = 92, W - 92
    d.text((lx, CY - 62), t["side_label"], font=_font(FONT_REGULAR, 15), fill=(*acc2, 255), anchor="lm")
    sf, st = _fit(d, t["side_sub"], FONT_ITALIC, 15, 10, 248)
    d.text((lx, CY + 36), st, font=sf, fill=(185, 170, 225, 230), anchor="lm")
    for i in range(240):
        d.point((lx + i, CY + 72), fill=(*acc, int(160 * (1 - i / 240))))
    d.text((lx, CY + 92), "A S T R A L A N   •   A S T R A N S", font=_font(FONT_REGULAR, 10),
           fill=(*acc2, 220), anchor="lm")
    d.text((rx, CY - 62), "T A N G G A L", font=_font(FONT_REGULAR, 15), fill=(*acc2, 255), anchor="rm")
    cf = _font(FONT_REGULAR, 14)
    cw = int(d.textlength(t["status"], font=cf) + 32)
    _chip(bg, rx - cw, CY + 58, t["status"], cf, acc, 60)
    d = ImageDraw.Draw(bg)

    # label tengah dengan diamond
    lf = _font(FONT_REGULAR, 20)
    d.text((CX, 468), t["label"], font=lf, fill=(*acc2, 255), anchor="mm")
    tw = d.textlength(t["label"], font=lf) / 2
    for i in range(90):
        a = int(220 * (1 - i / 90))
        d.point((CX - tw - 22 - i, 468), fill=(*acc, a))
        d.point((CX + tw + 22 + i, 468), fill=(*acc, a))
    for sx_ in (-1, 1):
        d.polygon([(CX + sx_ * (tw + 14), 463), (CX + sx_ * (tw + 19), 468),
                   (CX + sx_ * (tw + 14), 473), (CX + sx_ * (tw + 9), 468)], fill=(255, 255, 255, 255))

    # garis di bawah nama, sub teks, pesan footer
    for i in range(300):
        a = int(230 * (1 - i / 300))
        d.line([(CX - i, 588), (CX - i, 589)], fill=(*acc, a))
        d.line([(CX + i, 588), (CX + i, 589)], fill=(*acc, a))
    d.ellipse((CX - 5, 585, CX + 5, 595), fill=(255, 255, 255, 255))
    sub_f, sub_t = _fit(d, t["sub"], FONT_ITALIC, 22, 14, 900)
    d.text((CX, 622), sub_t, font=sub_f, fill=(215, 200, 245, 245), anchor="mm")
    ft_f, ft_t = _fit(d, t["footer_msg"], FONT_REGULAR, 15, 10, 1000)
    d.text((CX, 666), ft_t, font=ft_f, fill=(*acc, 255), anchor="mm")

    # brand pojok kiri atas
    ic = _lg(logo, 50)
    _blob(bg, (85, 58), 24, glow, 150, 10)
    bg.alpha_composite(ic, (60, 58 - ic.height // 2))
    d = ImageDraw.Draw(bg)
    d.text((124, 50), "A S T R A L A N", font=_font(FONT_BOLD, 16), fill=(235, 225, 255, 255), anchor="lm")
    d.text((124, 72), "Komunitas Astrans", font=_font(FONT_REGULAR, 11), fill=(170, 150, 215, 255), anchor="lm")

    # frame
    for x, y, sx, sy in [(24, 24, 1, 1), (W - 24, 24, -1, 1), (24, H - 24, 1, -1), (W - 24, H - 24, -1, -1)]:
        d.line([(x, y), (x + sx * 34, y)], fill=(*acc, 200), width=3)
        d.line([(x, y), (x, y + sy * 34)], fill=(*acc, 200), width=3)
    for x in range(W):
        a = int(210 * (1 - abs(x / W - .5) * 1.8))
        if a > 0:
            for yy_ in (0, 1, H - 1, H - 2):
                d.point((x, yy_), fill=(*acc, a))
    d.rounded_rectangle((14, 14, W - 15, H - 15), radius=6, outline=(*acc, 55), width=1)

    # grain halus
    rgb = np.asarray(bg.convert("RGB"), np.int16)
    gn = np.random.RandomState(1).normal(0, 3.2, (H, W, 1))
    return Image.fromarray(np.clip(rgb + gn, 0, 255).astype("uint8")).convert("RGBA")


# ══════════════════════════════════════════════════════════════════════════════
#  BAGIAN KARTU YANG BERUBAH PER MEMBER
# ══════════════════════════════════════════════════════════════════════════════
def render_card(static: Image.Image, kind: str, name: str,
                avatar_bytes: Optional[bytes], count: int, when: datetime) -> Image.Image:
    t = THEMES[kind]
    acc, glow = t["acc"], t["glow"]
    bg = static.copy()

    # avatar
    try:
        av = _circle(Image.open(BytesIO(avatar_bytes)), D) if avatar_bytes else _circle(_placeholder_avatar(D), D)
    except Exception:
        av = _circle(_placeholder_avatar(D), D)
    if kind == "leave":  # avatar dibuat redup
        alpha = av.getchannel("A")
        gray = ImageOps.grayscale(av.convert("RGB")).convert("RGBA")
        av = Image.blend(gray, Image.new("RGBA", (D, D), (130, 60, 180, 255)), 0.35)
        av.putalpha(alpha)
    bg.alpha_composite(av, (CX - D // 2, CY - D // 2))

    # badge +/-
    bx, by = CX + D // 2 - 14, CY + D // 2 - 14
    d = ImageDraw.Draw(bg)
    d.ellipse((bx - 24, by - 24, bx + 24, by + 24), fill=(10, 6, 30, 255), outline=(*acc, 255), width=3)
    d.line([(bx - 9, by), (bx + 9, by)], fill=(255, 255, 255), width=4)
    if t["badge"] == "+":
        d.line([(bx, by - 9), (bx, by + 9)], fill=(255, 255, 255), width=4)

    # panel kiri: nomor member
    lx, rx = 92, W - 92
    num = f"#{count}" if kind == "welcome" else f"{count}"
    nf, nt = _fit(d, num, FONT_BOLD, 60, 28, 248)
    _gtext(bg, (lx, CY - 14), nt, nf, (255, 255, 255), acc, glow, 12)

    # panel kanan: tanggal + jam WIB
    d = ImageDraw.Draw(bg)
    df, dt = _fit(d, f"{when.day:02d} {MONTHS[when.month - 1]}", FONT_BOLD, 44, 24, 248)
    d.text((rx, CY - 14), dt, font=df, fill=(255, 255, 255, 255), anchor="rm")
    tf, tt = _fit(d, f"{when.year}  •  {when:%H:%M} WIB", FONT_REGULAR, 16, 10, 248)
    d.text((rx, CY + 30), tt, font=tf, fill=(205, 190, 240, 240), anchor="rm")

    # nama (otomatis mengecil kalau panjang)
    name_font, name_text = _fit(d, name, FONT_BOLD, 70, 28, 860)
    nw = d.textlength(name_text, font=name_font)
    _gtext(bg, (CX - nw / 2, 534), name_text, name_font, t["name_grad"][0], t["name_grad"][1], glow, 16)
    return bg.convert("RGB")


# ══════════════════════════════════════════════════════════════════════════════
#  COG
# ══════════════════════════════════════════════════════════════════════════════
class Welcome(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.static: dict = {}

    def _build_all(self):
        logo = _prep_logo(BG_PATH)
        return {k: _build_static(logo, k) for k in THEMES}

    async def cog_load(self):
        # bangun cache di thread terpisah supaya bot tidak nge-freeze saat start
        loop = asyncio.get_running_loop()
        self.static = await loop.run_in_executor(None, self._build_all)

    # ── bikin + kirim notif ──────────────────────────────────────────────────
    async def send_notification(self, member: discord.Member, kind: str, count: Optional[int] = None):
        guild = member.guild
        channel_id = WELCOME_CHANNEL_ID if kind == "welcome" else LEAVE_CHANNEL_ID
        channel = guild.get_channel(channel_id)
        if channel is None:
            raise RuntimeError(f"Channel {channel_id} tidak ditemukan di server ini.")

        loop = asyncio.get_running_loop()
        if not self.static:
            self.static = await loop.run_in_executor(None, self._build_all)

        if count is None:
            count = guild.member_count or 0
        when = datetime.now(timezone(timedelta(hours=UTC_OFFSET)))

        try:
            avatar_bytes = await member.display_avatar.replace(size=512, format="png").read()
        except Exception:
            avatar_bytes = None

        card = await loop.run_in_executor(
            None,
            partial(render_card, self.static[kind], kind, member.display_name, avatar_bytes, count, when),
        )
        buf = BytesIO()
        card.save(buf, format="PNG")
        buf.seek(0)

        t = THEMES[kind]
        if kind == "welcome":
            desc = f"Selamat datang {member.mention} di **{SERVER_NAME}**"
        else:
            desc = f"**{member.display_name}** telah meninggalkan **{SERVER_NAME}**"
        embed = discord.Embed(description=desc, color=t["embed_color"], timestamp=when)
        embed.set_image(url=f"attachment://{t['filename']}")
        embed.set_footer(
            text=f"{SERVER_NAME} • {'Member' if kind == 'welcome' else 'Sisa member'} {count}",
            icon_url=guild.icon.url if guild.icon else None,
        )
        await channel.send(embed=embed, file=discord.File(buf, filename=t["filename"]))
        return channel

    # ── event asli ───────────────────────────────────────────────────────────
    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        if SKIP_BOTS and member.bot:
            return
        print(f"[WELCOME] {member} join: {member.guild.name}")
        try:
            await self.send_notification(member, "welcome")
        except Exception as e:
            print(f"[WELCOME] Error: {e}")

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        if SKIP_BOTS and member.bot:
            return
        print(f"[LEAVE] {member} keluar: {member.guild.name}")
        try:
            await self.send_notification(member, "leave")
        except Exception as e:
            print(f"[LEAVE] Error: {e}")

    # ── command tes (khusus admin) ───────────────────────────────────────────
    async def _run_test(self, ctx: commands.Context, member: discord.Member, kind: str):
        async with ctx.typing():
            try:
                count = ctx.guild.member_count or 0
                if kind == "leave":
                    count = max(count - 1, 0)  # simulasi: sisa member setelah keluar
                channel = await self.send_notification(member, kind, count=count)
            except Exception as e:
                await ctx.send(f"❌ Tes **{kind}** gagal: `{type(e).__name__}: {e}`")
                return
        await ctx.send(f"✅ Tes **{kind}** terkirim ke {channel.mention} (pakai data {member.display_name}).")

    @commands.hybrid_command(name="astwelcome", description="Tes kartu welcome (admin)")
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def astwelcome(self, ctx: commands.Context, member: Optional[discord.Member] = None):
        await self._run_test(ctx, member or ctx.author, "welcome")

    @commands.hybrid_command(name="astleave", description="Tes kartu leave (admin)")
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def astleave(self, ctx: commands.Context, member: Optional[discord.Member] = None):
        await self._run_test(ctx, member or ctx.author, "leave")

    async def cog_command_error(self, ctx: commands.Context, error: Exception):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("❌ Command ini khusus admin.")
        elif isinstance(error, commands.NoPrivateMessage):
            await ctx.send("❌ Command ini hanya bisa dipakai di server.")
        else:
            raise error


async def setup(bot):
    await bot.add_cog(Welcome(bot))