import discord
from discord.ext import commands
from discord import app_commands

import sqlite3
import random
from datetime import datetime, timedelta
from pathlib import Path


# =========================================================
# CONFIG
# =========================================================

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "afk.db"

# WIB = UTC + 7
WIB = timedelta(hours=7)


# =========================================================
# INTERNAL SERVER EMOJIS
# =========================================================

ARROW_BLUE = "<a:arrowblue:1555096801629970523>"
LAMP_PURPLE = "<a:lampuungu:1555112848131104859>"
FLOWER_PURPLE = "<a:bungaungu:1555113270443253791>"


# =========================================================
# AFK COG
# =========================================================

class AFK(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

        # Cache AFK di RAM
        self.afk_users = {}

        # Buat database otomatis
        self.init_database()

        # Load data AFK dari database
        self.load_afk_data()

    # =====================================================
    # TIME
    # =====================================================

    def now_wib(self):
        """
        Mengambil waktu sekarang dalam WIB.
        """
        return datetime.utcnow() + WIB

    # =====================================================
    # DATABASE
    # =====================================================

    def get_connection(self):
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn

    def init_database(self):
        """
        Membuat database dan tabel AFK otomatis.
        """

        DB_PATH.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        conn = self.get_connection()

        try:
            cursor = conn.cursor()

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS afk_users (
                    user_id INTEGER NOT NULL,
                    guild_id INTEGER NOT NULL,
                    reason TEXT NOT NULL DEFAULT 'AFK',
                    since TEXT NOT NULL,

                    PRIMARY KEY (user_id, guild_id)
                )
            """)

            conn.commit()

        finally:
            conn.close()

    def load_afk_data(self):
        """
        Memuat data AFK dari database ketika cog
        pertama kali dijalankan.
        """

        self.afk_users.clear()

        conn = self.get_connection()

        try:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT
                    user_id,
                    guild_id,
                    reason,
                    since
                FROM afk_users
            """)

            rows = cursor.fetchall()

            for row in rows:

                try:
                    since = datetime.fromisoformat(
                        row["since"]
                    )

                    self.afk_users[
                        (
                            row["guild_id"],
                            row["user_id"]
                        )
                    ] = {
                        "reason": row["reason"],
                        "since": since
                    }

                except Exception:
                    continue

        finally:
            conn.close()

    def save_afk(
        self,
        guild_id: int,
        user_id: int,
        reason: str,
        since: datetime
    ):
        """
        Simpan / update status AFK.
        """

        conn = self.get_connection()

        try:
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO afk_users (
                    user_id,
                    guild_id,
                    reason,
                    since
                )
                VALUES (?, ?, ?, ?)

                ON CONFLICT(user_id, guild_id)
                DO UPDATE SET
                    reason = excluded.reason,
                    since = excluded.since
            """, (
                user_id,
                guild_id,
                reason,
                since.isoformat()
            ))

            conn.commit()

        finally:
            conn.close()

    def remove_afk(
        self,
        guild_id: int,
        user_id: int
    ):
        """
        Hapus status AFK dari database.
        """

        conn = self.get_connection()

        try:
            cursor = conn.cursor()

            cursor.execute("""
                DELETE FROM afk_users
                WHERE user_id = ?
                AND guild_id = ?
            """, (
                user_id,
                guild_id
            ))

            conn.commit()

        finally:
            conn.close()

    # =====================================================
    # HELPER
    # =====================================================

    def random_color(self):
        return discord.Color(
            random.randint(
                0,
                0xFFFFFF
            )
        )

    def format_time(self, seconds):

        minutes, seconds = divmod(
            seconds,
            60
        )

        hours, minutes = divmod(
            minutes,
            60
        )

        days, hours = divmod(
            hours,
            24
        )

        if days > 0:
            return (
                f"{days} hari "
                f"{hours} jam"
            )

        elif hours > 0:
            return (
                f"{hours} jam "
                f"{minutes} menit"
            )

        elif minutes > 0:
            return (
                f"{minutes} menit "
                f"{seconds} detik"
            )

        else:
            return f"{seconds} detik"

    # =====================================================
    # /AFK
    # =====================================================

    @app_commands.command(
        name="afk",
        description="Set status AFK"
    )
    @app_commands.describe(
        reason="Alasan kamu AFK"
    )
    async def afk(
        self,
        interaction: discord.Interaction,
        reason: str = "AFK"
    ):

        user = interaction.user

        # Harus di server
        if interaction.guild is None:

            await interaction.response.send_message(
                f"{LAMP_PURPLE} Command ini hanya bisa digunakan di server.",
                ephemeral=True
            )

            return

        guild_id = interaction.guild.id
        user_id = user.id

        # Waktu WIB
        since = self.now_wib()

        # =================================================
        # SIMPAN DATABASE
        # =================================================

        self.save_afk(
            guild_id=guild_id,
            user_id=user_id,
            reason=reason,
            since=since
        )

        # =================================================
        # CACHE
        # =================================================

        self.afk_users[
            (
                guild_id,
                user_id
            )
        ] = {
            "reason": reason,
            "since": since
        }

        # =================================================
        # NICKNAME
        # =================================================

        try:

            current_name = user.display_name

            if current_name.startswith("[AFK] "):
                new_name = current_name

            else:
                new_name = (
                    f"[AFK] {current_name}"
                )

            await user.edit(
                nick=new_name
            )

        except discord.Forbidden:
            pass

        except discord.HTTPException:
            pass

        except Exception:
            pass

        # =================================================
        # EMBED
        # =================================================

        embed = discord.Embed(
            title=f"{LAMP_PURPLE} AFK Status Aktif",
            description=(
                f"{ARROW_BLUE} {user.mention} "
                f"telah mengaktifkan status AFK.\n\n"
                f"{FLOWER_PURPLE} **Alasan:** {reason}"
            ),
            color=self.random_color(),
            timestamp=since
        )

        embed.set_footer(
            text="Status akan otomatis nonaktif saat kamu kembali."
        )

        await interaction.response.send_message(
            embed=embed
        )

    # =====================================================
    # ON MESSAGE
    # =====================================================

    @commands.Cog.listener()
    async def on_message(
        self,
        message
    ):

        # Abaikan bot
        if message.author.bot:
            return

        # Abaikan DM
        if message.guild is None:
            return

        guild_id = message.guild.id
        author_id = message.author.id

        author_key = (
            guild_id,
            author_id
        )

        # =================================================
        # BALIK DARI AFK
        # =================================================

        if author_key in self.afk_users:

            data = self.afk_users.pop(
                author_key
            )

            # Hapus database
            self.remove_afk(
                guild_id=guild_id,
                user_id=author_id
            )

            # Hitung durasi
            afk_time = (
                self.now_wib() - data["since"]
            ).total_seconds()

            waktu = self.format_time(
                int(afk_time)
            )

            # =================================================
            # KEMBALIKAN NICKNAME
            # =================================================

            try:

                current_name = (
                    message.author.display_name
                )

                if current_name.startswith(
                    "[AFK] "
                ):

                    original_name = (
                        current_name[6:]
                    )

                    await message.author.edit(
                        nick=original_name
                    )

            except discord.Forbidden:
                pass

            except discord.HTTPException:
                pass

            except Exception:
                pass

            # =================================================
            # WELCOME BACK
            # =================================================

            embed = discord.Embed(
                title=f"{FLOWER_PURPLE} Welcome Back",
                description=(
                    f"{ARROW_BLUE} "
                    f"{message.author.mention} "
                    f"telah kembali.\n\n"
                    f"{LAMP_PURPLE} **Durasi AFK:** "
                    f"{waktu}"
                ),
                color=self.random_color(),
                timestamp=self.now_wib()
            )

            await message.channel.send(
                embed=embed
            )

        # =================================================
        # CEK MENTION
        # =================================================

        mentioned_users = set()

        for user in message.mentions:

            user_key = (
                guild_id,
                user.id
            )

            if user.id in mentioned_users:
                continue

            if user_key not in self.afk_users:
                continue

            mentioned_users.add(
                user.id
            )

            data = self.afk_users[
                user_key
            ]

            # =================================================
            # DURASI AFK
            # =================================================

            afk_time = (
                self.now_wib() - data["since"]
            ).total_seconds()

            waktu = self.format_time(
                int(afk_time)
            )

            # =================================================
            # AFK MENTION
            # =================================================

            embed = discord.Embed(
                title=f"{LAMP_PURPLE} Pengguna Sedang AFK",
                description=(
                    f"{ARROW_BLUE} "
                    f"{user.mention} "
                    f"saat ini sedang AFK.\n\n"
                    f"{FLOWER_PURPLE} **Alasan:** "
                    f"{data['reason']}\n"
                    f"{LAMP_PURPLE} **Sejak:** "
                    f"{waktu} yang lalu"
                ),
                color=self.random_color(),
                timestamp=self.now_wib()
            )

            await message.channel.send(
                embed=embed
            )


# =========================================================
# SETUP
# =========================================================

async def setup(bot):
    await bot.add_cog(AFK(bot))