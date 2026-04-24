import discord
from discord.ext import commands

GENDER_ROLES = {
    "Nova Girl": {"id": 1496850364446675105, "emoji": "🎀"},
    "Nova Boy": {"id": 1496850494814163086, "emoji": "💫"}
}


class GenderSelect(discord.ui.Select):
    def __init__(self):
        options = []

        for name, data in GENDER_ROLES.items():
            options.append(
                discord.SelectOption(
                    label=name,
                    value=str(data["id"]),
                    emoji=data["emoji"]
                )
            )

        super().__init__(
            placeholder="⚧️ Pilih gender role kamu...",
            min_values=1,
            max_values=1,  # cuma boleh pilih satu
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        selected_role_id = int(self.values[0])
        selected_role = interaction.guild.get_role(selected_role_id)

        removed_roles = []

        # Hapus semua gender role lain dulu
        for role_data in GENDER_ROLES.values():
            role = interaction.guild.get_role(role_data["id"])
            if role in interaction.user.roles and role.id != selected_role_id:
                await interaction.user.remove_roles(role)
                removed_roles.append(role.name)

        # Tambahin role baru kalau belum punya
        if selected_role not in interaction.user.roles:
            await interaction.user.add_roles(selected_role)
            msg = f"Role **{selected_role.name}** diambil"
        else:
            msg = f"Kamu sudah punya role **{selected_role.name}**"

        await interaction.response.send_message(msg, ephemeral=True)


class GenderView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(GenderSelect())


class GenderRole(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="setup_gender")
    async def setup_gender(self, ctx):
        embed = discord.Embed(
            title="Gender Roles Panel",
            description="Pilih satu gender role.\nMemilih ulang akan mengganti role.",
            color=discord.Color.pink()
        )

        file = discord.File("banner_gender.png", filename="gender.png")
        embed.set_image(url="attachment://gender.png")

        embed.add_field(
            name="Available Roles",
            value="\n".join(
                [f"{data['emoji']} {name}" for name, data in GENDER_ROLES.items()]
            ),
            inline=False
        )

        await ctx.send(embed=embed, view=GenderView(), file=file)


async def setup(bot):
    await bot.add_cog(GenderRole(bot))