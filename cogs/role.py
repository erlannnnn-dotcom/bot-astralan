import discord
from discord.ext import commands
from discord import app_commands

class RoleView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🎮 Gamer", style=discord.ButtonStyle.primary)
    async def gamer(self, interaction: discord.Interaction, button: discord.ui.Button):
        role = discord.utils.get(interaction.guild.roles, name="Gamer")

        if role in interaction.user.roles:
            await interaction.user.remove_roles(role)
            await interaction.response.send_message("Role Gamer dilepas", ephemeral=True)
        else:
            await interaction.user.add_roles(role)
            await interaction.response.send_message("Role Gamer diambil", ephemeral=True)

class Role(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="setup_role", description="Setup role button")
    async def setup_role(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            "Pilih role kamu:",
            view=RoleView()
        )

async def setup(bot):
    await bot.add_cog(Role(bot))