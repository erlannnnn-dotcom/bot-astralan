import discord
from discord.ext import commands
from discord import app_commands

class Rules(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="rules", description="Tampilkan rules server")
    async def rules(self, interaction: discord.Interaction):
        await interaction.response.send_message("""
📜 **RULES ASTRALAN**

1. Respect semua member  
2. No toxic  
3. No spam  
4. Ikuti event dengan fair  

Enjoy your stay 🌌
""")

async def setup(bot):
    await bot.add_cog(Rules(bot))