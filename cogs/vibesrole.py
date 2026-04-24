import discord
from discord.ext import commands

ROLES = {
    "Gamer": {"id": 1496848106384396382, "emoji": "🎮"},
    "Creator": {"id": 1496848431212265482, "emoji": "🎨"},
    "Social": {"id": 1496848571755008201, "emoji": "💬"},
    "Thinker": {"id": 1496848760154624100, "emoji": "🧠"},
    "Music Lover": {"id": 1496848872163639366, "emoji": "🎵"},
    "Movie Addict": {"id": 1497187182799224842, "emoji": "🎬"}
}


class RoleSelect(discord.ui.Select):
    def __init__(self):
        options = []

        for name, data in ROLES.items():
            options.append(
                discord.SelectOption(
                    label=name,
                    value=str(data["id"]),
                    emoji=data["emoji"]
                )
            )

        super().__init__(
            placeholder="✨ Pilih vibe kamu...",
            min_values=1,
            max_values=len(options),
            options=options,
            custom_id="vibe_select"
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


class RoleView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(RoleSelect())


class Vibesrole(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="setup_vibe")
    async def setup_vibe(self, ctx):
        embed = discord.Embed(
            title="Vibe Roles Panel",
            description="Pilih role sesuai kepribadian kamu.\nKlik lagi untuk melepas.",
            color=discord.Color.purple()
        )

        file = discord.File("banner_vibes.png", filename="vibes.png")
        embed.set_image(url="attachment://vibes.png")

        embed.add_field(
            name="Available Roles",
            value="\n".join(
                [f"{data['emoji']} {name}" for name, data in ROLES.items()]
            ),
            inline=False
        )

        await ctx.send(embed=embed, view=RoleView(), file=file)


async def setup(bot):
    await bot.add_cog(Vibesrole(bot))