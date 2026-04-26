import discord
from discord.ext import commands
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import aiohttp
import io
import os
import textwrap

# ╔══════════════════════════════════════════════════════════════╗
#                        KONFIGURASI UTAMA
#   Ganti semua ID di bawah ini sesuai server kamu
# ╚══════════════════════════════════════════════════════════════╝

QUOTE_CHANNEL_ID   = 1497429373299593296   # ID channel #quote
GALLERY_CHANNEL_ID = 1497457550935982081   # ID channel #quote-gallery (VIP)

# Role yang dianggap VIP — salah satu role sudah cukup
VIP_ROLE_IDS = [
    1497460091442565241,   # Role "Server Booster" (copy dari server settings)
    1497460404077723648,   # Role donasi — tambah/hapus sesuai kebutuhan
]

# ╔══════════════════════════════════════════════════════════════╗
#                      KONFIGURASI VISUAL
# ╚══════════════════════════════════════════════════════════════╝

ASSETS_DIR = os.path.join(os.path.dirname(__file__), "assets")
FONT_DIR   = os.path.join(ASSETS_DIR, "fonts")

# Background:
#   FREE → quote_bg_free.png   (boleh pakai yang ada watermark/logo)
#   VIP  → quote_bg_vip.png    (background bersih / lebih mewah)
BG_FREE = os.path.join(ASSETS_DIR, "quote_bg_free.png")
BG_VIP  = os.path.join(ASSETS_DIR, "quote_bg_vip.png")

IMG_W, IMG_H = 1456, 816

RING_FREE       = (160, 80,  255, 200)   # ungu
RING_VIP        = (255, 200, 50,  230)   # gold
LINE_FREE       = (160, 80,  255, 200)
LINE_VIP        = (255, 200, 50,  200)
WATERMARK_TEXT  = "astralan"
WATERMARK_COLOR = (255, 255, 255, 35)
VIP_BADGE_TEXT  = "✦ VIP"
VIP_BADGE_COLOR = (255, 200, 50, 255)


# ══════════════════════════════════════════════════════════════
def is_vip(member: discord.Member) -> bool:
    """True jika member punya salah satu role VIP."""
    role_ids = {r.id for r in member.roles}
    return bool(role_ids & set(VIP_ROLE_IDS))


# ══════════════════════════════════════════════════════════════
class Quotes(commands.Cog):
    """Quote card generator — Free & VIP tier."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ── Fetch avatar ─────────────────────────────────────────
    async def _fetch_avatar(self, member: discord.Member) -> Image.Image:
        url = member.display_avatar.replace(size=128, format="png").url
        async with aiohttp.ClientSession() as s:
            async with s.get(url) as r:
                data = await r.read()
        return Image.open(io.BytesIO(data)).convert("RGBA")

    # ── Circular mask ─────────────────────────────────────────
    @staticmethod
    def _circle(img: Image.Image, size: int) -> Image.Image:
        img  = img.resize((size, size), Image.LANCZOS)
        mask = Image.new("L", (size, size), 0)
        ImageDraw.Draw(mask).ellipse((0, 0, size, size), fill=255)
        out  = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        out.paste(img, (0, 0), mask)
        return out

    # ── Load font ─────────────────────────────────────────────
    @staticmethod
    def _font(name: str, size: int) -> ImageFont.FreeTypeFont:
        try:
            return ImageFont.truetype(os.path.join(FONT_DIR, name), size)
        except Exception:
            return ImageFont.load_default()

    # ── Glow ring avatar ─────────────────────────────────────
    @staticmethod
    def _ring_layer(ax, ay, size, color, vip) -> Image.Image:
        layer = Image.new("RGBA", (IMG_W, IMG_H), (0, 0, 0, 0))
        d     = ImageDraw.Draw(layer)
        r, g, b, _ = color
        if vip:
            for off, a in [(12, 60), (7, 120), (3, 200)]:
                d.ellipse((ax-off, ay-off, ax+size+off, ay+size+off),
                          outline=(r, g, b, a), width=2)
            return layer.filter(ImageFilter.GaussianBlur(radius=6))
        else:
            d.ellipse((ax-5, ay-5, ax+size+5, ay+size+5),
                      outline=color, width=3)
            return layer.filter(ImageFilter.GaussianBlur(radius=4))

    # ── Watermark diagonal (free only) ───────────────────────
    def _watermark(self, canvas: Image.Image) -> Image.Image:
        wm_font = self._font("Raleway-Regular.ttf", 22)
        for row in range(3):
            for col in range(4):
                tile = Image.new("RGBA", (IMG_W, IMG_H), (0, 0, 0, 0))
                ImageDraw.Draw(tile).text(
                    (600 + col * 220, 180 + row * 200),
                    WATERMARK_TEXT, font=wm_font, fill=WATERMARK_COLOR
                )
                tile   = tile.rotate(-25, expand=False)
                canvas = Image.alpha_composite(canvas, tile)
        return canvas

    # ── Badge VIP ─────────────────────────────────────────────
    def _vip_badge(self, canvas: Image.Image, ax, ay) -> Image.Image:
        layer = Image.new("RGBA", (IMG_W, IMG_H), (0, 0, 0, 0))
        d     = ImageDraw.Draw(layer)
        bx, by = ax - 2, ay - 28
        d.rounded_rectangle((bx, by, bx+68, by+22),
                             radius=11,
                             fill=(160, 110, 0, 200),
                             outline=(255, 200, 50, 220), width=1)
        d.text((bx+8, by+2), VIP_BADGE_TEXT,
               font=self._font("Raleway-SemiBold.ttf", 18),
               fill=VIP_BADGE_COLOR)
        return Image.alpha_composite(canvas, layer)

    # ── CORE: generate image ──────────────────────────────────
    async def generate_quote_image(
        self, quote_text: str, member: discord.Member, vip: bool
    ) -> bytes:

        # Background
        bg_path = BG_VIP if (vip and os.path.exists(BG_VIP)) else BG_FREE
        if os.path.exists(bg_path):
            bg = Image.open(bg_path).convert("RGBA").resize((IMG_W, IMG_H), Image.LANCZOS)
        else:
            bg = Image.new("RGBA", (IMG_W, IMG_H), (15, 5, 35, 255))
        canvas = bg.copy()

        # Font & ukuran dinamis
        n = len(quote_text)
        if   n < 80:  qs, ww = 58, 32
        elif n < 160: qs, ww = 48, 38
        elif n < 260: qs, ww = 40, 44
        else:         qs, ww = 34, 50

        f_q = self._font("PlayfairDisplay-Italic.ttf", qs)
        f_n = self._font("Raleway-SemiBold.ttf", 32)
        f_u = self._font("Raleway-Regular.ttf", 24)

        # Wrapping & posisi teks
        TX     = 590
        lines  = textwrap.fill(quote_text, width=ww).split("\n")
        lh     = qs + 14
        total  = len(lines) * lh
        ty     = IMG_H // 2 - total // 2 - 30

        # Glow teks
        glow_col = (255, 180, 30, 65) if vip else (120, 60, 200, 65)
        glow     = Image.new("RGBA", (IMG_W, IMG_H), (0, 0, 0, 0))
        gd       = ImageDraw.Draw(glow)
        for i, ln in enumerate(lines):
            gd.text((TX+3, ty + i*lh + 3), ln, font=f_q, fill=glow_col)
        glow   = glow.filter(ImageFilter.GaussianBlur(radius=10))
        canvas = Image.alpha_composite(canvas, glow)
        draw   = ImageDraw.Draw(canvas)

        # Teks quote
        oc = (100, 50, 0, 150) if vip else (80, 20, 140, 150)
        for i, ln in enumerate(lines):
            y = ty + i * lh
            for ox, oy in ((-1,-1),(1,-1),(-1,1),(1,1)):
                draw.text((TX+ox, y+oy), ln, font=f_q, fill=oc)
            draw.text((TX, y), ln, font=f_q, fill=(255, 255, 255, 245))

        # Garis dekorasi
        dy  = ty + total + 22
        lc  = LINE_VIP if vip else LINE_FREE
        draw.line([(TX, dy), (TX+320, dy)], fill=lc, width=2)

        # Ring avatar
        AV   = 90
        ax   = TX
        ay   = dy + 28
        rc   = RING_VIP if vip else RING_FREE
        ring = self._ring_layer(ax, ay, AV, rc, vip)
        canvas = Image.alpha_composite(canvas, ring)

        # Avatar
        av_img = await self._fetch_avatar(member)
        av_img = self._circle(av_img, AV)
        canvas.paste(av_img, (ax, ay), av_img)

        # Badge VIP
        if vip:
            canvas = self._vip_badge(canvas, ax, ay)

        # Nama & username
        draw     = ImageDraw.Draw(canvas)
        nx, ny   = ax + AV + 14, ay + 14
        nc       = (255, 210, 80, 255) if vip else (255, 255, 255, 255)
        draw.text((nx, ny),    member.display_name, font=f_n, fill=nc)
        draw.text((nx, ny+36), f"@{member.name}",   font=f_u,
                  fill=(200, 160, 255, 200))

        # Watermark free
        if not vip:
            canvas = self._watermark(canvas)

        # Simpan sebagai bytes
        buf = io.BytesIO()
        canvas.convert("RGB").save(buf, format="PNG", optimize=True)
        return buf.getvalue()

    # ── on_message ───────────────────────────────────────────
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return
        if message.channel.id != QUOTE_CHANNEL_ID:
            return
        if self.bot.user not in message.mentions:
            return

        # Bersihkan mention
        text = message.content
        for tok in (f"<@{self.bot.user.id}>", f"<@!{self.bot.user.id}>"):
            text = text.replace(tok, "").strip()

        if not text:
            await message.reply(
                "Tulis quote-mu setelah mention aku!\n"
                "Contoh: `@Bot Hidup adalah perjalanan, bukan tujuan.`",
                delete_after=10,
            )
            return

        member = message.author
        vip    = is_vip(member)

        async with message.channel.typing():
            try:
                img_data = await self.generate_quote_image(text, member, vip)

                # Kirim ke channel quote
                color = 0xF0C030 if vip else 0x7B2FBE
                embed = discord.Embed(color=color)
                if vip:
                    embed.set_footer(text="✦ VIP Quote")
                embed.set_image(url="attachment://quote.png")

                await message.reply(
                    file=discord.File(io.BytesIO(img_data), "quote.png"),
                    embed=embed,
                )

                # Auto-post ke gallery (VIP only)
                if vip:
                    gallery = message.guild.get_channel(GALLERY_CHANNEL_ID)
                    if gallery:
                        ge = discord.Embed(
                            color=0xF0C030,
                            description=f'*"{text}"*',
                        )
                        ge.set_author(
                            name=member.display_name,
                            icon_url=member.display_avatar.url,
                        )
                        ge.set_image(url="attachment://quote.png")
                        ge.set_footer(
                            text=f"#{message.channel.name}  •  ✦ VIP Quote"
                        )
                        await gallery.send(
                            file=discord.File(io.BytesIO(img_data), "quote.png"),
                            embed=ge,
                        )

            except Exception as e:
                await message.reply(f"❌ Gagal generate quote: `{e}`")

    # ── Prefix: !vipinfo ─────────────────────────────────────
    @commands.command(name="vipinfo")
    async def vipinfo(self, ctx: commands.Context):
        """Cek status VIP kamu untuk fitur Quote."""
        member = ctx.author
        vip    = is_vip(member)

        if vip:
            embed = discord.Embed(
                title="✦ VIP Quote — Aktif",
                description=(
                    "Kamu punya akses **VIP Quote**! 🎉\n\n"
                    "**Yang kamu dapat:**\n"
                    "‣ Background eksklusif tanpa watermark\n"
                    "‣ Ring avatar **emas** berlapis\n"
                    "‣ Badge **✦ VIP** di foto quote\n"
                    "‣ Quote otomatis masuk ke galeri server"
                ),
                color=0xF0C030,
            )
        else:
            roles = " / ".join(f"<@&{rid}>" for rid in VIP_ROLE_IDS)
            embed = discord.Embed(
                title="Quote — Free",
                description=(
                    "Kamu pakai Quote versi **Free**.\n\n"
                    f"Boost server (role: Astral Elite (VIP-I)) atau dapatkan role: Astral Sovereign (VIP-II) untuk unlock **VIP Quote**!"
                ),
                color=0x7B2FBE,
            )

        # Kirim sebagai DM agar tidak spam di channel
        try:
            await ctx.author.send(embed=embed)
            await ctx.message.add_reaction("📬")
        except discord.Forbidden:
            # Kalau DM tertutup, kirim di channel saja (lalu auto-delete)
            await ctx.reply(embed=embed, delete_after=15)


# ══════════════════════════════════════════════════════════════
async def setup(bot: commands.Bot):
    await bot.add_cog(Quotes(bot))