import discord
from discord.ext import commands


# ============================================================
# CONFIG
# ============================================================

GENDER_ROLES = {
    "Nova Girl": {
        "id": 1496850364446675105,
        "emoji": "🎀",
        "requires_verification": True
    },

    "Nova Boy": {
        "id": 1496850494814163086,
        "emoji": "💫",
        "requires_verification": False
    }
}


# ============================================================
# VERIFICATION VOICE
# ============================================================

# ID VC khusus untuk verifikasi
VERIFICATION_VOICE_CHANNEL_ID = 1539846749475049483


# ============================================================
# GENDER SELECT
# ============================================================

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
            max_values=1,
            options=options,
            custom_id="gender_select"
        )

    # ========================================================
    # CALLBACK
    # ========================================================

    async def callback(
        self,
        interaction: discord.Interaction
    ):

        selected_role_id = int(
            self.values[0]
        )

        selected_role = interaction.guild.get_role(
            selected_role_id
        )

        if selected_role is None:

            await interaction.response.send_message(
                "❌ Role tidak ditemukan. "
                "Silakan hubungi staff.",
                ephemeral=True
            )

            return

        # Ambil data role yang dipilih
        selected_data = None

        for name, data in GENDER_ROLES.items():

            if data["id"] == selected_role_id:

                selected_data = {
                    "name": name,
                    **data
                }

                break

        if selected_data is None:

            await interaction.response.send_message(
                "❌ Terjadi kesalahan pada konfigurasi role.",
                ephemeral=True
            )

            return

        # ====================================================
        # HAPUS GENDER ROLE LAIN
        # ====================================================

        removed_roles = []

        for role_data in GENDER_ROLES.values():

            role = interaction.guild.get_role(
                role_data["id"]
            )

            if (
                role
                and role in interaction.user.roles
                and role.id != selected_role_id
            ):

                try:

                    await interaction.user.remove_roles(
                        role,
                        reason="Astralan Gender Role Update"
                    )

                    removed_roles.append(
                        role.name
                    )

                except discord.Forbidden:

                    await interaction.response.send_message(
                        "❌ Bot tidak memiliki permission "
                        "untuk mengatur gender role.",
                        ephemeral=True
                    )

                    return

        # ====================================================
        # NOVA GIRL
        # ====================================================

        if selected_data["requires_verification"]:

            # Jangan langsung kasih Nova Girl
            #
            # Kalau user sudah punya Nova Girl,
            # tidak perlu melakukan apa-apa.
            if selected_role in interaction.user.roles:

                await interaction.response.send_message(
                    "🎀 Kamu sudah memiliki role "
                    f"**{selected_role.name}**.",
                    ephemeral=True
                )

                return

            # -----------------------------------------------
            # AMBIL VC VERIFICATION
            # -----------------------------------------------

            verification_channel = interaction.guild.get_channel(
                VERIFICATION_VOICE_CHANNEL_ID
            )

            if verification_channel:

                voice_mention = verification_channel.mention

            else:

                voice_mention = (
                    "**Verification Voice**"
                )

            # -----------------------------------------------
            # REMINDER EMBED
            # -----------------------------------------------

            embed = discord.Embed(
                title="🎀 Nova Girl Verification",
                description=(
                    "Untuk mendapatkan role "
                    f"**{selected_role.name}**, kamu perlu "
                    "melakukan verifikasi terlebih dahulu.\n\n"

                    f"🔊 **Silakan masuk ke {voice_mention}**\n\n"

                    "Setelah kamu masuk, staff Astralan akan "
                    "menerima notifikasi dan melakukan "
                    "verifikasi.\n\n"

                    "✨ Setelah verifikasi berhasil, "
                    "role **Nova Girl** akan diberikan "
                    "oleh sistem."
                ),
                color=discord.Color.from_rgb(
                    255,
                    105,
                    180
                )
            )

            embed.set_thumbnail(
                url=interaction.user.display_avatar.url
            )

            embed.set_footer(
                text="Astralan Verification System"
            )

            await interaction.response.send_message(
                embed=embed,
                ephemeral=True
            )

            return

        # ====================================================
        # NOVA BOY
        # ====================================================

        if selected_role not in interaction.user.roles:

            try:

                await interaction.user.add_roles(
                    selected_role,
                    reason="Astralan Gender Role Selection"
                )

            except discord.Forbidden:

                await interaction.response.send_message(
                    "❌ Bot tidak memiliki permission "
                    "untuk memberikan role.",
                    ephemeral=True
                )

                return

            embed = discord.Embed(
                description=(
                    f"Berhasil mendapatkan role "
                    f"**{selected_role.name}** {selected_data['emoji']}"
                ),
                color=discord.Color.from_rgb(
                    186,
                    104,
                    200
                )
            )

            await interaction.response.send_message(
                embed=embed,
                ephemeral=True
            )

        else:

            await interaction.response.send_message(
                f"✨ Kamu sudah memiliki role "
                f"**{selected_role.name}**.",
                ephemeral=True
            )


# ============================================================
# GENDER VIEW
# ============================================================

class GenderView(discord.ui.View):

    def __init__(self):

        super().__init__(
            timeout=None
        )

        self.add_item(
            GenderSelect()
        )


# ============================================================
# GENDER ROLE COG
# ============================================================

class GenderRole(commands.Cog):

    def __init__(self, bot):

        self.bot = bot

        # Persistent View
        self.bot.add_view(
            GenderView()
        )

    # ========================================================
    # SETUP GENDER PANEL
    # ========================================================

    @commands.command(
        name="setup_gender"
    )
    @commands.has_permissions(
        administrator=True
    )
    async def setup_gender(
        self,
        ctx: commands.Context
    ):

        embed = discord.Embed(
            title="Gender Roles Panel",
            description=(
                "Pilih satu gender role.\n"
                "Memilih ulang akan mengganti role."
            ),
            color=discord.Color.pink()
        )

        file = discord.File(
            "banner_gender.png",
            filename="gender.png"
        )

        embed.set_image(
            url="attachment://gender.png"
        )

        embed.add_field(
            name="Available Roles",
            value="\n".join(
                [
                    f"{data['emoji']} {name}"
                    for name, data in GENDER_ROLES.items()
                ]
            ),
            inline=False
        )

        await ctx.send(
            embed=embed,
            view=GenderView(),
            file=file
        )


# ============================================================
# SETUP
# ============================================================

async def setup(bot):

    await bot.add_cog(
        GenderRole(bot)
    )