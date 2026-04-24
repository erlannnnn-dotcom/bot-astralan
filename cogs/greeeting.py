import discord
from discord.ext import commands, tasks
from datetime import datetime, timedelta

CHANNEL_ID = 1494993934315946079  # ganti
STARDUST_ROLE_ID = 1496840197248122952  # ganti (role stardust)

class Greeting(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.greeting_loop.start()

    def cog_unload(self):
        self.greeting_loop.cancel()

    def get_wib_time(self):
        return datetime.utcnow() + timedelta(hours=7)

    @tasks.loop(minutes=1)
    async def greeting_loop(self):
        now = self.get_wib_time()
        hour = now.hour
        minute = now.minute

        if minute != 0:
            return

        channel = self.bot.get_channel(CHANNEL_ID)
        if channel is None:
            return

        if hour == 6:
            await self.send_greeting(channel, "pagi", now)
        elif hour == 12:
            await self.send_greeting(channel, "siang", now)
        elif hour == 18:
            await self.send_greeting(channel, "sore", now)
        elif hour == 21:
            await self.send_greeting(channel, "malam", now)

    async def send_greeting(self, channel, waktu, now):
        role_mention = f"<@&{STARDUST_ROLE_ID}>"

        teks = {
            "pagi": {
                "title": "Selamat Pagi, Stardust",
                "desc": (
                    f"{role_mention}\n\n"
                    "Semesta baru saja membuka lembaran hari yang segar.\n"
                    "Ambil napas perlahan, kumpulkan energi, dan mulai langkahmu dengan tenang.\n"
                    "Hari ini adalah kesempatan baru untuk bersinar."
                ),
                "color": discord.Color.from_rgb(255, 183, 77)
            },
            "siang": {
                "title": "Selamat Siang, Stardust",
                "desc": (
                    f"{role_mention}\n\n"
                    "Waktu terus berjalan, dan kamu sudah sampai di tengah perjalanan hari ini.\n"
                    "Jangan lupa berhenti sejenak, isi ulang energi, lalu lanjutkan dengan ritmemu sendiri.\n"
                    "Semua progres tetap berarti."
                ),
                "color": discord.Color.from_rgb(255, 213, 79)
            },
            "sore": {
                "title": "Selamat Sore, Stardust",
                "desc": (
                    f"{role_mention}\n\n"
                    "Langit mulai meredup, membawa suasana yang lebih tenang.\n"
                    "Ini saat yang tepat untuk melepas penat dan menikmati momen kecil yang hangat.\n"
                    "Biarkan hari ini ditutup dengan rasa damai."
                ),
                "color": discord.Color.from_rgb(129, 212, 250)
            },
            "malam": {
                "title": "Selamat Malam, Stardust",
                "desc": (
                    f"{role_mention}\n\n"
                    "Malam datang membawa ketenangan.\n"
                    "Saatnya beristirahat, menenangkan pikiran, dan mengisi ulang energi.\n"
                    "Besok adalah perjalanan baru yang menunggu."
                ),
                "color": discord.Color.from_rgb(179, 157, 219)
            }
        }

        data = teks[waktu]

        embed = discord.Embed(
            title=data["title"],
            description=data["desc"],
            color=data["color"]
        )

        embed.add_field(
            name="Waktu Sekarang",
            value=now.strftime("%H:%M WIB"),
            inline=False
        )

        embed.set_footer(text="Astral System")

        await channel.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Greeting(bot))