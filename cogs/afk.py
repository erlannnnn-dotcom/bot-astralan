import discord
from discord.ext import commands
from discord import app_commands

import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path


# =========================================================
# CONFIG
# =========================================================

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "afk.db"

# WIB = UTC + 7
WIB = timezone(timedelta(hours=7))

AFK_PREFIX = "[AFK] "

# Warna embed
COLOR_AFK = 0x9B6BFF     # ungu (AFK aktif & mention)
COLOR_BACK = 0x3BA55D    # hijau (welcome back)


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
        # key: (guild_id, user_id)
        # value: {"reason", "since", "mentions", "old_nick"}
        self.afk_users = {}

        self.init_database()
        self.load_afk_data()

    # =====================================================
    # TIME
    # =====================================================

    def now(self):
        """Waktu sekarang (UTC, timezone-aware)."""
        return datetime.now(timezone.utc)

    def to_wib_text(self, dt: datetime):
        """Format jam WIB, contoh: 21.30 WIB"""
        return dt.astimezone(WIB).strftime("%H.%M WIB")

    def relative_ts(self, dt: datetime):
        """Timestamp Discord yang update otomatis (contoh: 5 menit yang lalu)."""
        return f"<t:{int(dt.timestamp())}:R>"

    def format_time(self, seconds: int):
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
    # DATABASE
    # =====================================================

    def get_connection(self):
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn

    def init_database(self):
        """
        Membuat tabel AFK otomatis + migrasi kolom baru
        (aman untuk database lama).
        """

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
                    mentions INTEGER NOT NULL DEFAULT 0,
                    old_nick TEXT,

                    PRIMARY KEY (user_id, guild_id)
                )
            """)

            # Migrasi untuk database lama
            cursor.execute("PRAGMA table_info(afk_users)")
            columns = {row["name"] for row in cursor.fetchall()}

            if "mentions" not in columns:
                cursor.execute("""
                    ALTER TABLE afk_users
                    ADD COLUMN mentions INTEGER NOT NULL DEFAULT 0
                """)

            if "old_nick" not in columns:
                cursor.execute("""
                    ALTER TABLE afk_users
                    ADD COLUMN old_nick TEXT
                """)

            conn.commit()

        finally:
            conn.close()

    def load_afk_data(self):
        """Memuat data AFK dari database ke cache."""

        self.afk_users.clear()

        conn = self.get_connection()

        try:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT user_id, guild_id, reason, since, mentions, old_nick
                FROM afk_users
            """)

            for row in cursor.fetchall():

                try:
                    since = datetime.fromisoformat(row["since"])

                    # Data lama disimpan sebagai WIB tanpa timezone
                    if since.tzinfo is None:
                        since = since.replace(tzinfo=WIB)

                    since = since.astimezone(timezone.utc)

                    self.afk_users[
                        (row["guild_id"], row["user_id"])
                    ] = {
                        "reason": row["reason"],
                        "since": since,
                        "mentions": row["mentions"],
                        "old_nick": row["old_nick"],
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
        since: datetime,
        old_nick
    ):
        """Simpan / update status AFK."""

        conn = self.get_connection()

        try:
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO afk_users (
                    user_id, guild_id, reason, since, mentions, old_nick
                )
                VALUES (?, ?, ?, ?, 0, ?)

                ON CONFLICT(user_id, guild_id)
                DO UPDATE SET
                    reason = excluded.reason,
                    since = excluded.since,
                    mentions = 0,
                    old_nick = excluded.old_nick
            """, (
                user_id,
                guild_id,
                reason,
                since.isoformat(),
                old_nick
            ))

            conn.commit()

        finally:
            conn.close()

    def update_mentions(
        self,
        guild_id: int,
        user_id: int,
        mentions: int
    ):
        """Update jumlah mention saat user AFK."""

        conn = self.get_connection()

        try:
            cursor = conn.cursor()

            cursor.execute("""
                UPDATE afk_users
                SET mentions = ?
                WHERE user_id = ? AND guild_id = ?
            """, (mentions, user_id, guild_id))

            conn.commit()

        finally:
            conn.close()

    def remove_afk(self, guild_id: int, user_id: int):
        """Hapus status AFK dari database."""

        conn = self.get_connection()

        try:
            cursor = conn.cursor()

            cursor.execute("""
                DELETE FROM afk_users
                WHERE user_id = ? AND guild_id = ?
            """, (user_id, guild_id))

            conn.commit()

        finally:
            conn.close()

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
        reason: app_commands.Range[str, 1, 200] = "AFK"
    ):

        # Harus di server
        if interaction.guild is None:

            await interaction.response.send_message(
                f"{LAMP_PURPLE} Command ini hanya bisa digunakan di server.",
                ephemeral=True
            )

            return

        user = interaction.user
        guild_id = interaction.guild.id
        user_id = user.id

        since = self.now()

        # Simpan nickname asli (None = tidak punya nickname)
        old_nick = user.nick

        # Kalau sudah AFK sebelumnya, pertahankan nickname asli
        previous = self.afk_users.get((guild_id, user_id))

        if previous is not None:
            old_nick = previous["old_nick"]

        # =================================================
        # SIMPAN DATABASE + CACHE
        # =================================================

        self.save_afk(
            guild_id=guild_id,
            user_id=user_id,
            reason=reason,
            since=since,
            old_nick=old_nick
        )

        self.afk_users[(guild_id, user_id)] = {
            "reason": reason,
            "since": since,
            "mentions": 0,
            "old_nick": old_nick
        }

        # =================================================
        # NICKNAME
        # =================================================

        try:

            base_name = old_nick or user.display_name

            # Batas nickname Discord = 32 karakter
            max_len = 32 - len(AFK_PREFIX)
            new_name = f"{AFK_PREFIX}{base_name[:max_len]}"

            await user.edit(nick=new_name)

        except (discord.Forbidden, discord.HTTPException):
            pass

        except Exception:
            pass

        # =================================================
        # EMBED
        # =================================================

        embed = discord.Embed(
            title=f"{LAMP_PURPLE} AFK aktif",
            description=(
                f"{ARROW_BLUE} Oke {user.mention}, kamu sekarang AFK. "
                f"Kami kasih tahu siapa pun yang mention kamu."
            ),
            color=COLOR_AFK,
            timestamp=since
        )

        embed.set_author(
            name=user.display_name,
            icon_url=user.display_avatar.url
        )

        embed.add_field(
            name=f"{FLOWER_PURPLE} Alasan",
            value=reason,
            inline=True
        )

        embed.add_field(
            name=f"{LAMP_PURPLE} Mulai",
            value=self.to_wib_text(since),
            inline=True
        )

        embed.set_footer(
            text="Status nonaktif otomatis saat kamu kirim pesan"
        )

        await interaction.response.send_message(embed=embed)

    # =====================================================
    # ON MESSAGE
    # =====================================================

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):

        # Abaikan bot
        if message.author.bot:
            return

        # Abaikan DM
        if message.guild is None:
            return

        guild_id = message.guild.id
        author_id = message.author.id

        author_key = (guild_id, author_id)

        # =================================================
        # BALIK DARI AFK
        # =================================================

        if author_key in self.afk_users:

            data = self.afk_users.pop(author_key)

            self.remove_afk(
                guild_id=guild_id,
                user_id=author_id
            )

            afk_seconds = int(
                (self.now() - data["since"]).total_seconds()
            )

            waktu = self.format_time(afk_seconds)

            # ---------------------------------------------
            # KEMBALIKAN NICKNAME
            # ---------------------------------------------

            try:

                current_nick = message.author.nick

                if current_nick and current_nick.startswith(AFK_PREFIX):
                    await message.author.edit(
                        nick=data["old_nick"]
                    )

            except (discord.Forbidden, discord.HTTPException):
                pass

            except Exception:
                pass

            # ---------------------------------------------
            # WELCOME BACK
            # ---------------------------------------------

            embed = discord.Embed(
                title=f"{FLOWER_PURPLE} Welcome back!",
                description=(
                    f"{ARROW_BLUE} {message.author.mention} "
                    f"sudah kembali."
                ),
                color=COLOR_BACK,
                timestamp=self.now()
            )

            embed.add_field(
                name=f"{LAMP_PURPLE} Durasi AFK",
                value=waktu,
                inline=True
            )

            embed.add_field(
                name=f"{FLOWER_PURPLE} Alasan tadi",
                value=data["reason"],
                inline=True
            )

            embed.add_field(
                name=f"{ARROW_BLUE} Di-mention",
                value=f"{data['mentions']} kali",
                inline=True
            )

            await message.channel.send(embed=embed)

        # =================================================
        # CEK MENTION
        # =================================================

        handled = set()

        for user in message.mentions:

            # Lewati bot, diri sendiri, dan duplikat
            if user.bot or user.id == author_id:
                continue

            if user.id in handled:
                continue

            user_key = (guild_id, user.id)

            data = self.afk_users.get(user_key)

            if data is None:
                continue

            handled.add(user.id)

            # Tambah hitungan mention
            data["mentions"] += 1

            self.update_mentions(
                guild_id=guild_id,
                user_id=user.id,
                mentions=data["mentions"]
            )

            # ---------------------------------------------
            # EMBED AFK MENTION
            # ---------------------------------------------

            embed = discord.Embed(
                title=f"{LAMP_PURPLE} Lagi AFK",
                description=(
                    f"{ARROW_BLUE} {user.mention} "
                    f"sedang tidak di tempat."
                ),
                color=COLOR_AFK,
                timestamp=self.now()
            )

            embed.set_thumbnail(url=user.display_avatar.url)

            embed.add_field(
                name=f"{FLOWER_PURPLE} Alasan",
                value=data["reason"],
                inline=True
            )

            embed.add_field(
                name=f"{LAMP_PURPLE} Sejak",
                value=self.relative_ts(data["since"]),
                inline=True
            )

            await message.channel.send(embed=embed)


# =========================================================
# SETUP
# =========================================================

async def setup(bot):
    await bot.add_cog(AFK(bot))