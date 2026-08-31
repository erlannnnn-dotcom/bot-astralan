import discord
from discord.ext import commands
import re


# =========================================================
# CONFIG
# =========================================================

# Ganti dengan ID bot "AST Arcane" yang tampil di server kamu
ARCANE_BOT_ID = 1496893755909734560  # <- Sesuaikan dengan ID asli bot Arcane

# Channel tempat Arcane mengirim log level
ARCANE_LOG_CHANNEL_ID = 1496893755909734560

# Channel tempat bot AST mengirim notifikasi
LEVEL_NOTIFICATION_CHANNEL_ID = 1496893755909734560


# =========================================================
# ROLE LEVEL AST
# =========================================================

LEVEL_ROLES = {
    10: 1539868313717309462,  # AST Newcomer
    20: 1539868536657289237,  # AST Active
    35: 1539868642840154162,  # AST Expert
    75: 1539868797236940841,  # AST Legend
}

LEVEL_ROLE_NAMES = {
    10: "AST Newcomer",
    20: "AST Active",
    35: "AST Expert",
    75: "AST Legend",
}


# =========================================================
# COG
# =========================================================

class ASTLevel(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):

        # Harus berasal dari channel log Arcane
        if message.channel.id != ARCANE_LOG_CHANNEL_ID:
            return

        # Harus berasal dari Arcane
        if message.author.id != ARCANE_BOT_ID:
            return

        # Ambil teks dari message.content (karena format Arcane di gambar adalah teks biasa)
        text = message.content
        if not text and message.embeds:
            # Fallback jika suatu saat pakai embed
            text_parts = [emb.description for emb in message.embeds if emb.description]
            text = " ".join(text_parts)

        # =================================================
        # DETECT LEVEL (Disesuaikan dengan format gambar)
        # =================================================
        # Contoh teks: "@finn telah mencapai level 8. Letsgoww..."
        level_match = re.search(
            r"level\D*(\d+)",
            text,
            re.IGNORECASE
        )

        if not level_match:
            return

        level = int(level_match.group(1))

        # =================================================
        # TENTUKAN ROLE TERTINGGI
        # =================================================
        available_levels = [
            lvl for lvl in LEVEL_ROLES
            if level >= lvl
        ]

        if not available_levels:
            return

        target_level = max(available_levels)
        target_role_id = LEVEL_ROLES[target_level]

        guild = message.guild
        if guild is None:
            return

        target_role = guild.get_role(target_role_id)
        if target_role is None:
            print(f"[AST LEVEL] Role ID {target_role_id} tidak ditemukan.")
            return

        # =================================================
        # CARI MEMBER
        # =================================================
        member = None
        if message.mentions:
            for mentioned_member in message.mentions:
                if not mentioned_member.bot:
                    member = mentioned_member
                    break

        if member is None:
            return

        # =================================================
        # CEK LEVEL ROLE MEMBER SEKARANG
        # =================================================
        current_level = 0
        for lvl, role_id in LEVEL_ROLES.items():
            role = guild.get_role(role_id)
            if role and role in member.roles:
                current_level = max(current_level, lvl)

        if current_level >= target_level:
            return

        # =================================================
        # HAPUS ROLE LEVEL SEBELUMNYA
        # =================================================
        old_roles = []
        for lvl, role_id in LEVEL_ROLES.items():
            if lvl == target_level:
                continue
            role = guild.get_role(role_id)
            if role and role in member.roles:
                old_roles.append(role)

        if old_roles:
            try:
                await member.remove_roles(*old_roles, reason="AST Level Role Upgrade")
            except discord.Forbidden:
                print(f"[AST LEVEL] Tidak bisa menghapus role lama dari {member}.")

        # =================================================
        # BERIKAN ROLE BARU
        # =================================================
        try:
            await member.add_roles(target_role, reason=f"AST Level {target_level}")
        except discord.Forbidden:
            print(f"[AST LEVEL] Tidak bisa memberikan {target_role.name} kepada {member}.")
            return

        # =================================================
        # NOTIFICATION
        # =================================================
        notification_channel = guild.get_channel(LEVEL_NOTIFICATION_CHANNEL_ID)
        if notification_channel is None:
            return

        embed = discord.Embed(
            title="✨ Level Up!",
            description=(
                f"Selamat {member.mention}!\n\n"
                f"Kamu telah mencapai **Level {level}** "
                f"dan mendapatkan role **{target_role.name}** 🎉"
            ),
            color=discord.Color.from_rgb(186, 104, 200)
        )

        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="Level", value=f"**{level}**", inline=True)
        embed.add_field(name="New Role", value=target_role.mention, inline=True)
        embed.set_footer(text="Astralan Level System")

        await notification_channel.send(embed=embed)

        print(f"[AST LEVEL] {member} → Level {level} → {target_role.name}")


async def setup(bot):
    await bot.add_cog(ASTLevel(bot))