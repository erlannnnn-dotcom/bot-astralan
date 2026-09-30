import discord
from discord.ext import commands

class AutoThread(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Daftar ID channel yang ditentukan
        self.target_channels = {
            1496859809532743730,
            1538340630239903744,
            1539266079610900490
        }

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # Abaikan pesan yang dikirim oleh bot sendiri
        if message.author.bot:
            return

        # Cek apakah pesan dikirim di salah satu target channel
        if message.channel.id in self.target_channels:
            # Cek apakah ada lampiran (attachment) dan salah satunya adalah gambar
            has_image = any(
                att.content_type and att.content_type.startswith('image/')
                for att in message.attachments
            )

            if has_image:
                try:
                    # Menentukan judul thread
                    # Jika member menulis deskripsi/caption, gunakan teksnya.
                    # Jika tidak ada caption, gunakan nama member.
                    thread_name = message.content.strip() if message.content else f"Diskusi - {message.author.display_name}"

                    # Batasi panjang judul max 100 karakter (limit Discord)
                    if len(thread_name) > 100:
                        thread_name = thread_name[:97] + "..."

                    # Buat thread langsung dari pesan tersebut
                    await message.create_thread(
                        name=thread_name,
                        auto_archive_duration=1440 # Otomatis diarsipkan setelah 24 jam (1440 menit)
                    )
                except discord.HTTPException as e:
                    print(f"[AutoThread Error] Gagal membuat thread: {e}")

async def setup(bot):
    await bot.add_cog(AutoThread(bot))
root@server2:~/bot-astralan/bot-astralan/cogs# cat staffdirectory.py
import discord
from discord.ext import commands, tasks
from datetime import datetime, timezone
import json
import os
import asyncio


class StaffDirectory(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

        # ==========================================
        # CONFIG
        # ==========================================

        # Channel tempat Staff Directory ditampilkan
        self.CHANNEL_ID = 1553032690465251410

        # ==========================================
        # ASTRALAN STATUS EMOJI
        # ==========================================

        self.ONLINE_EMOJI_ID = 1553033618845343786
        self.OFFLINE_EMOJI_ID = 1553033468265631796

        # ==========================================
        # ASTRALAN STAFF ROLES
        # ==========================================

        self.STAFF_ROLES = [

            {
                "role_id": 1496838207822889050,
                "name": "Own",
                "emoji": "👑",
                "color": discord.Color.from_rgb(155, 89, 182)
            },

            {
                "role_id": 1496846251914956820,
                "name": "Guardian",
                "emoji": "🛡️",
                "color": discord.Color.from_rgb(126, 87, 194)
            },

            {
                "role_id": 1542886846508437515,
                "name": "Event Organizer",
                "emoji": "🎉",
                "color": discord.Color.from_rgb(171, 112, 214)
            },

            {
                "role_id": 1542887345873756272,
                "name": "Creative Studio",
                "emoji": "🎨",
                "color": discord.Color.from_rgb(186, 104, 200)
            },

            {
                "role_id": 1542887778658951208,
                "name": "Community Relations",
                "emoji": "💜",
                "color": discord.Color.from_rgb(139, 92, 246)
            }
        ]

        # ==========================================
        # MESSAGE ID
        # ==========================================

        self.message_ids = {
            role["role_id"]: None
            for role in self.STAFF_ROLES
        }

        # ==========================================
        # EMBED CACHE
        # ==========================================

        self.embed_cache = {}

        # ==========================================
        # ACTIVITY DATABASE
        # ==========================================

        self.activity_file = "staff_activity.json"
        self.activity_data = self.load_activity()

        # ==========================================
        # REFRESH CONTROL
        # ==========================================

        self.refresh_lock = asyncio.Lock()

        self.refresh_task = None

        self.REFRESH_DELAY = 5

        # ==========================================
        # START AUTO REFRESH
        # ==========================================

        self.update_directory.start()

    # ==========================================
    # LOAD ACTIVITY
    # ==========================================

    def load_activity(self):
        """Membaca database aktivitas staff."""

        if not os.path.exists(self.activity_file):
            return {}

        try:
            with open(
                self.activity_file,
                "r",
                encoding="utf-8"
            ) as f:

                return json.load(f)

        except Exception as e:

            print(
                f"[ASTRALAN DIRECTORY] "
                f"Gagal membaca activity data: {e}"
            )

            return {}

    # ==========================================
    # SAVE ACTIVITY
    # ==========================================

    def save_activity(self):
        """Menyimpan database aktivitas staff."""

        try:

            with open(
                self.activity_file,
                "w",
                encoding="utf-8"
            ) as f:

                json.dump(
                    self.activity_data,
                    f,
                    indent=4,
                    ensure_ascii=False
                )

        except Exception as e:

            print(
                f"[ASTRALAN DIRECTORY] "
                f"Gagal menyimpan activity data: {e}"
            )

    # ==========================================
    # UPDATE LAST ACTIVE
    # ==========================================

    def update_activity(self, member_id):

        timestamp = int(
            datetime.now(
                timezone.utc
            ).timestamp()
        )

        old_timestamp = self.activity_data.get(
            str(member_id)
        )

        # Jangan tulis file jika timestamp
        # sebenarnya tidak berubah.
        if old_timestamp == timestamp:
            return

        self.activity_data[str(member_id)] = timestamp

        self.save_activity()

    # ==========================================
    # GET STAFF STATUS
    # ==========================================

    def get_activity_status(self, member):

        timestamp = self.activity_data.get(
            str(member.id)
        )

        # ======================================
        # AMBIL EMOJI DARI SERVER
        # ======================================

        online_emoji = member.guild.get_emoji(
            self.ONLINE_EMOJI_ID
        )

        offline_emoji = member.guild.get_emoji(
            self.OFFLINE_EMOJI_ID
        )

        # Fallback jika emoji tidak ditemukan
        online_emoji = (
            str(online_emoji)
            if online_emoji
            else "🟢"
        )

        offline_emoji = (
            str(offline_emoji)
            if offline_emoji
            else "⚪"
        )

        # ======================================
        # STAFF SEDANG AKTIF
        # ======================================

        if member.status != discord.Status.offline:

            if not timestamp:

                timestamp = int(
                    datetime.now(
                        timezone.utc
                    ).timestamp()
                )

                self.activity_data[
                    str(member.id)
                ] = timestamp

                self.save_activity()

            return f"{online_emoji} **Aktif sekarang**"

        # ======================================
        # STAFF SUDAH OFFLINE
        # ======================================

        if timestamp:

            return (
                f"{offline_emoji} "
                f"**Aktif <t:{timestamp}:R>**"
            )

        # ======================================
        # BELUM ADA DATA
        # ======================================

        return (
            f"{offline_emoji} "
            f"**Belum terdeteksi**"
        )

    # ==========================================
    # GENERATE ROLE EMBED
    # ==========================================

    async def generate_role_embed(
        self,
        guild,
        role_info
    ):

        role = guild.get_role(
            role_info["role_id"]
        )

        # ======================================
        # EMBED DASAR
        # ======================================

        embed = discord.Embed(
            color=role_info.get(
                "color",
                discord.Color.from_rgb(
                    139,
                    92,
                    246
                )
            )
        )

        # ======================================
        # ROLE TIDAK DITEMUKAN
        # ======================================

        if not role:

            embed.description = (
                "╭─ ⚠️ **Role tidak ditemukan**\n"
                "╰─ Pastikan role Astralan masih tersedia."
            )

            return embed

        # ======================================
        # URUTKAN MEMBER
        # ======================================

        members = sorted(
            role.members,
            key=lambda m: m.display_name.lower()
        )

        # ======================================
        # HEADER ASTRALAN
        # ======================================

        embed.set_author(
            name=(
                f"ASTRALAN  •  STAFF DIRECTORY"
            ),
            icon_url=(
                guild.icon.url
                if guild.icon
                else discord.Embed.Empty
            )
        )

        # ======================================
        # ROLE TITLE
        # ======================================

        embed.title = (
            f"{role_info['emoji']}  {role_info['name']}"
        )

        embed.description = (
            "╭────────────────────────────╮\n"
            f"│  **{role_info['name']}**\n"
            "│  Astralan Staff Division\n"
            "╰────────────────────────────╯"
        )

        # ======================================
        # TIDAK ADA STAFF
        # ======================================

        if not members:

            embed.add_field(
                name="✦ Personnel",
                value=(
                    "```"
                    "Belum ada staff yang terdaftar."
                    "```"
                ),
                inline=False
            )

        # ======================================
        # ADA STAFF
        # ======================================

        else:

            staff_list = []

            for index, member in enumerate(members):

                status = self.get_activity_status(
                    member
                )

                number = f"{index + 1:02d}"

                staff_info = (
                    f"**{number}  {member.display_name}**\n"
                    f"└─ {member.mention}\n"
                    f"   {status}"
                )

                staff_list.append(
                    staff_info
                )

            # ----------------------------------
            # STAFF LIST
            # ----------------------------------

            embed.add_field(
                name=(
                    f"✦ Personnel  ·  {len(members)} Staff"
                ),
                value=(
                    "\n\n".join(staff_list)
                ),
                inline=False
            )

        # ======================================
        # FOOTER
        # ======================================

        embed.set_footer(
            text=(
                f"Astralan  •  "
                f"{role_info['name']}  •  "
                f"{len(members)} personnel"
            )
        )

        return embed

    # ==========================================
    # FIND OLD STAFF MESSAGES
    # ==========================================

    async def find_existing_messages(self, channel):

        found = {}

        try:

            async for message in channel.history(
                limit=100
            ):

                if message.author != self.bot.user:
                    continue

                if not message.embeds:
                    continue

                author = message.embeds[0].author

                if not author or not author.name:
                    continue

                for role_info in self.STAFF_ROLES:

                    role_id = role_info["role_id"]

                    if role_id in self.message_ids:

                        if self.message_ids[role_id]:
                            continue

                    if role_info["name"] in author.name:

                        found[role_id] = message.id

                        break

        except discord.HTTPException as e:

            print(
                f"[ASTRALAN DIRECTORY] "
                f"Gagal mencari message lama: {e}"
            )

        return found

    # ==========================================
    # SCHEDULE REFRESH
    # ==========================================

    def schedule_refresh(self, guild):

        if (
            self.refresh_task
            and not self.refresh_task.done()
        ):
            return

        self.refresh_task = asyncio.create_task(
            self._delayed_refresh(guild)
        )

    # ==========================================
    # DELAYED REFRESH
    # ==========================================

    async def _delayed_refresh(self, guild):

        try:

            await asyncio.sleep(
                self.REFRESH_DELAY
            )

            await self.refresh_all_panels(
                guild
            )

        except asyncio.CancelledError:

            pass

        except Exception as e:

            print(
                f"[ASTRALAN DIRECTORY] "
                f"Refresh task error: {e}"
            )

    # ==========================================
    # REFRESH ALL PANELS
    # ==========================================

    async def refresh_all_panels(self, guild):

        if self.refresh_lock.locked():
            return

        async with self.refresh_lock:

            channel = self.bot.get_channel(
                self.CHANNEL_ID
            )

            if not channel:

                print(
                    "[ASTRALAN DIRECTORY] "
                    "Channel tidak ditemukan."
                )

                return

            # ==================================
            # CARI MESSAGE LAMA
            # ==================================

            missing_roles = [
                role_info
                for role_info in self.STAFF_ROLES
                if not self.message_ids.get(
                    role_info["role_id"]
                )
            ]

            if missing_roles:

                found_messages = (
                    await self.find_existing_messages(
                        channel
                    )
                )

                for role_id, message_id in found_messages.items():

                    self.message_ids[
                        role_id
                    ] = message_id

            # ==================================
            # UPDATE SETIAP PANEL
            # ==================================

            for role_info in self.STAFF_ROLES:

                role_id = role_info["role_id"]

                try:

                    embed = (
                        await self.generate_role_embed(
                            guild,
                            role_info
                        )
                    )

                    # ==================================
                    # UBAH EMBED MENJADI DATA
                    # ==================================

                    embed_data = embed.to_dict()

                    old_embed_data = (
                        self.embed_cache.get(
                            role_id
                        )
                    )

                    message_id = (
                        self.message_ids.get(
                            role_id
                        )
                    )

                    # ==================================
                    # MESSAGE SUDAH ADA
                    # ==================================

                    if message_id:

                        if (
                            old_embed_data
                            == embed_data
                        ):

                            continue

                        try:

                            message = (
                                channel.get_partial_message(
                                    message_id
                                )
                            )

                            await message.edit(
                                embed=embed
                            )

                            self.embed_cache[
                                role_id
                            ] = embed_data

                            continue

                        except discord.NotFound:

                            print(
                                "[ASTRALAN DIRECTORY] "
                                f"Message {role_info['name']} "
                                "sudah tidak ditemukan."
                            )

                            self.message_ids[
                                role_id
                            ] = None

                            self.embed_cache.pop(
                                role_id,
                                None
                            )

                        except discord.HTTPException as e:

                            print(
                                "[ASTRALAN DIRECTORY] "
                                f"Gagal edit "
                                f"{role_info['name']}: {e}"
                            )

                            continue

                    # ==================================
                    # MESSAGE TIDAK ADA
                    # ==================================

                    new_message = await channel.send(
                        embed=embed
                    )

                    self.message_ids[
                        role_id
                    ] = new_message.id

                    self.embed_cache[
                        role_id
                    ] = embed_data

                    print(
                        "[ASTRALAN DIRECTORY] "
                        f"Panel {role_info['name']} dibuat."
                    )

                except Exception as e:

                    print(
                        "[ASTRALAN DIRECTORY] "
                        f"Error {role_info['name']}: {e}"
                    )

    # ==========================================
    # STAFF MENGIRIM PESAN
    # ==========================================

    @commands.Cog.listener()
    async def on_message(self, message):

        if message.author.bot:
            return

        if not isinstance(
            message.author,
            discord.Member
        ):
            return

        member = message.author

        # Cek apakah member adalah staff
        is_staff = any(
            role.id in self.message_ids
            for role in member.roles
        )

        if not is_staff:
            return

        self.update_activity(
            member.id
        )

    # ==========================================
    # STAFF ONLINE / OFFLINE
    # ==========================================

    @commands.Cog.listener()
    async def on_presence_update(
        self,
        before,
        after
    ):

        is_staff = any(
            role.id in self.message_ids
            for role in after.roles
        )

        if not is_staff:
            return

        # ======================================
        # OFFLINE → ONLINE
        # ======================================

        if (
            before.status == discord.Status.offline
            and after.status != discord.Status.offline
        ):

            self.update_activity(
                after.id
            )

            self.schedule_refresh(
                after.guild
            )

    # ==========================================
    # ROLE STAFF BERUBAH
    # ==========================================

    @commands.Cog.listener()
    async def on_member_update(
        self,
        before,
        after
    ):

        # Tidak ada perubahan role
        if before.roles == after.roles:
            return

        # ======================================
        # CEK ROLE STAFF ASTRALAN
        # ======================================

        staff_role_ids = {
            role["role_id"]
            for role in self.STAFF_ROLES
        }

        before_roles = {
            role.id
            for role in before.roles
        }

        after_roles = {
            role.id
            for role in after.roles
        }

        changed_roles = (
            before_roles ^ after_roles
        )

        if not (
            changed_roles
            & staff_role_ids
        ):
            return

        # ======================================
        # REFRESH DENGAN DEBOUNCE
        # ======================================

        self.schedule_refresh(
            after.guild
        )

    # ==========================================
    # AUTO REFRESH
    # ==========================================

    @tasks.loop(minutes=10)
    async def update_directory(self):

        await self.bot.wait_until_ready()

        channel = self.bot.get_channel(
            self.CHANNEL_ID
        )

        if not channel:
            return

        await self.refresh_all_panels(
            channel.guild
        )

    # ==========================================
    # BEFORE AUTO REFRESH
    # ==========================================

    @update_directory.before_loop
    async def before_update_directory(self):

        await self.bot.wait_until_ready()

    # ==========================================
    # SETUP DIRECTORY
    # ==========================================

    @commands.command(
        name="setupdirectory"
    )
    @commands.has_permissions(
        administrator=True
    )
    async def setup_directory(
        self,
        ctx
    ):

        self.CHANNEL_ID = ctx.channel.id

        try:

            await ctx.message.delete()

        except Exception:
            pass

        # Reset cache
        self.embed_cache.clear()

        # ======================================
        # BUAT PANEL ASTRALAN
        # ======================================

        for role_info in self.STAFF_ROLES:

            embed = (
                await self.generate_role_embed(
                    ctx.guild,
                    role_info
                )
            )

            message = await ctx.send(
                embed=embed
            )

            role_id = role_info["role_id"]

            self.message_ids[
                role_id
            ] = message.id

            self.embed_cache[
                role_id
            ] = embed.to_dict()

        print(
            "[ASTRALAN DIRECTORY] "
            "Directory berhasil dibuat."
        )

    # ==========================================
    # UNLOAD
    # ==========================================

    def cog_unload(self):

        self.update_directory.cancel()

        if (
            self.refresh_task
            and not self.refresh_task.done()
        ):

            self.refresh_task.cancel()


# ==============================================
# SETUP
# ==============================================

async def setup(bot):

    await bot.add_cog(
        StaffDirectory(bot)
    )