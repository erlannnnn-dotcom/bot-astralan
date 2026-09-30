import asyncio
import random
from datetime import datetime, timedelta, timezone
from functools import lru_cache, partial
from io import BytesIO
from typing import Optional

import discord
from discord.ext import commands
from PIL import Image, ImageChops, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageOps

# ══════════════════════════════════════════════════════════════════════════════
#  KONFIGURASI
# ══════════════════════════════════════════════════════════════════════════════
WELCOME_CHANNEL_ID = 1497149920006639718
LEAVE_CHANNEL_ID   = 1497151497983623320   # ganti kalau channel leave beda

SERVER_NAME = "Astralan"
SKIP_BOTS   = True                          # True = akun bot tidak dikirimi notif
UTC_OFFSET  = 8                             # WITA (Makassar) = UTC+8

BG_PATH      = "welcome_bg.png"             # gambar logo ungu (yang kamu kirim)
FONT_BOLD    = "fonts/LEMONMILK-Bold.otf"
FONT_REGULAR = "fonts/LEMONMILK-Regular.otf"
FONT_ITALIC  = "fonts/LEMONMILK-RegularItalic.otf"

# Logo di bg asli (dipakai untuk icon kecil di footer): (kiri, atas, kanan, bawah)
LOGO_CROP = (250, 300, 1010, 960)

W, H = 1200, 500

THEMES = {
    "welcome": dict(
        acc=(150, 120, 255), acc2=(90, 190, 255), glow=(110, 70, 255),
        tint=False, seed=7, badge="+",
        label="W E L C O M E",
        sub="Stardust baru telah bergabung",
        status="• JOINED",
        footer_msg="Semoga betah dan jangan lupa baca #rules",
        name_grad=((255, 255, 255), (200, 170, 255)),
        embed_color=0x9B45FF,
        filename="welcome.png",
    ),
    "leave": dict(
        acc=(214, 120, 255), acc2=(255, 120, 220), glow=(200, 70, 235),
        tint=True, seed=3, badge="-",
        label="G O O D B Y E",
        sub="Satu bintang telah meninggalkan galaksi",
        status="• LEFT",
        footer_msg="Sampai jumpa lagi, semoga bertemu di galaksi lain",
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


def _base_bg(src: Image.Image, tint: bool) -> Image.Image:
    S = 0.8
    im = src.resize((int(src.width * S), int(src.height * S)), Image.LANCZOS)
    ox, oy = 386, -271
    cv = Image.new("RGB", (W, H), (5, 3, 16))
    cv.paste(ImageOps.mirror(im), (ox - im.width, oy))
    cv.paste(im, (ox, oy))
    cv = ImageEnhance.Brightness(cv).enhance(0.78)
    if tint:  # geser ke magenta untuk kartu leave
        r, g, b = cv.split()
        r = ImageChops.add(r, r.point(lambda v: int(v * 0.55)))
        b = b.point(lambda v: int(v * 0.84))
        cv = Image.merge("RGB", (r, g, b))
    cv = cv.convert("RGBA")

    # gelapkan sisi kiri supaya teks terbaca
    ramp = Image.new("L", (256, 1))
    ramp.putdata(list(range(256)))
    ramp = ramp.resize((760, H), Image.BILINEAR)
    ramp = ramp.point(lambda v: int(235 * max(0.0, 1 - v / 255) ** 1.2 + 25))
    alpha = Image.new("L", (W, H), 25)
    alpha.paste(ramp, (0, 0))
    shade = Image.new("RGBA", (W, H), (4, 2, 14, 0))
    shade.putalpha(alpha)
    cv.alpha_composite(shade)
    return cv


def _stars(img, n, col, seed):
    rnd = random.Random(seed)
    g = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(g)
    for _ in range(n):
        x, y = rnd.randint(0, W), rnd.randint(0, H - 90)
        r = rnd.choice([1, 1, 1, 2, 2, 3])
        d.ellipse((x - r, y - r, x + r, y + r), fill=(*col, rnd.randint(90, 230)))
    for _ in range(9):
        x, y = rnd.randint(40, W - 40), rnd.randint(20, H - 110)
        l = rnd.randint(8, 16)
        d.line([(x - l, y), (x + l, y)], fill=(*col, 170), width=1)
        d.line([(x, y - l), (x, y + l)], fill=(*col, 170), width=1)
    img.alpha_composite(g.filter(ImageFilter.GaussianBlur(0.6)))


def _brackets(d, box, col, l=26, w=3):
    x0, y0, x1, y1 = box
    for x, y, sx, sy in [(x0, y0, 1, 1), (x1, y0, -1, 1), (x0, y1, 1, -1), (x1, y1, -1, -1)]:
        d.line([(x, y), (x + sx * l, y)], fill=col, width=w)
        d.line([(x, y), (x, y + sy * l)], fill=col, width=w)


def _grad_text(img, xy, text, font, top, bot, glow, blur=16, anchor="lm"):
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


def _circle(img: Image.Image, D: int) -> Image.Image:
    ss = 3
    img = img.convert("RGBA").resize((D, D), Image.LANCZOS)
    m = Image.new("L", (D * ss, D * ss), 0)
    ImageDraw.Draw(m).ellipse((0, 0, D * ss - 1, D * ss - 1), fill=255)
    img.putalpha(m.resize((D, D), Image.LANCZOS))
    return img


def _placeholder_avatar(D: int) -> Image.Image:
    a = Image.new("RGBA", (D, D), (120, 90, 220, 255))
    dr = ImageDraw.Draw(a)
    dr.ellipse((D * .33, D * .2, D * .67, D * .55), fill=(238, 228, 255, 255))
    dr.ellipse((D * .18, D * .58, D * .82, D * 1.2), fill=(238, 228, 255, 255))
    return a


# Pusat avatar & ukuran
AV_CX, AV_CY, AV_D = 905, 232, 230


def _build_static(src: Image.Image, kind: str) -> Image.Image:
    """Bagian kartu yang tidak berubah per member (di-cache, dibuat sekali saja)."""
    t = THEMES[kind]
    acc, acc2, glow = t["acc"], t["acc2"], t["glow"]
    bg = _base_bg(src, t["tint"])
    _stars(bg, 70, (225, 210, 255), t["seed"])

    cx, cy, D = AV_CX, AV_CY, AV_D
    ss = 3

    # glow di belakang avatar
    halo = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(halo).ellipse((cx - D // 2 - 20, cy - D // 2 - 20, cx + D // 2 + 20, cy + D // 2 + 20), fill=(*glow, 255))
    bg.alpha_composite(halo.filter(ImageFilter.GaussianBlur(40)))

    # ring orbit luar
    R = D // 2 + 30
    o = Image.new("RGBA", (2 * R * ss, 2 * R * ss), (0, 0, 0, 0))
    od = ImageDraw.Draw(o)
    box = (0, 0, 2 * R * ss - 1, 2 * R * ss - 1)
    od.ellipse(box, outline=(*acc, 150), width=2 * ss)
    od.arc(box, 200, 320, fill=(*acc2, 255), width=5 * ss)
    od.arc(box, 20, 70, fill=(255, 255, 255, 255), width=5 * ss)
    bg.alpha_composite(o.resize((2 * R, 2 * R), Image.LANCZOS), (cx - R, cy - R))

    # ring tebal dekat avatar
    R2 = D // 2 + 10
    ring = Image.new("RGBA", (2 * R2 * ss, 2 * R2 * ss), (0, 0, 0, 0))
    rd = ImageDraw.Draw(ring)
    rd.ellipse((0, 0, 2 * R2 * ss - 1, 2 * R2 * ss - 1), fill=(*acc, 255))
    rd.ellipse((8 * ss, 8 * ss, 2 * R2 * ss - 8 * ss - 1, 2 * R2 * ss - 8 * ss - 1), fill=(0, 0, 0, 0))
    bg.alpha_composite(ring.resize((2 * R2, 2 * R2), Image.LANCZOS), (cx - R2, cy - R2))

    # siku sudut + garis aksen vertikal
    d = ImageDraw.Draw(bg)
    _brackets(d, (24, 22, W - 24, H - 100), (*acc, 170))
    bar = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(bar).rounded_rectangle((58, 92, 63, 290), radius=3, fill=(*acc2, 255))
    bg.alpha_composite(bar.filter(ImageFilter.GaussianBlur(5)))
    bg.alpha_composite(bar)

    # label, garis pemisah, sub teks
    X = 84
    d = ImageDraw.Draw(bg)
    d.text((X, 100), t["label"], font=_font(FONT_REGULAR, 20), fill=(*acc2, 255), anchor="lm")
    for i in range(380):
        a = int(230 * (1 - i / 380))
        d.line([(X + i, 222), (X + i, 223)], fill=(*acc, a))
    d.ellipse((X - 4, 219, X + 4, 227), fill=(255, 255, 255, 255))
    sub_font, sub_text = _fit(d, t["sub"], FONT_ITALIC, 20, 13, 620)
    d.text((X, 258), sub_text, font=sub_font, fill=(205, 190, 240, 240), anchor="lm")

    # footer
    fy = H - 78
    bg.alpha_composite(Image.new("RGBA", (W, 78), (7, 3, 22, 215)), (0, fy))
    d = ImageDraw.Draw(bg)
    for x in range(W):
        a = int(200 * (1 - abs(x / W - 0.5) * 1.6))
        if a > 0:
            d.point((x, fy), fill=(*acc, a))
            d.point((x, fy + 1), fill=(*acc, a))
    logo = src.convert("RGB").crop(LOGO_CROP).resize((54, 47), Image.LANCZOS)
    patch = bg.crop((36, fy + 15, 90, fy + 62)).convert("RGB")
    bg.alpha_composite(ImageChops.add(patch, logo).convert("RGBA"), (36, fy + 15))
    d = ImageDraw.Draw(bg)
    d.text((106, fy + 29), "A S T R A L A N", font=_font(FONT_BOLD, 17), fill=(235, 225, 255, 255), anchor="lm")
    d.text((106, fy + 54), "Komunitas Stardust", font=_font(FONT_REGULAR, 11), fill=(170, 150, 215, 255), anchor="lm")
    msg_font, msg = _fit(d, t["footer_msg"], FONT_REGULAR, 14, 9, W - 50 - 400)
    d.text((W - 50, fy + 39), msg, font=msg_font, fill=(*acc, 255), anchor="rm")
    return bg


def render_card(src: Image.Image, static: Image.Image, kind: str, name: str,
                avatar_bytes: Optional[bytes], count: int, when: datetime) -> Image.Image:
    t = THEMES[kind]
    acc, acc2, glow = t["acc"], t["acc2"], t["glow"]
    bg = static.copy()

    # avatar
    D = AV_D
    try:
        av = _circle(Image.open(BytesIO(avatar_bytes)), D) if avatar_bytes else _circle(_placeholder_avatar(D), D)
    except Exception:
        av = _circle(_placeholder_avatar(D), D)
    if kind == "leave":  # avatar dibuat redup
        alpha = av.getchannel("A")
        gray = ImageOps.grayscale(av.convert("RGB")).convert("RGBA")
        av = Image.blend(gray, Image.new("RGBA", (D, D), (130, 60, 180, 255)), 0.35)
        av.putalpha(alpha)
    bg.alpha_composite(av, (AV_CX - D // 2, AV_CY - D // 2))

    # badge +/-
    bx, by = AV_CX + D // 2 - 18, AV_CY + D // 2 - 18
    d = ImageDraw.Draw(bg)
    d.ellipse((bx - 22, by - 22, bx + 22, by + 22), fill=(10, 6, 30, 255), outline=(*acc, 255), width=3)
    d.line([(bx - 8, by), (bx + 8, by)], fill=(255, 255, 255), width=4)
    if t["badge"] == "+":
        d.line([(bx, by - 8), (bx, by + 8)], fill=(255, 255, 255), width=4)

    # nama (otomatis mengecil kalau panjang)
    X = 84
    name_font, name_text = _fit(d, name, FONT_BOLD, 56, 24, 640)
    _grad_text(bg, (X, 162), name_text, name_font, t["name_grad"][0], t["name_grad"][1], glow)

    # chip info
    f = _font(FONT_REGULAR, 14)
    date_txt = f"{when.day:02d} {MONTHS[when.month - 1]} {when.year}"
    member_txt = f"MEMBER  {count}" if kind == "leave" else f"MEMBER  #{count}"
    w1 = _chip(bg, X, 304, member_txt, f, acc)
    w2 = _chip(bg, X + w1 + 12, 304, date_txt, f, acc2, 40)
    _chip(bg, X + w1 + w2 + 24, 304, t["status"], f, acc, 40)
    return bg.convert("RGB")


# ══════════════════════════════════════════════════════════════════════════════
#  COG
# ══════════════════════════════════════════════════════════════════════════════
class Welcome(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.src = Image.open(BG_PATH).convert("RGB")
        self.static = {k: _build_static(self.src, k) for k in THEMES}

    # ── bikin + kirim notif ──────────────────────────────────────────────────
    async def send_notification(self, member: discord.Member, kind: str, count: Optional[int] = None):
        guild = member.guild
        channel_id = WELCOME_CHANNEL_ID if kind == "welcome" else LEAVE_CHANNEL_ID
        channel = guild.get_channel(channel_id)
        if channel is None:
            raise RuntimeError(f"Channel {channel_id} tidak ditemukan di server ini.")

        if count is None:
            count = guild.member_count or 0
        when = datetime.now(timezone(timedelta(hours=UTC_OFFSET)))

        try:
            avatar_bytes = await member.display_avatar.replace(size=512, format="png").read()
        except Exception:
            avatar_bytes = None

        loop = asyncio.get_running_loop()  # kompatibel Python 3.8
        card = await loop.run_in_executor(
            None,
            partial(render_card, self.src, self.static[kind], kind, member.display_name, avatar_bytes, count, when),
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

    @commands.hybrid_command(name="testwelcome", description="Tes kartu welcome (admin)")
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def testwelcome(self, ctx: commands.Context, member: Optional[discord.Member] = None):
        await self._run_test(ctx, member or ctx.author, "welcome")

    @commands.hybrid_command(name="testleave", description="Tes kartu leave (admin)")
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def testleave(self, ctx: commands.Context, member: Optional[discord.Member] = None):
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