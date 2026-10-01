import discord
from discord.ext import commands
from discord import app_commands

import sqlite3
import random
from datetime import datetime
from pathlib import Path


# =========================================================
# CONFIG
# =========================================================

# Lokasi database:
# /root/discord-kim/afk.db
BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "afk.db"


# =========================================================
# AFK COG
# =========================================================

class AFK(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        # Cache AFK di RAM untuk akses cepat.
        # Database tetap menjadi penyimpanan utama.
        self.afk_users = {}

        # Pastikan database dan tabel otomatis dibuat.
        self.init_database()

        # Load data AFK lama dari database.
        self.load_afk_data()

    # =====================================================
    # DATABASE
    # =====================================================

    def get_connection(self):
        """
        Membuka koneksi SQLite ke database AFK.
        """
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn

    def init_database(self):
        """
        Membuat database dan tabel AFK jika belum ada.
        """

        # Folder utama bot harusnya sudah ada,
        # tetapi tetap dibuat jika diperlukan.
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)

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
        Memuat seluruh status AFK dari database ke RAM
        ketika cog pertama kali dijalankan.
        """

        self.afk_users.clear()

        conn = self.get_connection()

        try:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT user_id, guild_id, reason, since
                FROM afk_users
            """)

            rows = cursor.fetchall()

            for row in rows:
                try:
                    since = datetime.fromisoformat(row["since"])

                    self.afk_users[
                        (row["guild_id"], row["user_id"])
                    ] = {
                        "reason": row["reason"],
                        "since": since
                    }

                except Exception:
                    # Kalau ada satu data rusak,
                    # jangan sampai seluruh cog gagal load.
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
        Menyimpan / memperbarui status AFK ke database.
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
        Menghapus status AFK dari database.
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
        return discord.Color(random.randint(0, 0xFFFFFF))

    def format_time(self, seconds):
        minutes, seconds = divmod(seconds, 60)
        hours, minutes = divmod(minutes, 60)
        days, hours = divmod(hours, 24)

        if days > 0:
            return f"{days} hari {hours} jam"

        elif hours > 0:
            return f"{hours} jam {minutes} menit"

        elif minutes > 0:
            return f"{minutes} menit {seconds} detik"

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

        # Command AFK harus digunakan di server.
        if interaction.guild is None:
            await interaction.response.send_message(
                "❌ Command ini hanya bisa digunakan di server.",
                ephemeral=True
            )
            return

        guild_id = interaction.guild.id
        user_id = user.id

        # Waktu AFK.
        since = datetime.utcnow()

        # Simpan ke database.
        self.save_afk(
            guild_id=guild_id,
            user_id=user_id,
            reason=reason,
            since=since
        )

        # Simpan ke cache RAM.
        self.afk_users[
            (guild_id, user_id)
        ] = {
            "reason": reason,
            "since": since
        }

        # =================================================
        # UBAH NICKNAME
        # =================================================

        try:
            current_name = user.display_name

            # Hindari menjadi:
            # [AFK] [AFK] Nama
            if current_name.startswith("[AFK] "):
                new_name = current_name
            else:
                new_name = f"[AFK] {current_name}"

            await user.edit(nick=new_name)

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
            title="🌙 AFK Status Aktif",
            description=(
                f"{user.mention} telah mengaktifkan status AFK.\n\n"
                f"**Alasan:** {reason}"
            ),
            color=self.random_color(),
            timestamp=datetime.utcnow()
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
    async def on_message(self, message):

        # Abaikan bot.
        if message.author.bot:
            return

        # Pesan DM tidak memiliki guild.
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

            data = self.afk_users.pop(author_key)

            # Hapus dari database.
            self.remove_afk(
                guild_id=guild_id,
                user_id=author_id
            )

            # Hitung durasi AFK.
            afk_time = (
                datetime.utcnow() - data["since"]
            ).total_seconds()

            waktu = self.format_time(
                int(afk_time)
            )

            # =================================================
            # KEMBALIKAN NICKNAME
            # =================================================

            try:
                current_name = message.author.display_name

                if current_name.startswith("[AFK] "):
                    original_name = current_name[6:]

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
            # WELCOME BACK EMBED
            # =================================================

            embed = discord.Embed(
                title="👋 Welcome Back",
                description=(
                    f"{message.author.mention} telah kembali.\n\n"
                    f"**Durasi AFK:** {waktu}"
                ),
                color=self.random_color(),
                timestamp=datetime.utcnow()
            )

            await message.channel.send(
                embed=embed
            )

        # =================================================
        # CEK MENTION
        # =================================================

        # Set supaya kalau user dimention beberapa kali
        # dalam satu pesan, hanya muncul satu notifikasi.
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

            mentioned_users.add(user.id)

            data = self.afk_users[user_key]

            # Hitung durasi AFK.
            afk_time = (
                datetime.utcnow() - data["since"]
            ).total_seconds()

            waktu = self.format_time(
                int(afk_time)
            )

            # =================================================
            # AFK MENTION EMBED
            # =================================================

            embed = discord.Embed(
                title="⚠️ Pengguna Sedang AFK",
                description=(
                    f"{user.mention} saat ini sedang AFK.\n\n"
                    f"**Alasan:** {data['reason']}\n"
                    f"**Sejak:** {waktu} yang lalu"
                ),
                color=self.random_color(),
                timestamp=datetime.utcnow()
            )

            await message.channel.send(
                embed=embed
            )


# =========================================================
# SETUP
# =========================================================

async def setup(bot):
    await bot.add_cog(AFK(bot))