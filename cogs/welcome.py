import discord
from discord.ext import commands

class Welcome(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member):
        channel = discord.utils.get(member.guild.text_channels, name="welcome")
        if channel:
            await channel.send(f"Selamat datang {member.mention} di Astralan 🌌")

async def setup(bot):
    await bot.add_cog(Welcome(bot))