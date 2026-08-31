import discord
from discord.ext import commands

ROLES = {
    "21+ Tahun": {"id": 1544007923926310983, "emoji": "🧔"},
    "18 - 21 Tahun": {"id": 1544008158102556743, "emoji": "👱"},
    "13 - 17 Tahun": {"id": 1544008353951252610, "emoji": "👦"}
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
            placeholder="✨ Pilih kategori umur kamu...",
            min_values=1,
            max_values=1,
            options=options,
            custom_id="age_select"
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


class Agerole(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="setup_age")
    @commands.has_permissions(administrator=True)
    async def setup_age(self, ctx):
        embed = discord.Embed(
            title="Age Roles Panel",
            description="Pilih kategori umur kamu di bawah.\n(Hanya bisa memilih satu role, otomatis mengganti role lama jika ada).",
            color=discord.Color.blue()
        )

        file = discord.File("banner_age.png", filename="age.png")   
        embed.set_image(url="attachment://age.png")

        embed.add_field(
            name="Available Roles",
            value="\n".join(
                [f"{data['emoji']} : {name}" for name, data in ROLES.items()]
            ),
            inline=False
        )

        await ctx.send(embed=embed, view=RoleView(), file=file)


async def setup(bot):
    await bot.add_cog(Agerole(bot))