import discord
from discord.ext import commands
from discord import app_commands
from PIL import Image, ImageDraw, ImageFont
import aiohttp
import io
import os
import textwrap
from datetime import datetime

# ─── CONFIG ───────────────────────────────────────────────────────────────────
# Role ID VIP (isi dengan ID role VIP kamu)
VIP_ROLE_IDS = [
    1497460091442565241,   # VIP Role 1
    1497460404077723648,   # VIP Role 2
]

# Path ke background template (sesuaikan dengan lokasi file)
TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "assets", "templates")

# Nama file template per platform
TEMPLATES = {
    "whatsapp":  "wa_bg.png",
    "twitter":   "twitter_bg.png",
    "instagram": "instagram_bg.png",
    "discord":   "discord_bg.png",
}

# ─── LAYOUT CONFIG ────────────────────────────────────────────────────────────
# Sesuaikan koordinat ini dengan posisi elemen di background masing-masing.
# (x, y) = pojok kiri atas area teks / gambar.
LAYOUT = {
    "whatsapp": {
        "username":    (486, 213),    # posisi teks username
        "status":      (486, 251),    # posisi teks "online / status"
        "message":     (411, 383),    # pojok kiri atas kotak pesan
        "message_box": (485, 509),    # lebar x tinggi area teks pesan
        "time":        (800, 900),    # posisi timestamp (17:44)
        "avatar":      (337, 176),    # pojok kiri atas lingkaran avatar (100x100 px)
        "avatar_size": (120, 120),
        # Font sizes
        "font_username": 30,
        "font_status":   24,
        "font_message":  105,
        "font_time":     35,
        # Warna teks
        "color_username": (255, 255, 255),
        "color_status":   (150, 255, 180),
        "color_message":  (220, 255, 230),
        "color_time":     (150, 220, 170),
    },
    "twitter": {
        "username":    (437, 393),
        "status":      (437, 431),
        "message":     (339, 534),
        "message_box": (586, 295),
        "time":        (885, 845),
        "avatar":      (304, 367),    
        "avatar_size": (104, 104),
        "font_username": 34,
        "font_status":   24,
        "font_message":  90,
        "font_time":     22,
        "color_username": (255, 255, 255),
        "color_status":   (110, 130, 150),
        "color_message":  (220, 225, 230),
        "color_time":     (100, 120, 140),
    },
    "instagram": {
        "username":    (210, 175),
        "status":      (210, 215),
        "message":     (210, 265),
        "message_box": (680, 200),
        "time":        (210, 490),
        "avatar":      (80, 160),
        "avatar_size": (110, 110),
        "font_username": 34,
        "font_status":   24,
        "font_message":  28,
        "font_time":     22,
        "color_username": (255, 255, 255),
        "color_status":   (180, 180, 180),
        "color_message":  (240, 240, 240),
        "color_time":     (150, 150, 150),
    },
    "discord": {
        "username":    (210, 175),
        "status":      (210, 215),
        "message":     (210, 265),
        "message_box": (680, 200),
        "time":        (210, 490),
        "avatar":      (80, 155),
        "avatar_size": (110, 110),
        "font_username": 34,
        "font_status":   24,
        "font_message":  28,
        "font_time":     22,
        "color_username": (255, 255, 255),
        "color_status":   (180, 180, 180),
        "color_message":  (220, 222, 225),
        "color_time":     (114, 118, 125),
    },
}

# ── Samakan semua ukuran & posisi ke WhatsApp ──
base = LAYOUT["whatsapp"]

keys_to_sync = [
    "username",
    "status",
    "message",
    "message_box",
    "time",
    "avatar",
    "avatar_size",
    "font_username",
    "font_status",
    "font_message",
    "font_time",
]

for platform in ["instagram", "discord"]:
    for key in keys_to_sync:
        LAYOUT[platform][key] = base[key]

# ─── HELPERS ──────────────────────────────────────────────────────────────────

def has_vip(member: discord.Member) -> bool:
    """Cek apakah member punya salah satu role VIP."""
    return any(role.id in VIP_ROLE_IDS for role in member.roles)


def load_font(size: int) -> ImageFont.FreeTypeFont:
    """Load font; fallback ke default jika tidak ada font kustom."""
    font_paths = [
        "cogs/assets/fonts/Raleway-SemiBold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "arial.ttf",
    ]
    for path in font_paths:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    return ImageFont.load_default()


def circle_crop(img: Image.Image, size: tuple) -> Image.Image:
    """Crop gambar jadi lingkaran."""
    img = img.resize(size, Image.LANCZOS).convert("RGBA")
    mask = Image.new("L", size, 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((0, 0, size[0], size[1]), fill=255)
    result = Image.new("RGBA", size, (0, 0, 0, 0))
    result.paste(img, mask=mask)
    return result


async def fetch_avatar(avatar_url: str, size: tuple) -> Image.Image | None:
    """Download avatar dari URL dan kembalikan sebagai gambar lingkaran."""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(str(avatar_url)) as resp:
                if resp.status == 200:
                    data = await resp.read()
                    img = Image.open(io.BytesIO(data))
                    return circle_crop(img, size)
    except Exception:
        pass
    return None

VERIFIED_ICON_PATH = os.path.join(
    os.path.dirname(__file__), "assets", "templates", "Twitter_Verified.png"
)

def load_verified_icon(size: int = 24):
    if os.path.exists(VERIFIED_ICON_PATH):
        img = Image.open(VERIFIED_ICON_PATH).convert("RGBA")
        return img.resize((size, size), Image.LANCZOS)
    return None


def generate_image(
    platform: str,
    username: str,
    text: str,
    time_str: str,
    avatar_img: Image.Image | None,
    status: str = "online",
    member: discord.Member | None = None,
) -> io.BytesIO:
    """Buat gambar fake chat di atas template background."""
    layout = LAYOUT[platform]

    # Load template background
    template_path = os.path.join(TEMPLATE_DIR, TEMPLATES[platform])
    if not os.path.exists(template_path):
        raise FileNotFoundError(
            f"Template '{TEMPLATES[platform]}' tidak ditemukan di {TEMPLATE_DIR}.\n"
            "Pastikan kamu sudah menaruh file background di folder assets/templates/."
        )

    bg = Image.open(template_path).convert("RGBA")
    draw = ImageDraw.Draw(bg)

    # ── Avatar ──
    if avatar_img:
        avatar_img = avatar_img.convert("RGBA")
        bg.paste(avatar_img, layout["avatar"], mask=avatar_img)

    # ── Username ──
    font_user = load_font(layout["font_username"])
    draw.text(layout["username"], username, font=font_user, fill=layout["color_username"])

    # ── Verified badge (Twitter & Instagram only) ──
    if platform in ["twitter", "instagram"]:
        icon = load_verified_icon(size=int(layout["font_username"] * 0.8))

        if icon:
            # hitung lebar teks username
            bbox = draw.textbbox((0, 0), username, font=font_user)
            text_width = bbox[2] - bbox[0]

            # posisi icon (di kanan username)
            icon_x = layout["username"][0] + text_width + 9  # jarak 8px
            icon_y = layout["username"][1] + 5

            bg.paste(icon, (icon_x, icon_y), mask=icon)

    font_status = load_font(layout["font_status"])

    # khusus Twitter → pakai username Discord member
    if member and platform in ["twitter", "instagram", "discord"]:
        status_text = f"@{member.name}"
    else:
        status_text = status

    draw.text(layout["status"], status_text, font=font_status, fill=layout["color_status"])

        # ── Message (dynamic: sedikit teks besar, banyak teks mengecil) ──
    max_width_px, max_height_px = layout["message_box"]

    # mulai dari ukuran DEFAULT (font_message = ukuran terbesar)
    max_font_size = layout["font_message"]
    min_font_size = 12

    font_size = max_font_size

    while font_size >= min_font_size:
        font_msg = load_font(font_size)

        # wrap berdasarkan ukuran font sekarang
        chars_per_line = max(10, int(max_width_px / (font_size * 0.55)))
        wrapped = textwrap.fill(text, width=chars_per_line)

        # hitung ukuran teks
        bbox = draw.multiline_textbbox((0, 0), wrapped, font=font_msg, spacing=8)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]

        # kalau muat → pakai ukuran ini
        if text_width <= max_width_px and text_height <= max_height_px:
            break

        # kalau tidak muat → kecilin
        font_size -= 2

    # posisi X tetap (rata kiri)
    x = layout["message"][0]

    # posisi Y tetap center vertical
    box_y = layout["message"][1]
    y = box_y + (max_height_px - text_height) // 2

    draw.multiline_text(
        (x, y),
        wrapped,
        font=font_msg,
        fill=layout["color_message"],
        spacing=8,
        align="left"
    )

    # ── Timestamp ──
    font_time = load_font(layout["font_time"])
    draw.text(layout["time"], time_str, font=font_time, fill=layout["color_time"])

    # Simpan ke buffer
    buffer = io.BytesIO()
    bg.convert("RGB").save(buffer, format="PNG")
    buffer.seek(0)
    return buffer


# ─── COG ──────────────────────────────────────────────────────────────────────

class FakeChat(commands.Cog):
    """Cog untuk fitur Fake Chat / Tweet Generator."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def fakechat(
        self,
        interaction: discord.Interaction,
        username: str,
        text: str,
        platform: app_commands.Choice[str] | None = None,
        status: str = "online",
        time: str | None = None,
    ):
        await interaction.response.defer()

        member = interaction.user
        is_vip = has_vip(member)

        # Tentukan platform
        if platform is not None:
            if not is_vip:
                await interaction.followup.send(
                    "❌ Kamu butuh role **VIP** untuk memilih platform lain.\n"
                    "Member hanya bisa menggunakan template **WhatsApp**.",
                    ephemeral=True,
                )
                return
            chosen_platform = platform.value
        else:
            chosen_platform = "whatsapp"  # default untuk member biasa

        # Waktu
        time_str = time if time else datetime.now().strftime("%H:%M")

        # Ambil avatar user Discord (opsional: bisa diganti avatar custom)
        avatar_img = None
        if member.display_avatar:
            avatar_size = LAYOUT[chosen_platform]["avatar_size"]
            avatar_img = await fetch_avatar(member.display_avatar.url, avatar_size)

        # Generate gambar
        try:
            buffer = generate_image(
                platform=chosen_platform,
                username=username,
                text=text,
                time_str=time_str,
                avatar_img=avatar_img,
                status=status,
                member=interaction.user
            )
        except FileNotFoundError as e:
            await interaction.followup.send(f"⚠️ {e}", ephemeral=True)
            return
        except Exception as e:
            await interaction.followup.send(
                f"❌ Gagal generate gambar: `{e}`", ephemeral=True
            )
            return

        file = discord.File(buffer, filename=f"fakechat_{chosen_platform}.png")
        platform_label = chosen_platform.capitalize()
        await interaction.followup.send(
            content=f"**Fake {platform_label} Chat** — `{username}`",
            file=file,
        )

    # ── Prefix command (!fakechat) ──
    @commands.command(name="fakechat")
    async def fakechat_prefix(
        self,
        ctx: commands.Context,
        username: str,
        *,
        text: str,
    ):
        """
        Prefix: !fakechat <username> <teks>
        VIP: !fakechat <platform> <username> <teks>
        """
        member = ctx.author
        is_vip = has_vip(member)

        # Cek apakah arg pertama adalah nama platform (hanya VIP)
        platforms = list(TEMPLATES.keys())
        parts = text.split(maxsplit=1)

        chosen_platform = "whatsapp"
        if is_vip and username.lower() in platforms:
            chosen_platform = username.lower()
            if not parts:
                await ctx.reply("❌ Format: `!fakechat <platform> <username> <teks>`")
                return
            # geser argumen
            username = parts[0]
            text = parts[1] if len(parts) > 1 else ""
            if not text:
                await ctx.reply("❌ Teks pesan tidak boleh kosong.")
                return

        time_str = datetime.now().strftime("%H:%M")

        avatar_img = None
        if member.display_avatar:
            avatar_size = LAYOUT[chosen_platform]["avatar_size"]
            avatar_img = await fetch_avatar(member.display_avatar.url, avatar_size)

        async with ctx.typing():
            try:
                buffer = generate_image(
                    platform=chosen_platform,
                    username=username,
                    text=text,
                    time_str=time_str,
                    avatar_img=avatar_img,
                    member=ctx.author  # ← INI YANG KURANG
                )
            except FileNotFoundError as e:
                await ctx.reply(f"⚠️ {e}")
                return
            except Exception as e:
                await ctx.reply(f"❌ Gagal generate gambar: `{e}`")
                return

        file = discord.File(buffer, filename=f"fakechat_{chosen_platform}.png")
        await ctx.reply(
            content=f"✨ **Fake {chosen_platform.capitalize()} Chat** — `{username}`",
            file=file,
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(FakeChat(bot))