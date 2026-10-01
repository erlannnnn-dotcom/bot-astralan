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
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

# ══════════════════════════════════════════════════════════════════════════════
#  KONFIGURASI  (ubah bagian ini saja)
# ══════════════════════════════════════════════════════════════════════════════
WELCOME_CHANNEL_ID = 1494993934315946079   # channel tempat welcome dikirim
RULES_CHANNEL_ID   = 1496857934339244163   # channel tata-tertib
ROLE_CHANNEL_ID    = 1496857983735435486   # channel atribut / pilih role
VOICE_GIRL_ID      = 1539846749475049483   # voice untuk verif girl

ARROW_EMOJI      = "<a:arrow:1555096801629970523>"       # emoji animasi panah
VERIF_GIRL_EMOJI = "<a:verifgirl:1555094789962334260>"   # emoji animasi verif girl
GREETING_EMOJI   = ""                                    # emoji di baris sapaan (kosong = polos)

SERVER_NAME = "Astralan"
SKIP_BOTS   = True                          # True = akun bot tidak dikirimi welcome
UTC_OFFSET  = 7                             # WIB = UTC+7
TEST_COMMAND = "asttestwelcome"             # ketik ini (tanpa prefix) untuk tes, khusus admin

BG_PATH      = "welcome_bg.png"             # logo Astralan (PNG transparan)
FONT_BOLD    = "fonts/LEMONMILK-Bold.otf"
FONT_REGULAR = "fonts/LEMONMILK-Regular.otf"
FONT_ITALIC  = "fonts/LEMONMILK-RegularItalic.otf"

# Teks di dalam gambar
CARD_LABEL   = "—  W E L C O M E   T O   A S T R A L A N"
CARD_SUB     = "Astrans baru telah bergabung"
CARD_FOOTER  = "Selamat bergabung dan semoga betah di Server"
CARD_STATUS  = "• JOINED"

W, H = 1280, 720                            # ukuran gambar 16:9
HX, HY, HR = 290, 372, 168                  # pusat & radius avatar hexagon

ACC   = (150, 120, 255)                     # warna aksen utama (ungu)
ACC2  = (90, 190, 255)                      # warna aksen kedua (biru)
GLOW  = (110, 70, 255)                      # warna glow
NEB1  = (90, 50, 220)                       # warna nebula 1
NEB2  = (40, 110, 230)                      # warna nebula 2
NAME_GRAD = ((255, 255, 255), (200, 170, 255))

MONTHS = ["JAN", "FEB", "MAR", "APR", "MEI", "JUN", "JUL", "AGU", "SEP", "OKT", "NOV", "DES"]


# ══════════════════════════════════════════════════════════════════════════════
#  HELPER GAMBAR
# ══════════════════════════════════════════════════════════════════════════════
@lru_cache(maxsize=64)
def _font(path: str, size: int):
    """Load font; kalau file tidak ada pakai font bawaan Pillow."""
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
    """Buka logo transparan lalu crop bagian yang kosong."""
    logo = Image.open(path).convert("RGBA")
    bbox = logo.getchannel("A").getbbox()
    return logo.crop(bbox) if bbox else logo


def _lg(logo: Image.Image, w: int) -> Image.Image:
    """Resize logo ke lebar w (rasio tetap)."""
    return logo.resize((w, int(logo.height * w / logo.width)), Image.LANCZOS)


def _blob(img, xy, r, col, a, blur):
    """Lingkaran cahaya blur (dipakai untuk glow)."""
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    x, y = xy
    ImageDraw.Draw(layer).ellipse((x - r, y - r, x + r, y + r), fill=(*col, a))
    img.alpha_composite(layer.filter(ImageFilter.GaussianBlur(blur)))


def _stars(img, n, seed):
    """Bintang kecil + beberapa sparkle 4 arah."""
    rnd = random.Random(seed)
    g = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(g)
    for _ in range(n):
        x, y = rnd.randint(0, W), rnd.randint(0, H - 80)
        s = rnd.choice([1, 1, 1, 2, 2, 3])
        d.ellipse((x - s, y - s, x + s, y + s), fill=(225, 210, 255, rnd.randint(80, 230)))
    img.alpha_composite(g.filter(ImageFilter.GaussianBlur(0.6)))
    g = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(g)
    for _ in range(4):
        x, y = rnd.randint(40, W - 40), rnd.randint(25, H - 60)
        l = rnd.randint(10, 20)
        if x < 300 and y < 120:  # jangan menimpa logo di pojok kiri atas
            x += 300
        d.polygon([(x, y - l), (x + 2, y - 2), (x + l, y), (x + 2, y + 2),
                   (x, y + l), (x - 2, y + 2), (x - l, y), (x - 2, y - 2)], fill=(255, 255, 255, 200))
    img.alpha_composite(g.filter(ImageFilter.GaussianBlur(0.5)))


def _radial(cx, cy, rx, ry):
    """Mask gradasi radial (terang di tengah, gelap di tepi)."""
    y, x = np.mgrid[0:H, 0:W]
    v = np.clip(1 - np.sqrt(((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2), 0, 1)
    return Image.fromarray((v * 255).astype("uint8"))


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


def _gtext(img, xy, text, font, top, bot, glow, blur=16, anchor="lm"):
    """Teks dengan gradasi vertikal + glow."""
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
    """Label kapsul (rounded)."""
    d = ImageDraw.Draw(img)
    w = int(d.textlength(text, font=font) + pad * 2)
    lay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(lay).rounded_rectangle(
        (x, y, x + w, y + h), radius=h // 2, fill=(*col, fill_a), outline=(*col, 200), width=2
    )
    img.alpha_composite(lay)
    ImageDraw.Draw(img).text((x + pad, y + h / 2 + 1), text, font=font, fill=(245, 238, 255, 255), anchor="lm")
    return w


def _hex(cx, cy, r, rot=-90):
    """Titik sudut hexagon (ujung runcing di atas)."""
    return [(cx + r * math.cos(math.radians(rot + 60 * i)),
             cy + r * math.sin(math.radians(rot + 60 * i))) for i in range(6)]


def _placeholder_avatar(size: int) -> Image.Image:
    """Avatar cadangan kalau foto profil gagal diambil."""
    a = Image.new("RGBA", (size, size), (120, 90, 220, 255))
    dr = ImageDraw.Draw(a)
    dr.ellipse((size * .33, size * .2, size * .67, size * .55), fill=(238, 228, 255, 255))
    dr.ellipse((size * .18, size * .58, size * .82, size * 1.2), fill=(238, 228, 255, 255))
    return a


# ══════════════════════════════════════════════════════════════════════════════
#  BAGIAN KARTU YANG TETAP (dibuat sekali saja, lalu di-cache)
# ══════════════════════════════════════════════════════════════════════════════
def _build_static(logo: Image.Image):
    """Return (base, overlay).
    base    = background, logo, garis, hexagon (di bawah avatar & angka ghost)
    overlay = brand, teks tetap, frame (di atas avatar)"""
    ss = 3
    bg = Image.new("RGBA", (W, H), (4, 2, 14, 255))

    # nebula (awan warna)
    bg.alpha_composite(_clouds(NEB1, 11, 260, 255, .36, _radial(250, 300, 800, 560)))
    bg.alpha_composite(_clouds(NEB2, 23, 300, 200, .38, _radial(1100, 620, 700, 420)))
    bg.alpha_composite(_clouds(ACC, 41, 160, 100, .50, _radial(300, 380, 600, 450)))

    # logo raksasa di belakang avatar (glow + versi tipis)
    wm = _lg(logo, 900)
    pos = (HX - wm.width // 2, HY - wm.height // 2 + 60)
    g = wm.copy()
    g.putalpha(wm.getchannel("A").point(lambda v: int(v * .55)))
    bg.alpha_composite(g.filter(ImageFilter.GaussianBlur(26)), pos)
    wm.putalpha(wm.getchannel("A").point(lambda v: int(v * .26)))
    bg.alpha_composite(wm.filter(ImageFilter.GaussianBlur(1)), pos)

    _stars(bg, 150, 7)

    # panel gelap diagonal di sisi kanan supaya teks terbaca
    dk = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(dk).polygon([(540, 0), (W, 0), (W, H), (440, H)], fill=(4, 2, 14, 175))
    bg.alpha_composite(dk.filter(ImageFilter.GaussianBlur(8)))

    # garis cahaya diagonal pemisah
    sl = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    sd = ImageDraw.Draw(sl)
    sd.line([(540, 0), (440, H)], fill=(*ACC2, 255), width=3)
    sd.line([(556, 0), (456, H)], fill=(*ACC, 120), width=1)
    sd.line([(526, 0), (426, H)], fill=(*ACC, 70), width=1)
    bg.alpha_composite(sl.filter(ImageFilter.GaussianBlur(7)))
    bg.alpha_composite(sl)

    # bintang jatuh
    for sx, sy, L in [(620, 70, 170), (80, 520, 150)]:
        sm = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        smd = ImageDraw.Draw(sm)
        for i in range(L):
            k = i / L
            smd.ellipse((sx + i * 1.9 - 2, sy + i * .62 - 1, sx + i * 1.9 + 2, sy + i * .62 + 1),
                        fill=(255, 255, 255, int(220 * k ** 2)))
        bg.alpha_composite(sm.filter(ImageFilter.GaussianBlur(0.8)))

    # glow di belakang hexagon
    _blob(bg, (HX, HY), HR, GLOW, 255, 55)

    # border hexagon berlapis
    RB = HR + 46
    lay = Image.new("RGBA", (2 * RB * ss, 2 * RB * ss), (0, 0, 0, 0))
    ld = ImageDraw.Draw(lay)

    def poly(r, col, wd):
        pts = [((x - HX + RB) * ss, (y - HY + RB) * ss) for x, y in _hex(HX, HY, r)]
        ld.line(pts + [pts[0]], fill=col, width=wd * ss, joint="curve")

    poly(HR + 34, (*ACC, 70), 2)
    poly(HR + 20, (*ACC2, 110), 2)
    poly(HR + 7, (*ACC, 255), 8)
    pts = _hex(HX, HY, HR + 7)
    for a, b, c, wd in [(0, 1, ACC2, 8), (1, 2, (255, 255, 255), 4), (3, 4, ACC2, 8)]:  # sisi bercahaya
        ld.line([((pts[a][0] - HX + RB) * ss, (pts[a][1] - HY + RB) * ss),
                 ((pts[b][0] - HX + RB) * ss, (pts[b][1] - HY + RB) * ss)], fill=(*c, 255), width=wd * ss)
    bg.alpha_composite(lay.resize((2 * RB, 2 * RB), Image.LANCZOS), (HX - RB, HY - RB))

    # titik bersinar di tiap sudut hexagon luar
    for i, (x, y) in enumerate(_hex(HX, HY, HR + 34)):
        _blob(bg, (x, y), 8, ACC2 if i % 2 else (255, 255, 255), 255, 5)
        ImageDraw.Draw(bg).ellipse((x - 4, y - 4, x + 4, y + 4), fill=(255, 255, 255, 255))

    # ── overlay (di atas avatar & angka ghost) ───────────────────────────────
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    X = 600

    # label atas, garis pemisah, sub teks
    d.text((X, 128), CARD_LABEL, font=_font(FONT_REGULAR, 17), fill=(*ACC2, 255), anchor="lm")
    for i in range(520):
        d.line([(X + i, 276), (X + i, 277)], fill=(*ACC, int(230 * (1 - i / 520))))
    d.ellipse((X - 5, 272, X + 5, 282), fill=(255, 255, 255, 255))
    sf, st = _fit(d, CARD_SUB, FONT_ITALIC, 25, 14, 600)
    d.text((X, 320), st, font=sf, fill=(215, 200, 245, 245), anchor="lm")

    # label kolom info + garis pembatas
    for i, (x, lb) in enumerate([(X, "M E M B E R"), (830, "T A N G G A L"), (1040, "W A K T U")]):
        d.text((x, 420), lb, font=_font(FONT_REGULAR, 14), fill=(*ACC2, 255), anchor="lm")
        if i:
            for k in range(70):
                d.point((x - 30, 415 + k), fill=(*ACC, int(200 * (1 - abs(k - 35) / 35))))

    # chip status + pesan bawah
    cf = _font(FONT_REGULAR, 14)
    cw = _chip(ov, X, 566, CARD_STATUS, cf, ACC, 60)
    d = ImageDraw.Draw(ov)
    ff, ft = _fit(d, CARD_FOOTER, FONT_ITALIC, 15, 10, 1230 - (X + cw + 24))
    d.text((X + cw + 24, 586), ft, font=ff, fill=(*ACC, 255), anchor="lm")

    # brand pojok kiri atas
    ic = _lg(logo, 50)
    _blob(ov, (85, 58), 24, GLOW, 150, 10)
    ov.alpha_composite(ic, (60, 58 - ic.height // 2))
    d = ImageDraw.Draw(ov)
    d.text((124, 50), "A S T R A L A N", font=_font(FONT_BOLD, 16), fill=(235, 225, 255, 255), anchor="lm")
    d.text((124, 72), "Komunitas Astrans", font=_font(FONT_REGULAR, 11), fill=(170, 150, 215, 255), anchor="lm")

    # teks vertikal di tepi kiri
    vt = Image.new("RGBA", (420, 30), (0, 0, 0, 0))
    ImageDraw.Draw(vt).text((210, 15), "A S T R A L A N   •   A S T R A N S   •   S E R V E R",
                            font=_font(FONT_REGULAR, 10), fill=(*ACC2, 150), anchor="mm")
    ov.alpha_composite(vt.rotate(90, expand=True), (38, H // 2 - 200))

    # frame sudut + garis aksen atas/bawah
    d = ImageDraw.Draw(ov)
    for x, y, sx, sy in [(24, 24, 1, 1), (W - 24, 24, -1, 1), (24, H - 24, 1, -1), (W - 24, H - 24, -1, -1)]:
        d.line([(x, y), (x + sx * 34, y)], fill=(*ACC, 200), width=3)
        d.line([(x, y), (x, y + sy * 34)], fill=(*ACC, 200), width=3)
    for x in range(W):
        a = int(210 * (1 - abs(x / W - .5) * 1.8))
        if a > 0:
            for yy in (0, 1, H - 1, H - 2):
                d.point((x, yy), fill=(*ACC, a))
    d.rounded_rectangle((14, 14, W - 15, H - 15), radius=6, outline=(*ACC, 55), width=1)
    return bg, ov


# ══════════════════════════════════════════════════════════════════════════════
#  BAGIAN KARTU YANG BERUBAH PER MEMBER
# ══════════════════════════════════════════════════════════════════════════════
def render_card(base: Image.Image, overlay: Image.Image, name: str,
                avatar_bytes: Optional[bytes], count: int, when: datetime) -> Image.Image:
    ss = 3
    bg = base.copy()

    # angka member raksasa (outline samar) di belakang teks
    gsize = 340 if len(str(count)) <= 4 else 270
    gh = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(gh).text((W + 10, H + 40), str(count), font=_font(FONT_BOLD, gsize),
                            fill=(0, 0, 0, 0), stroke_width=2, stroke_fill=(*ACC, 70), anchor="rs")
    bg.alpha_composite(gh)

    # avatar berbentuk hexagon
    size = 2 * HR
    try:
        av = Image.open(BytesIO(avatar_bytes)).convert("RGBA") if avatar_bytes else _placeholder_avatar(size)
    except Exception:
        av = _placeholder_avatar(size)
    av = ImageOps.fit(av, (size, size), Image.LANCZOS)
    m = Image.new("L", (size * ss, size * ss), 0)
    ImageDraw.Draw(m).polygon([((x - HX + HR) * ss, (y - HY + HR) * ss) for x, y in _hex(HX, HY, HR - 2)], fill=255)
    av.putalpha(m.resize((size, size), Image.LANCZOS))
    bg.alpha_composite(av, (HX - HR, HY - HR))

    # brand, teks tetap, frame
    bg.alpha_composite(overlay)

    # badge "+" di sudut kanan bawah hexagon
    bx, by = _hex(HX, HY, HR + 7)[2]
    d = ImageDraw.Draw(bg)
    d.ellipse((bx - 26, by - 26, bx + 26, by + 26), fill=(10, 6, 30, 255), outline=(*ACC, 255), width=3)
    d.line([(bx - 10, by), (bx + 10, by)], fill=(255, 255, 255), width=4)
    d.line([(bx, by - 10), (bx, by + 10)], fill=(255, 255, 255), width=4)

    # nama (otomatis mengecil kalau panjang)
    X = 600
    nf, nt = _fit(d, name, FONT_BOLD, 88, 34, 620)
    _gtext(bg, (X, 214), nt, nf, NAME_GRAD[0], NAME_GRAD[1], GLOW, 18)

    # tiga kolom info: member, tanggal, waktu (WIB)
    d = ImageDraw.Draw(bg)
    cols = [
        (X,    f"#{count}",                                  "Anggota baru Server", 170),
        (830,  f"{when.day:02d} {MONTHS[when.month - 1]}",   f"{when.year}",        170),
        (1040, f"{when:%H:%M}",                              "WIB  •  UTC+7",       180),
    ]
    for x, val, sub, mw in cols:
        vf, vt = _fit(d, val, FONT_BOLD, 44, 22, mw)
        _gtext(bg, (x, 466), vt, vf, (255, 255, 255), ACC, GLOW, 10)
        d = ImageDraw.Draw(bg)
        sf, st = _fit(d, sub, FONT_ITALIC, 14, 9, mw)
        d.text((x, 508), st, font=sf, fill=(185, 170, 225, 230), anchor="lm")

    # grain halus supaya terlihat premium
    rgb = np.asarray(bg.convert("RGB"), np.int16)
    gn = np.random.RandomState(1).normal(0, 3.2, (H, W, 1))
    return Image.fromarray(np.clip(rgb + gn, 0, 255).astype("uint8"))


# ══════════════════════════════════════════════════════════════════════════════
#  COG
# ══════════════════════════════════════════════════════════════════════════════
class Welcomee(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.static = None  # (base, overlay), dibuat saat cog di-load

    def _build_all(self):
        return _build_static(_prep_logo(BG_PATH))

    async def cog_load(self):
        # bangun background di thread terpisah supaya bot tidak nge-freeze saat start
        loop = asyncio.get_running_loop()
        self.static = await loop.run_in_executor(None, self._build_all)
        print("[WELCOME] Kartu siap dipakai.")

    # ── teks pesan di atas gambar ────────────────────────────────────────────
    def _message_text(self, member: discord.Member) -> str:
        greet = f"{GREETING_EMOJI} " if GREETING_EMOJI else ""
        return (
            f"{greet}**Selamat bergabung, Astrans baru!**\n"
            f"Selamat datang di **{SERVER_NAME}**, {member.mention}!\n"
            f"{ARROW_EMOJI} `Baca rules:` <#{RULES_CHANNEL_ID}>\n"
            f"{ARROW_EMOJI} `Pilih role:` <#{ROLE_CHANNEL_ID}>\n"
            f"{VERIF_GIRL_EMOJI} `Verif girl:` lalu masuk ke <#{VOICE_GIRL_ID}>"
        )

    # ── bikin gambar + kirim pesan (tanpa embed) ─────────────────────────────
    async def send_welcome(self, member: discord.Member, count: Optional[int] = None):
        guild = member.guild
        channel = guild.get_channel(WELCOME_CHANNEL_ID)
        if channel is None:
            raise RuntimeError(f"Channel {WELCOME_CHANNEL_ID} tidak ditemukan di server ini.")

        loop = asyncio.get_running_loop()
        if self.static is None:  # jaga-jaga kalau belum selesai dibangun
            self.static = await loop.run_in_executor(None, self._build_all)

        if count is None:
            count = guild.member_count or 0
        when = datetime.now(timezone(timedelta(hours=UTC_OFFSET)))  # waktu WIB

        # ambil foto profil
        try:
            avatar_bytes = await member.display_avatar.replace(size=512, format="png").read()
        except Exception:
            avatar_bytes = None

        # render gambar di thread terpisah
        card = await loop.run_in_executor(
            None,
            partial(render_card, self.static[0], self.static[1], member.display_name, avatar_bytes, count, when),
        )
        buf = BytesIO()
        card.save(buf, format="PNG")
        buf.seek(0)

        # teks + gambar sebagai attachment (di luar panel/embed)
        await channel.send(content=self._message_text(member), file=discord.File(buf, filename="welcome.png"))
        return channel

    # ── event asli: member baru masuk ────────────────────────────────────────
    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        if SKIP_BOTS and member.bot:
            return
        print(f"[WELCOME] {member} join: {member.guild.name}")
        try:
            await self.send_welcome(member)
        except Exception as e:
            print(f"[WELCOME] Error: {e}")

    # ── command tes: ketik "asttestwelcome" (tanpa prefix), khusus admin ─────
    # Boleh ditambah mention untuk tes pakai data member lain: asttestwelcome @nama
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or message.guild is None:
            return
        parts = message.content.strip().split()
        if not parts or parts[0].lower() != TEST_COMMAND:
            return
        if not message.author.guild_permissions.administrator:
            await message.channel.send("❌ Command ini khusus admin.")
            return

        member = message.mentions[0] if message.mentions else message.author
        async with message.channel.typing():
            try:
                target = await self.send_welcome(member)
            except Exception as e:
                await message.channel.send(f"❌ Tes welcome gagal: `{type(e).__name__}: {e}`")
                return
        await message.channel.send(
            f"✅ Tes welcome terkirim ke {target.mention} (pakai data {member.display_name})."
        )


async def setup(bot):
    await bot.add_cog(Welcomee(bot))