import discord
from discord.ext import commands

GAME_ROLES = {
    "Roblox": {"id": 1496849096911229109, "emoji": "🧱"},
    "Minecraft": {"id": 1496849678640218223, "emoji": "⛏️"},
    "GTA": {"id": 1496849773389418536, "emoji": "🚗"},
    "Mobile Legend": {"id": 1497203663276478494, "emoji": "🧙"},
    "PUBG": {"id": 1496849816893001798, "emoji": "🔫"},
    "HOK": {"id": 1497203796399620358, "emoji": "⚔️"},
    "Delta Force": {"id": 1497203904159416360, "emoji": "🎯"},
    "Valorant": {"id": 1496849865433546792, "emoji": "💥"},
    "Free Fire": {"id": 1496849913034706964, "emoji": "🔥"},
    "Efootball": {"id": 1496849953564135424, "emoji": "⚽"},
    "EA FC": {"id": 1496850065560567808, "emoji": "🏆"}
}


class GameSelect(discord.ui.Select):
    def __init__(self):
        options = []

        for game, data in GAME_ROLES.items():
            options.append(
                discord.SelectOption(
                    label=game,
                    value=str(data["id"]),
                    emoji=data["emoji"]
                )
            )

        super().__init__(
            placeholder="🎮 Pilih game favorit kamu...",
            min_values=1,
            max_values=len(options),
            options=options,
            custom_id="game_select"
        )

    async def callback(self, interaction: discord.Interaction):
        added = []
        removed = []

        for value in self.values:
            role = interaction.guild.get_role(int(value))

            if role in interaction.user.roles:
                await interaction.user.remove_roles(role)
                removed.append(role.name)
            else:
                await interaction.user.add_roles(role)
                added.append(role.name)

        msg = ""

        if added:
            msg += "**Diambil:** " + ", ".join(added) + "\n"
        if removed:
            msg += "**Dilepas:** " + ", ".join(removed)

        await interaction.response.send_message(msg, ephemeral=True)


class GameRoleView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(GameSelect())


class Role(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="setup_role")
    @commands.has_permissions(administrator=True)
    async def setup_role(self, ctx):
        embed = discord.Embed(
            title="Game Roles Panel",
            description="Pilih game untuk mendapatkan role.\nKlik lagi untuk melepas.",
            color=discord.Color.blue()
        )

        # FILE LOKAL
        file = discord.File("banner_roles.png", filename="banner.png")
        embed.set_image(url="attachment://banner.png")

        embed.add_field(
            name="Available Games",
            value="\n".join(
                [f"{data['emoji']} {game}" for game, data in GAME_ROLES.items()]
            ),
            inline=False
        )

        await ctx.send(embed=embed, view=GameRoleView(), file=file)


async def setup(bot):
    await bot.add_cog(Role(bot))