import discord
from discord.ext import commands
from discord.ui import View, Button


# ============================================================
# ASTRALAN VERIFICATION SYSTEM
# ============================================================

# ============================================================
# CONFIG
# ============================================================

# ID VOICE CHANNEL KHUSUS VERIFIKASI
VERIFICATION_VOICE_CHANNEL_ID = 1539846749475049483

# ID CHANNEL NOTIF STAFF
NOTIFICATION_CHANNEL_ID = 1539847239722213467

# ID CHANNEL LOG VERIFIKASI
LOG_CHANNEL_ID = 1539849869051826197

# ID ROLE STAFF YANG AKAN DI-MENTION
# Contoh: Guardian + Overseer
STAFF_ROLE_IDS = [
    1496846251914956820,  # Guardian
    1496845677764804738,  # Overseer
]

# ID ROLE YANG DIBERIKAN SETELAH VERIFIED
VERIFIED_ROLE_ID = 1496850364446675105


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def get_role(
    guild: discord.Guild,
    role_id: int
):
    return guild.get_role(role_id)


def get_channel(
    guild: discord.Guild,
    channel_id: int
):
    return guild.get_channel(channel_id)


def is_staff(member: discord.Member) -> bool:
    """
    Mengecek apakah member memiliki salah satu
    role staff yang sudah ditentukan.
    """

    return any(
        role.id in STAFF_ROLE_IDS
        for role in member.roles
    )


# ============================================================
# VERIFICATION VIEW
# ============================================================

class VerificationView(View):

    def __init__(
        self,
        cog,
        member_id: int
    ):
        # timeout=None = tombol tidak expire
        super().__init__(timeout=None)

        self.cog = cog
        self.member_id = member_id

    # ========================================================
    # STAFF PERMISSION CHECK
    # ========================================================

    async def interaction_check(
        self,
        interaction: discord.Interaction
    ):

        if not isinstance(
            interaction.user,
            discord.Member
        ):
            return False

        # Hanya staff yang bisa menggunakan button
        if not is_staff(interaction.user):

            await interaction.response.send_message(
                "❌ Kamu tidak memiliki izin untuk "
                "memproses verification ini.",
                ephemeral=True
            )

            return False

        return True

    # ========================================================
    # VERIFY BUTTON
    # ========================================================

    @discord.ui.button(
        label="Verify",
        emoji="🟢",
        style=discord.ButtonStyle.success,
        custom_id="astralan_verification_verify"
    )
    async def verify_button(
        self,
        interaction: discord.Interaction,
        button: Button
    ):

        guild = interaction.guild

        if guild is None:
            return

        # ----------------------------------------------------
        # CEK REQUEST
        # ----------------------------------------------------

        if self.member_id not in self.cog.pending_requests:

            await interaction.response.send_message(
                "⚠️ Verification request ini sudah "
                "tidak aktif atau sudah diproses.",
                ephemeral=True
            )

            return

        # ----------------------------------------------------
        # GET MEMBER
        # ----------------------------------------------------

        member = guild.get_member(
            self.member_id
        )

        if member is None:

            await interaction.response.send_message(
                "❌ Member tersebut sudah tidak berada "
                "di server.",
                ephemeral=True
            )

            self.cog.remove_request(
                self.member_id
            )

            return

        # ----------------------------------------------------
        # GET VERIFIED ROLE
        # ----------------------------------------------------

        verified_role = get_role(
            guild,
            VERIFIED_ROLE_ID
        )

        if verified_role is None:

            await interaction.response.send_message(
                "❌ Role Verified tidak ditemukan.\n"
                "Periksa `VERIFIED_ROLE_ID`.",
                ephemeral=True
            )

            return

        # ----------------------------------------------------
        # CEK SUDAH VERIFIED
        # ----------------------------------------------------

        if verified_role in member.roles:

            await interaction.response.send_message(
                "ℹ️ Member ini sudah memiliki "
                "role Verified.",
                ephemeral=True
            )

            self.cog.remove_request(
                self.member_id
            )

            return

        # ----------------------------------------------------
        # GIVE ROLE
        # ----------------------------------------------------

        try:

            await member.add_roles(
                verified_role,
                reason=(
                    f"Astralan Verification | "
                    f"Verified by {interaction.user} "
                    f"({interaction.user.id})"
                )
            )

        except discord.Forbidden:

            await interaction.response.send_message(
                "❌ Bot tidak memiliki permission "
                "untuk memberikan role.\n\n"
                "Pastikan role bot berada di atas "
                "role Verified.",
                ephemeral=True
            )

            return

        except discord.HTTPException:

            await interaction.response.send_message(
                "❌ Terjadi error Discord saat "
                "memberikan role.",
                ephemeral=True
            )

            return

        # ----------------------------------------------------
        # REMOVE REQUEST
        # ----------------------------------------------------

        self.cog.remove_request(
            self.member_id
        )

        # ----------------------------------------------------
        # DISABLE BUTTON
        # ----------------------------------------------------

        for item in self.children:
            item.disabled = True

        # ----------------------------------------------------
        # UPDATE EMBED
        # ----------------------------------------------------

        if interaction.message.embeds:

            embed = interaction.message.embeds[0].copy()

        else:

            embed = discord.Embed(
                title="Verification Request"
            )

        embed.color = discord.Color.green()

        embed.add_field(
            name="🟢 Status",
            value=(
                f"Verified by "
                f"{interaction.user.mention}"
            ),
            inline=False
        )

        embed.set_footer(
            text="Astralan Verification System • VERIFIED"
        )

        await interaction.response.edit_message(
            embed=embed,
            view=self
        )

        # ----------------------------------------------------
        # SEND LOG
        # ----------------------------------------------------

        await self.cog.send_log(
            guild=guild,
            member=member,
            staff=interaction.user,
            action="VERIFIED"
        )

    # ========================================================
    # REJECT BUTTON
    # ========================================================

    @discord.ui.button(
        label="Reject",
        emoji="🔴",
        style=discord.ButtonStyle.danger,
        custom_id="astralan_verification_reject"
    )
    async def reject_button(
        self,
        interaction: discord.Interaction,
        button: Button
    ):

        guild = interaction.guild

        if guild is None:
            return

        # ----------------------------------------------------
        # CEK REQUEST
        # ----------------------------------------------------

        if self.member_id not in self.cog.pending_requests:

            await interaction.response.send_message(
                "⚠️ Verification request ini sudah "
                "tidak aktif atau sudah diproses.",
                ephemeral=True
            )

            return

        # ----------------------------------------------------
        # GET MEMBER
        # ----------------------------------------------------

        member = guild.get_member(
            self.member_id
        )

        # ----------------------------------------------------
        # REMOVE REQUEST
        # ----------------------------------------------------

        self.cog.remove_request(
            self.member_id
        )

        # ----------------------------------------------------
        # DISABLE BUTTON
        # ----------------------------------------------------

        for item in self.children:
            item.disabled = True

        # ----------------------------------------------------
        # UPDATE EMBED
        # ----------------------------------------------------

        if interaction.message.embeds:

            embed = interaction.message.embeds[0].copy()

        else:

            embed = discord.Embed(
                title="Verification Request"
            )

        embed.color = discord.Color.red()

        embed.add_field(
            name="🔴 Status",
            value=(
                f"Rejected by "
                f"{interaction.user.mention}"
            ),
            inline=False
        )

        embed.set_footer(
            text="Astralan Verification System • REJECTED"
        )

        await interaction.response.edit_message(
            embed=embed,
            view=self
        )

        # ----------------------------------------------------
        # SEND LOG
        # ----------------------------------------------------

        if member:

            await self.cog.send_log(
                guild=guild,
                member=member,
                staff=interaction.user,
                action="REJECTED"
            )


# ============================================================
# MAIN COG
# ============================================================

class Verification(commands.Cog):

    def __init__(self, bot):

        self.bot = bot

        # Menyimpan request yang sedang aktif.
        #
        # Format:
        #
        # {
        #     member_id: {
        #         "message_id": 123,
        #         "channel_id": 123,
        #         "voice_channel_id": 123
        #     }
        # }
        #
        self.pending_requests = {}

        # ====================================================
        # REGISTER PERSISTENT BUTTON
        # ====================================================

        self.bot.add_view(
            VerificationView(
                self,
                0
            )
        )

    # ========================================================
    # REMOVE REQUEST
    # ========================================================

    def remove_request(
        self,
        member_id: int
    ):

        self.pending_requests.pop(
            member_id,
            None
        )

    # ========================================================
    # VOICE JOIN DETECTION
    # ========================================================

    @commands.Cog.listener()
    async def on_voice_state_update(
        self,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState
    ):

        # ----------------------------------------------------
        # BOT DIABAIKAN
        # ----------------------------------------------------

        if member.bot:
            return

        # ----------------------------------------------------
        # HARUS JOIN VOICE
        # ----------------------------------------------------

        if after.channel is None:
            return

        # ----------------------------------------------------
        # HANYA VC KHUSUS VERIFIKASI
        # ----------------------------------------------------

        if after.channel.id != VERIFICATION_VOICE_CHANNEL_ID:
            return

        # ----------------------------------------------------
        # ABAIKAN PINDAH VC
        # ----------------------------------------------------

        if before.channel is not None:
            return

        # ----------------------------------------------------
        # CEK REQUEST AKTIF
        # ----------------------------------------------------

        if member.id in self.pending_requests:
            return

        # ----------------------------------------------------
        # CEK SUDAH VERIFIED
        # ----------------------------------------------------

        verified_role = get_role(
            member.guild,
            VERIFIED_ROLE_ID
        )

        if verified_role:

            if verified_role in member.roles:
                return

        # ----------------------------------------------------
        # GET NOTIFICATION CHANNEL
        # ----------------------------------------------------

        notification_channel = get_channel(
            member.guild,
            NOTIFICATION_CHANNEL_ID
        )

        if notification_channel is None:
            print(
                "[VERIFICATION] "
                "Notification channel tidak ditemukan."
            )

            return

        # ----------------------------------------------------
        # STAFF MENTION
        # ----------------------------------------------------

        staff_mentions = []

        for role_id in STAFF_ROLE_IDS:

            role = get_role(
                member.guild,
                role_id
            )

            if role:
                staff_mentions.append(
                    role.mention
                )

        mention_text = " ".join(
            staff_mentions
        )

        # ----------------------------------------------------
        # CREATE EMBED
        # ----------------------------------------------------

        embed = discord.Embed(
            title="🔔 New Verification Request",
            description=(
                f"{member.mention} telah memasuki "
                f"**Verification Voice**.\n\n"
                "Staff dipersilakan melakukan "
                "verifikasi terhadap member ini."
            ),
            color=discord.Color.from_rgb(
                186,
                104,
                200
            ),
            timestamp=discord.utils.utcnow()
        )

        embed.set_thumbnail(
            url=member.display_avatar.url
        )

        embed.add_field(
            name="👤 Member",
            value=(
                f"{member.mention}\n"
                f"`{member}`\n"
                f"`{member.id}`"
            ),
            inline=False
        )

        embed.add_field(
            name="🔊 Verification Room",
            value=after.channel.mention,
            inline=True
        )

        embed.add_field(
            name="📌 Status",
            value="🟡 Waiting for Staff",
            inline=True
        )

        embed.set_footer(
            text="Astralan Verification System"
        )

        # ----------------------------------------------------
        # CREATE BUTTON
        # ----------------------------------------------------

        view = VerificationView(
            self,
            member.id
        )

        # ----------------------------------------------------
        # SEND NOTIFICATION
        # ----------------------------------------------------

        try:

            message = await notification_channel.send(
                content=mention_text,
                embed=embed,
                view=view,
                allowed_mentions=discord.AllowedMentions(
                    roles=True,
                    users=True
                )
            )

        except discord.Forbidden:

            print(
                "[VERIFICATION] "
                "Bot tidak memiliki permission "
                "untuk mengirim pesan."
            )

            return

        except discord.HTTPException as error:

            print(
                f"[VERIFICATION] Discord error: {error}"
            )

            return

        # ----------------------------------------------------
        # SAVE REQUEST
        # ----------------------------------------------------

        self.pending_requests[
            member.id
        ] = {
            "message_id": message.id,
            "channel_id": notification_channel.id,
            "voice_channel_id": after.channel.id,
            "created_at": discord.utils.utcnow()
        }

        print(
            f"[VERIFICATION] "
            f"Request dibuat untuk {member} "
            f"({member.id})"
        )

    # ========================================================
    # LOG SYSTEM
    # ========================================================

    async def send_log(
        self,
        guild: discord.Guild,
        member: discord.Member,
        staff: discord.Member,
        action: str
    ):

        log_channel = get_channel(
            guild,
            LOG_CHANNEL_ID
        )

        if log_channel is None:
            print(
                "[VERIFICATION] "
                "Log channel tidak ditemukan."
            )

            return

        # ----------------------------------------------------
        # ACTION STYLE
        # ----------------------------------------------------

        if action == "VERIFIED":

            color = discord.Color.green()
            title = "🟢 Member Verified"

        else:

            color = discord.Color.red()
            title = "🔴 Verification Rejected"

        # ----------------------------------------------------
        # CREATE LOG EMBED
        # ----------------------------------------------------

        embed = discord.Embed(
            title=title,
            color=color,
            timestamp=discord.utils.utcnow()
        )

        embed.set_thumbnail(
            url=member.display_avatar.url
        )

        embed.add_field(
            name="👤 Member",
            value=(
                f"{member.mention}\n"
                f"`{member}`\n"
                f"`{member.id}`"
            ),
            inline=False
        )

        embed.add_field(
            name="🛡️ Staff",
            value=(
                f"{staff.mention}\n"
                f"`{staff}`"
            ),
            inline=True
        )

        embed.add_field(
            name="📌 Action",
            value=action,
            inline=True
        )

        embed.set_footer(
            text="Astralan Verification Logs"
        )

        try:

            await log_channel.send(
                embed=embed
            )

        except discord.HTTPException as error:

            print(
                f"[VERIFICATION LOG] "
                f"Error: {error}"
            )

    # ========================================================
    # TEST COMMAND
    # ========================================================

    @commands.command(
        name="test_verification"
    )
    @commands.has_permissions(
        administrator=True
    )
    async def test_verification(
        self,
        ctx: commands.Context
    ):

        notification_channel = get_channel(
            ctx.guild,
            NOTIFICATION_CHANNEL_ID
        )

        if notification_channel is None:

            await ctx.send(
                "❌ Notification channel tidak ditemukan."
            )

            return

        embed = discord.Embed(
            title="🧪 Test Verification Request",
            description=(
                "Ini adalah test dari "
                "Astralan Verification System."
            ),
            color=discord.Color.from_rgb(
                186,
                104,
                200
            ),
            timestamp=discord.utils.utcnow()
        )

        embed.set_thumbnail(
            url=ctx.author.display_avatar.url
        )

        embed.add_field(
            name="👤 Member",
            value=ctx.author.mention,
            inline=False
        )

        embed.add_field(
            name="📌 Status",
            value="🟡 Test Request",
            inline=True
        )

        embed.set_footer(
            text="Astralan Verification System • TEST"
        )

        view = VerificationView(
            self,
            ctx.author.id
        )

        await notification_channel.send(
            embed=embed,
            view=view
        )

        await ctx.send(
            "✅ Test verification berhasil dikirim."
        )


# ============================================================
# ERROR HANDLER
# ============================================================

async def setup(bot):

    await bot.add_cog(
        Verification(bot)
    )