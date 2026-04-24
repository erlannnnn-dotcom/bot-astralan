import discord
from discord.ext import commands

# ================= CONFIG =================
CATEGORY_ID = 1497284211839729856  # ganti
STAFF_ROLE_ID = 1496845677764804738  # ganti
# =========================================

# ======== WARNA PER KATEGORI ========
COLORS = {
    "Keluhan": discord.Color.orange(),
    "Report": discord.Color.red(),
    "Donate": discord.Color.green(),
    "Partnership": discord.Color.blue()
}


# ======== MODAL (PERTANYAAN) ========
class TicketModal(discord.ui.Modal):
    def __init__(self, category_name):
        super().__init__(title=f"{category_name} Ticket")
        self.category_name = category_name

        # ===== KELUHAN =====
        if category_name == "Keluhan":
            self.q1 = discord.ui.TextInput(label="Apa yang terjadi?", style=discord.TextStyle.paragraph)
            self.q2 = discord.ui.TextInput(label="Kapan kejadian ini?", required=False)
            self.q3 = discord.ui.TextInput(label="Siapa yang terlibat?", required=False)

        # ===== REPORT =====
        elif category_name == "Report":
            self.q1 = discord.ui.TextInput(label="Siapa yang kamu laporkan?")
            self.q2 = discord.ui.TextInput(label="Apa pelanggarannya?", style=discord.TextStyle.paragraph)
            self.q3 = discord.ui.TextInput(label="Bukti (link/screenshot)", required=False)

        # ===== DONATE =====
        elif category_name == "Donate":
            self.q1 = discord.ui.TextInput(label="Tujuan donasi kamu?")
            self.q2 = discord.ui.TextInput(label="Metode pembayaran (opsional)", required=False)
            self.q3 = None

        # ===== PARTNERSHIP =====
        elif category_name == "Partnership":
            self.q1 = discord.ui.TextInput(label="Nama server / komunitas")
            self.q2 = discord.ui.TextInput(label="Tujuan kerja sama", style=discord.TextStyle.paragraph)
            self.q3 = discord.ui.TextInput(label="Link / info tambahan", required=False)

        self.add_item(self.q1)
        self.add_item(self.q2)
        if self.q3:
            self.add_item(self.q3)

    async def on_submit(self, interaction: discord.Interaction):
        guild = interaction.guild

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.get_role(STAFF_ROLE_ID): discord.PermissionOverwrite(read_messages=True)
        }

        channel = await guild.create_text_channel(
            name=f"{self.category_name.lower()}-{interaction.user.name}",
            category=guild.get_channel(CATEGORY_ID),
            overwrites=overwrites
        )

        embed = discord.Embed(
            title=f"🌌 Astral Ticket — {self.category_name}",
            color=COLORS[self.category_name]
        )

        # masukin jawaban ke embed
        for item in self.children:
            embed.add_field(
                name=item.label,
                value=item.value if item.value else "-",
                inline=False
            )

        await channel.send(
            content=f"{interaction.user.mention} | <@&{STAFF_ROLE_ID}>",
            embed=embed,
            view=DecisionView(interaction.user)
        )

        await interaction.response.send_message(
            f"Ticket kamu sudah dibuat: {channel.mention}",
            ephemeral=True
        )


# ======== DECISION BUTTON (STAFF ONLY) ========
class DecisionView(discord.ui.View):
    def __init__(self, user):
        super().__init__(timeout=None)
        self.user = user

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if discord.utils.get(interaction.user.roles, id=STAFF_ROLE_ID):
            return True

        await interaction.response.send_message(
            "Kamu tidak punya akses untuk tombol ini.",
            ephemeral=True
        )
        return False

    @discord.ui.button(label="Accept", style=discord.ButtonStyle.success)
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            "Ticket diterima. Silakan lanjutkan diskusi.",
            ephemeral=True
        )

        for item in self.children:
            item.disabled = True

        await interaction.message.edit(view=self)

    @discord.ui.button(label="Reject", style=discord.ButtonStyle.danger)
    async def reject(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            "Ticket ditolak & channel akan dihapus...",
            ephemeral=True
        )

        await interaction.channel.delete()


# ======== PANEL BUTTON ========
class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Keluhan", style=discord.ButtonStyle.primary)
    async def keluhan(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(TicketModal("Keluhan"))

    @discord.ui.button(label="Report", style=discord.ButtonStyle.danger)
    async def report(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(TicketModal("Report"))

    @discord.ui.button(label="Donate", style=discord.ButtonStyle.success)
    async def donate(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(TicketModal("Donate"))

    @discord.ui.button(label="Partnership", style=discord.ButtonStyle.secondary)
    async def partner(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(TicketModal("Partnership"))


# ======== COG ========
class Ticket(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="setup_ticket")
    async def setup_ticket(self, ctx):
        embed = discord.Embed(
            title="Astral Support Gateway",
            description=(
                "Pilih kategori yang sesuai dengan kebutuhan kamu.\n\n"

                "🔥 **Keluhan**: Laporkan pengalaman tidak nyaman dalam server.\n\n"

                "⚠️ **Report**: Laporkan pelanggaran aturan.\n\n"

                "💠 **Donate**: Dukungan atau kontribusi ke server.\n\n"

                "🤝 **Partnership**: Ajukan kerja sama komunitas.\n\n"

                "Semua ticket bersifat privat dan hanya bisa dilihat oleh kamu & staff."
            ),
            color=discord.Color.from_rgb(140, 82, 255)
        )

        await ctx.send(embed=embed, view=TicketView())


async def setup(bot):
    await bot.add_cog(Ticket(bot))