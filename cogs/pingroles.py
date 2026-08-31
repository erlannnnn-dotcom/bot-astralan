import discord
from discord.ext import commands

ROLES = {
    "🎉 | Giveaway Alerts": {"id": 1544020602795462758, "emoji": "🎉"},
    "🍿 | Movie Nights": {"id": 1544020705728008323, "emoji": "🍿"},
    "📢 | Update Ping": {"id": 1544020788993065012, "emoji": "📢"},
    "💬 | Active Chatter": {"id": 1544020861814571184, "emoji": "💬"},
    "🔊 | VC Ping": {"id": 1544021003749953609, "emoji": "🔊"}
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
            placeholder="🔔 Pilih notification & ping roles kamu...",
            min_values=1,
            max_values=len(options),
            options=options,
            custom_id="pingroles_select"
        )

    async def callback(self, interaction: discord.Interaction):
        added = []
        removed = []

        selected_role_ids = [int(v) for v in self.values]

        for name, data in ROLES.items():
            role = interaction.guild.get_role(data["id"])
            if not role:
                continue

            if role.id in selected_role_ids:
                if role not in interaction.user.roles:
                    await interaction.user.add_roles(role)
                    added.append(role.name)
            else:
                if role in interaction.user.roles:
                    await interaction.user.remove_roles(role)
                    removed.append(role.name)

        msg = ""

        if added:
            msg += "**Diambil:** " + ", ".join(added) + "\n"
        if removed:
            msg += "**Dilepas:** " + ", ".join(removed)

        if not msg:
            msg = "Role kamu sudah sesuai!"

        await interaction.response.send_message(msg, ephemeral=True)


class RoleView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(RoleSelect())


class PingRoles(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="setup_pingroles")
    @commands.has_permissions(administrator=True)
    async def setup_pingroles(self, ctx):
        embed = discord.Embed(
            title="Notification & Ping Roles Panel",
            description="Pilih role notifikasi yang kamu inginkan di bawah ini.\n(Bisa memilih lebih dari satu role sekaligus).",
            color=discord.Color.gold()
        )

        file = discord.File("banner_pingroles.png", filename="pingroles.png")
        embed.set_image(url="attachment://pingroles.png")

        embed.add_field(
            name="Available Ping Roles",
            value="\n".join(
                [f"{name}" for name, data in ROLES.items()]
            ),
            inline=False
        )

        await ctx.send(embed=embed, view=RoleView(), file=file)


async def setup(bot):
    await bot.add_cog(PingRoles(bot))