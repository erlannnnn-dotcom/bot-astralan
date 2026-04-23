import discord
from discord.ext import commands
from discord import app_commands

class AFK(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.afk_users = {}

    @app_commands.command(name="afk", description="Set status AFK")
    async def afk(self, interaction: discord.Interaction, reason: str = "AFK"):
        self.afk_users[interaction.user.id] = reason
        await interaction.response.send_message(f"Kamu sekarang AFK: {reason}")

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return

        if message.author.id in self.afk_users:
            del self.afk_users[message.author.id]
            await message.channel.send(f"{message.author.mention} sudah tidak AFK lagi!")

        for user in message.mentions:
            if user.id in self.afk_users:
                await message.channel.send(
                    f"{user.name} lagi AFK: {self.afk_users[user.id]}"
                )

async def setup(bot):
    await bot.add_cog(AFK(bot))