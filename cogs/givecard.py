import discord
from discord.ext import commands
from PIL import Image, ImageDraw, ImageFont
import aiohttp
import io
import os

# ─────────────────────────────────────────────────────────────────────────────
#  KONFIGURASI
# ─────────────────────────────────────────────────────────────────────────────

VIP_ROLE_IDS = {
    1497460404077723648,
    1497460091442565241,
}

BASE_DIR = os.path.dirname(__file__)
BG_PATH  = os.path.join(BASE_DIR, "assets", "templates", "givecard_bg.png")

FONT_DIR      = os.path.join(BASE_DIR, "assets", "fonts")
FONT_USERNAME = os.path.join(FONT_DIR, "Cinzel-Regular.ttf")
FONT_MESSAGE  = os.path.join(FONT_DIR, "Cinzel-Bold.ttf")
FONT_LABEL    = os.path.join(FONT_DIR, "Raleway-Light.ttf")

_SYS_FALLBACKS = [
    "/usr/share/fonts/opentype/urw-base35/P052-BoldItalic.otf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
]

def load_font(primary: str, size: int) -> ImageFont.FreeTypeFont:
    for path in [primary] + _SYS_FALLBACKS:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


# ─────────────────────────────────────────────────────────────────────────────
#  HELPER
# ─────────────────────────────────────────────────────────────────────────────

def has_vip_role(member: discord.Member) -> bool:
    return any(role.id in VIP_ROLE_IDS for role in member.roles)


def text_width(font: ImageFont.FreeTypeFont, text: str) -> int:
    bbox = font.getbbox(text)
    return bbox[2] - bbox[0]


def text_height(font: ImageFont.FreeTypeFont, text: str) -> int:
    bbox = font.getbbox(text)
    return bbox[3] - bbox[1]


def wrap_text(text: str, font: ImageFont.FreeTypeFont, max_width: int) -> list[str]:
    words = text.split()
    lines, line = [], ""
    for word in words:
        test = (line + " " + word).strip()
        if text_width(font, test) <= max_width:
            line = test
        else:
            if line:
                lines.append(line)
            line = word
    if line:
        lines.append(line)
    return lines or [""]

def get_dynamic_font(message: str) -> ImageFont.FreeTypeFont:
    length = len(message)

    # Range ukuran font (bisa lo adjust feel-nya)
    if length <= 20:
        size = 60
    elif length <= 35:
        size = 54
    elif length <= 50:
        size = 48
    elif length <= 65:
        size = 32
    else:
        size = 36

    return load_font(FONT_MESSAGE, size)

async def fetch_avatar(session: aiohttp.ClientSession, url: str, size: int) -> Image.Image:
    async with session.get(url) as resp:
        data = await resp.read()
    img = Image.open(io.BytesIO(data)).convert("RGBA").resize((size, size), Image.LANCZOS)
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, size - 1, size - 1), fill=255)
    circle = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    circle.paste(img, mask=mask)
    return circle


# ─────────────────────────────────────────────────────────────────────────────
#  KOORDINAT LAYOUT (sesuai template 1456×816)
# ─────────────────────────────────────────────────────────────────────────────

# Pusat lingkaran kiri & kanan di template
LEFT_CX   = 379   # pusat lingkaran pengirim (X)
RIGHT_CX  = 1292  # pusat lingkaran penerima (X)
CIRCLE_CY = 475   # pusat Y kedua lingkaran

# Radius dalam lingkaran template (sesuaikan agar avatar pas)
AVATAR_R  = 99    # radius avatar (px) — sesuai diameter ~176px

# Panel pesan tengah — koordinat dari Photoshop (canvas 1456×816)
MSG_PANEL_LEFT   = 560
MSG_PANEL_TOP    = 333
MSG_PANEL_WIDTH  = 559
MSG_PANEL_HEIGHT = 260
MSG_PANEL_CX     = MSG_PANEL_LEFT + MSG_PANEL_WIDTH  // 2  # 839
MSG_PANEL_CY     = MSG_PANEL_TOP  + MSG_PANEL_HEIGHT // 2  # 482

# ─────────────────────────────────────────────────────────────────────────────
#  BUILD KARTU
# ─────────────────────────────────────────────────────────────────────────────

async def build_givecard(
    sender: discord.Member,
    receiver: discord.Member,
    message: str,
) -> io.BytesIO:

    canvas = Image.open(BG_PATH).convert("RGBA")
    W, H   = canvas.size  # 1456 x 816

    font_user    = load_font(FONT_USERNAME, 28)
    font_msg     = get_dynamic_font(message)
    font_label   = load_font(FONT_LABEL,    20)
    font_brand   = load_font(FONT_LABEL,    13)

    # ── Avatar ──────────────────────────────────────────────────────────────
    async with aiohttp.ClientSession() as session:
        av_sender   = await fetch_avatar(session, sender.display_avatar.with_size(256).url,   AVATAR_R * 2)
        av_receiver = await fetch_avatar(session, receiver.display_avatar.with_size(256).url, AVATAR_R * 2)

    # Tempel tepat di tengah lingkaran template
    canvas.paste(av_sender,   (LEFT_CX  - AVATAR_R, CIRCLE_CY - AVATAR_R), av_sender)
    canvas.paste(av_receiver, (RIGHT_CX - AVATAR_R, CIRCLE_CY - AVATAR_R), av_receiver)

    draw = ImageDraw.Draw(canvas, "RGBA")

    # ── Username di BAWAH lingkaran ──────────────────────────────────────────
    uname_y = CIRCLE_CY + AVATAR_R + 23

    sname = f"@{sender.name}"
    draw.text(
        (LEFT_CX  - text_width(font_user, sname) / 2, uname_y),
        sname,
        font=font_user,
        fill=(232, 213, 255, 230),
    )

    rname = f"@{receiver.name}"
    draw.text(
        (RIGHT_CX - text_width(font_user, rname) / 2, uname_y),
        rname,
        font=font_user,
        fill=(232, 213, 255, 230),
    )

    # ── Pesan — tengah panel ─────────────────────────────────────────────────
    lines   = wrap_text(message, font_msg, MSG_PANEL_WIDTH - 24)  # padding 12px kanan-kiri
    line_h  = text_height(font_msg, "Ag") + 10
    total_h = len(lines) * line_h
    msg_y   = MSG_PANEL_CY - total_h / 2

    for ln in lines:
        draw.text(
            (MSG_PANEL_CX - text_width(font_msg, ln) / 2, msg_y),
            ln,
            font=font_msg,
            fill=(232, 213, 255, 245),
        )
        msg_y += line_h

    # ── Watermark brand ──────────────────────────────────────────────────────
    brand = "A  S  T  R  A  L  A  N"
    draw.text(
        (W / 2 - text_width(font_brand, brand) / 2, H - 44),
        brand,
        font=font_brand,
        fill=(155, 114, 207, 100),
    )

    buf = io.BytesIO()
    canvas.convert("RGB").save(buf, format="PNG", optimize=True)
    buf.seek(0)
    return buf


# ─────────────────────────────────────────────────────────────────────────────
#  COG
# ─────────────────────────────────────────────────────────────────────────────

class GiveCard(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="givecard")
    async def givecard(self, ctx: commands.Context, penerima: discord.Member, *, pesan: str):
        """
        Kirim kartu hadiah astralan ke member lain.
        Penggunaan: !givecard @member pesan kamu di sini
        Khusus member VIP.
        """
        if not has_vip_role(ctx.author):
            await ctx.reply("✦ Fitur ini khusus member **VIP** Astralan.", mention_author=False)
            return

        if penerima.id == ctx.author.id:
            await ctx.reply("✦ Tidak bisa kirim kartu ke diri sendiri.", mention_author=False)
            return

        if len(pesan) > 75:
            await ctx.reply("✦ Pesan terlalu panjang, maksimal 75 karakter ya.", mention_author=False)
            return

        async with ctx.typing():
            image_buf = await build_givecard(
                sender=ctx.author,
                receiver=penerima,
                message=pesan,
            )

        file = discord.File(image_buf, filename="givecard.png")
        await ctx.send(
            content=f"✦ {penerima.mention}, kamu dapat kartu dari {ctx.author.mention}!",
            file=file,
        )

    @givecard.error
    async def givecard_error(self, ctx: commands.Context, error):
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.reply(
                "✦ Format salah. Cara pakai: `!givecard @member pesan kamu`",
                mention_author=False,
            )
        elif isinstance(error, commands.MemberNotFound):
            await ctx.reply("✦ Member tidak ditemukan.", mention_author=False)


async def setup(bot: commands.Bot):
    await bot.add_cog(GiveCard(bot))