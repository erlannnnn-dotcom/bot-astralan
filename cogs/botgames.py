import discord
from discord.ext import commands

ROLES = {
    "OwO": {"id": 1544016021193494568, "emoji": "💸"},
    "UwU": {"id": 1544016918086942760, "emoji": "🌸"}
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
            placeholder="🎮 Pilih role bot games kamu...",
            min_values=1,
            max_values=1,
            options=options,
            custom_id="botgames_role_select"
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


class BotGames(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="setup_botgames")
    @commands.has_permissions(administrator=True)
    async def setup_botgames(self, ctx):
        embed = discord.Embed(
            title="Bot Games Roles Panel",
            description="Pilih role bot games kamu di bawah ini.\n(Hanya bisa memilih satu role, otomatis mengganti role lama jika ada).",
            color=discord.Color.green()
        )

        file = discord.File("banner_botgames.png", filename="botgames.png")
        embed.set_image(url="attachment://botgames.png")

        embed.add_field(
            name="Available Roles",
            value="\n".join(
                [f"{data['emoji']} : {name}" for name, data in ROLES.items()]
            ),
            inline=False
        )

        await ctx.send(embed=embed, view=RoleView(), file=file)


async def setup(bot):
    await bot.add_cog(BotGames(bot))