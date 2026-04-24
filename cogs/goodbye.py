import discord
from discord.ext import commands
from PIL import Image, ImageDraw, ImageFont
import requests
from io import BytesIO

CHANNEL_ID = 1497151497983623320

# ── KONFIGURASI ────────────────────────────────────────────────────────────────
CIRCLE_CX = 836
CIRCLE_CY = 420
CIRCLE_R  = 205

FONT_BOLD    = "fonts/LEMONMILK-Bold.otf"
FONT_REGULAR = "fonts/LEMONMILK-Regular.otf"
FONT_LIGHT   = "fonts/LEMONMILK-RegularItalic.otf"
TEXT_X = 50


class Goodbye(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def create_goodbye_card(self, member: discord.Member) -> Image.Image:
        bg = Image.open("goodbye_bg.png").convert("RGBA")  # pakai bg khusus goodbye
        draw = ImageDraw.Draw(bg)

        DIAM = CIRCLE_R * 2
        response = requests.get(member.display_avatar.replace(size=512).url, timeout=10)
        avatar = Image.open(BytesIO(response.content)).resize((DIAM, DIAM), Image.LANCZOS).convert("RGBA")

        mask = Image.new("L", (DIAM, DIAM), 0)
        ImageDraw.Draw(mask).ellipse((0, 0, DIAM, DIAM), fill=255)
        avatar.putalpha(mask)

        bg.paste(avatar, (CIRCLE_CX - CIRCLE_R, CIRCLE_CY - CIRCLE_R), avatar)

        try:
            f_label = ImageFont.truetype(FONT_LIGHT,   30)
            f_name  = ImageFont.truetype(FONT_BOLD,    85)
            f_sub   = ImageFont.truetype(FONT_REGULAR, 22)
        except Exception:
            f_label = f_name = f_sub = ImageFont.load_default()

        label_y = CIRCLE_CY - 130
        name_y  = CIRCLE_CY - 90
        line_y  = name_y + 100
        sub_y   = line_y + 14

        draw.text((TEXT_X, label_y), "G O O D B Y E", font=f_label, fill=(120, 90, 200, 220))
        draw.text((TEXT_X, name_y), member.display_name, font=f_name, fill=(180, 70, 255, 255))
        draw.line([(TEXT_X, line_y), (TEXT_X+320, line_y)], fill=(90, 60, 150, 180), width=1)

        draw.text(
            (TEXT_X, sub_y),
            "Telah kembali ke hamparan bintang...",
            font=f_sub,
            fill=(160, 140, 200, 200)
        )

        return bg

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        print(f"[GOODBYE] {member} keluar dari: {member.guild.name}")
        channel = member.guild.get_channel(CHANNEL_ID)

        if channel is None:
            print("[GOODBYE] Channel tidak ditemukan!")
            return

        try:
            card = self.create_goodbye_card(member)
            buf = BytesIO()
            card.save(buf, format="PNG")
            buf.seek(0)

            file = discord.File(buf, filename="goodbye.png")

            embed = discord.Embed(
                description=
                f"{member.mention} telah meninggalkan **Astralan**.\n\n Terima kasih sudah menjadi bagian dari komunitas ini\n Semoga perjalananmu menyenangkan di luar sana.",
                color=0x6A3DFF,
            )
            embed.set_image(url="attachment://goodbye.png")

            await channel.send(embed=embed, file=file)

        except Exception as e:
            print(f"[GOODBYE] Error: {e}")


async def setup(bot):
    await bot.add_cog(Goodbye(bot))