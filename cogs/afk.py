import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime
import random

class AFK(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.afk_users = {}

    def random_color(self):
        return discord.Color(random.randint(0, 0xFFFFFF))

    def format_time(self, seconds):
        minutes, seconds = divmod(seconds, 60)
        hours, minutes = divmod(minutes, 60)
        days, hours = divmod(hours, 24)

        if days > 0:
            return f"{days} hari {hours} jam"
        elif hours > 0:
            return f"{hours} jam {minutes} menit"
        elif minutes > 0:
            return f"{minutes} menit {seconds} detik"
        else:
            return f"{seconds} detik"

    @app_commands.command(name="afk", description="Set status AFK")
    async def afk(self, interaction: discord.Interaction, reason: str = "AFK"):
        user = interaction.user

        self.afk_users[user.id] = {
            "reason": reason,
            "since": datetime.utcnow()
        }

        # ubah nickname jadi [AFK]
        try:
            if interaction.guild:
                await user.edit(nick=f"[AFK] {user.display_name}")
        except:
            pass

        embed = discord.Embed(
            title="🌙 Kamu sekarang AFK",
            description=f"**Alasan:** {reason}",
            color=self.random_color()
        )
        embed.set_footer(text="Status AFK aktif")

        await interaction.response.send_message(embed=embed)

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return

        # BALIK DARI AFK
        if message.author.id in self.afk_users:
            data = self.afk_users.pop(message.author.id)
            afk_time = (datetime.utcnow() - data["since"]).total_seconds()
            waktu = self.format_time(int(afk_time))

            # balikin nickname
            try:
                if message.guild:
                    original_name = message.author.display_name.replace("[AFK] ", "")
                    await message.author.edit(nick=original_name)
            except:
                pass

            embed = discord.Embed(
                title="👋 Welcome Back!",
                description=f"{message.author.mention} sudah kembali dari AFK\n\n⏳ Durasi AFK: **{waktu}**",
                color=self.random_color()
            )
            await message.channel.send(embed=embed)

        # CEK ORANG YANG DI MENTION
        for user in message.mentions:
            if user.id in self.afk_users:
                data = self.afk_users[user.id]
                afk_time = (datetime.utcnow() - data["since"]).total_seconds()
                waktu = self.format_time(int(afk_time))

                embed = discord.Embed(
                    title="⚠️ User sedang AFK",
                    description=(
                        f"{user.mention} sedang AFK\n"
                        f"📝 Alasan: **{data['reason']}**\n"
                        f"⏳ Sejak: **{waktu} yang lalu**"
                    ),
                    color=self.random_color()
                )

                await message.channel.send(embed=embed)

async def setup(bot):
    await bot.add_cog(AFK(bot))