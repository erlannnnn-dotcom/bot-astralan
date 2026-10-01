import discord
from discord.ext import commands, tasks
from datetime import datetime, timezone
import json
import os
import asyncio


LOG = "[ASTRALAN DIRECTORY]"


class StaffDirectory(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

        # ==========================================
        # CONFIG
        # ==========================================

        # Channel tempat Staff Directory ditampilkan
        self.CHANNEL_ID = 1553032690465251410

        # Judul embed ringkasan (juga dipakai untuk mencari pesan lama)
        self.HEADER_TITLE = "Staff directory"

        # Warna embed ringkasan
        self.HEADER_COLOR = discord.Color.from_rgb(139, 92, 246)

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
                "color": discord.Color.from_rgb(155, 89, 182)
            },

            {
                "role_id": 1496846251914956820,
                "name": "Guardian",
                "color": discord.Color.from_rgb(126, 87, 194)
            },

            {
                "role_id": 1542886846508437515,
                "name": "Event Organizer",
                "color": discord.Color.from_rgb(171, 112, 214)
            },

            {
                "role_id": 1542887345873756272,
                "name": "Creative Studio",
                "color": discord.Color.from_rgb(186, 104, 200)
            },

            {
                "role_id": 1542887778658951208,
                "name": "Community Relations",
                "color": discord.Color.from_rgb(139, 92, 246)
            }
        ]

        self.STAFF_ROLE_IDS = {
            role["role_id"] for role in self.STAFF_ROLES
        }

        # Online, Idle, dan DND dianggap aktif
        self.ACTIVE_STATUSES = {
            discord.Status.online,
            discord.Status.idle,
            discord.Status.dnd
        }

        # ==========================================
        # MESSAGE ID
        # ==========================================

        # ID pesan disimpan ke file agar tetap sama setelah bot restart.
        self.message_file = "staff_directory_messages.json"
        self.directory_state = self.load_message_state()

        saved_messages = self.directory_state.get("messages", {})

        self.message_ids = {
            role["role_id"]: saved_messages.get(
                str(role["role_id"])
            )
            for role in self.STAFF_ROLES
        }

        # ID pesan embed ringkasan
        self.header_message_id = self.directory_state.get(
            "header_message_id"
        )

        # Gunakan channel yang tersimpan jika tersedia.
        self.CHANNEL_ID = self.directory_state.get(
            "channel_id",
            self.CHANNEL_ID
        )

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
    # LOAD MESSAGE STATE
    # ==========================================

    def load_message_state(self):
        """Membaca state pesan. Jika belum ada, otomatis membuat JSON."""

        default_data = {
            "channel_id": self.CHANNEL_ID,
            "header_message_id": None,
            "messages": {}
        }

        # JSON belum ada -> buat otomatis.
        if not os.path.exists(self.message_file):
            self._write_message_state(default_data)

            print(f"{LOG} File {self.message_file} dibuat otomatis.")

            return default_data

        try:
            with open(
                self.message_file,
                "r",
                encoding="utf-8"
            ) as f:
                data = json.load(f)

            if not isinstance(data, dict):
                return default_data

            data.setdefault("channel_id", self.CHANNEL_ID)
            data.setdefault("header_message_id", None)
            data.setdefault("messages", {})

            return data

        except Exception as e:
            print(f"{LOG} Gagal membaca message state: {e}")

            # File rusak -> gunakan state kosong lalu perbaiki file.
            self._write_message_state(default_data)

            return default_data

    def _write_message_state(self, data):
        """Menulis file JSON state."""

        try:
            with open(
                self.message_file,
                "w",
                encoding="utf-8"
            ) as f:
                json.dump(
                    data,
                    f,
                    indent=4,
                    ensure_ascii=False
                )

        except Exception as e:
            print(f"{LOG} Gagal menulis message state: {e}")

    # ==========================================
    # SAVE MESSAGE STATE
    # ==========================================

    def save_message_state(self):
        """Menyimpan ID channel dan pesan Staff Directory."""

        data = {
            "channel_id": self.CHANNEL_ID,
            "header_message_id": self.header_message_id,
            "messages": {
                str(role_id): message_id
                for role_id, message_id
                in self.message_ids.items()
                if message_id
            }
        }

        self._write_message_state(data)

    # ==========================================
    # PANEL ID HELPER
    # ==========================================

    def get_panel_id(self, key):
        """key = 'header' atau role_id."""

        if key == "header":
            return self.header_message_id

        return self.message_ids.get(key)

    def set_panel_id(self, key, message_id):

        if key == "header":
            self.header_message_id = message_id
        else:
            self.message_ids[key] = message_id

    def reset_panel_ids(self):

        self.header_message_id = None

        for role_id in self.message_ids:
            self.message_ids[role_id] = None

        self.embed_cache.clear()

        self.save_message_state()

    # ==========================================
    # LOAD / SAVE ACTIVITY
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
            print(f"{LOG} Gagal membaca activity data: {e}")

            return {}

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
            print(f"{LOG} Gagal menyimpan activity data: {e}")

    def update_activity(
        self,
        member_id,
        timestamp=None,
        min_interval=0
    ):
        """
        Catat waktu terakhir aktif.

        min_interval = jeda minimal (detik) sejak catatan sebelumnya,
        supaya file tidak ditulis ulang setiap staff mengirim pesan.
        """

        if timestamp is None:
            timestamp = int(datetime.now(timezone.utc).timestamp())

        old_timestamp = self.activity_data.get(str(member_id))

        if old_timestamp is not None:

            if old_timestamp == timestamp:
                return

            if timestamp - old_timestamp < min_interval:
                return

        self.activity_data[str(member_id)] = timestamp

        self.save_activity()

    # ==========================================
    # STATUS HELPER
    # ==========================================

    def is_active(self, member):
        return member.status in self.ACTIVE_STATUSES

    def get_status_emoji(self, guild, active):
        """Emoji status dari server, fallback ke emoji bawaan."""

        if active:
            emoji = guild.get_emoji(self.ONLINE_EMOJI_ID)
            return str(emoji) if emoji else "🟢"

        emoji = guild.get_emoji(self.OFFLINE_EMOJI_ID)
        return str(emoji) if emoji else "⚪"

    def get_status_text(self, member):
        """Teks status (tanpa emoji)."""

        timestamp = self.activity_data.get(str(member.id))

        if self.is_active(member):

            # Staff aktif tapi belum punya data -> simpan waktu sekarang.
            if not timestamp:
                self.update_activity(member.id)

            return "Aktif sekarang"

        if timestamp:
            return f"Aktif <t:{timestamp}:R>"

        return "Belum terdeteksi"

    def sort_key(self, member):
        """
        Urutan: yang aktif dulu, lalu offline dari yang
        terakhir aktif paling baru, lalu berdasarkan nama.
        """

        timestamp = self.activity_data.get(str(member.id), 0)

        return (
            0 if self.is_active(member) else 1,
            -timestamp,
            member.display_name.lower()
        )

    # ==========================================
    # GENERATE HEADER EMBED
    # ==========================================

    def generate_header_embed(self, guild):

        # Staff unik (satu orang bisa punya lebih dari satu role staff)
        unique_members = {}

        for role_info in self.STAFF_ROLES:

            role = guild.get_role(role_info["role_id"])

            if not role:
                continue

            for member in role.members:
                unique_members[member.id] = member

        total = len(unique_members)

        active = sum(
            1 for member in unique_members.values()
            if self.is_active(member)
        )

        embed = discord.Embed(
            title=self.HEADER_TITLE,
            description="Daftar staff Astralan dan status aktivitasnya.",
            color=self.HEADER_COLOR
        )

        if guild.icon:
            embed.set_author(
                name="ASTRALAN",
                icon_url=guild.icon.url
            )
        else:
            embed.set_author(name="ASTRALAN")

        embed.add_field(
            name="Total staff",
            value=str(total),
            inline=True
        )

        embed.add_field(
            name="Aktif",
            value=str(active),
            inline=True
        )

        embed.add_field(
            name="Offline",
            value=str(total - active),
            inline=True
        )

        return embed

    # ==========================================
    # GENERATE ROLE EMBED
    # ==========================================

    def generate_role_embed(self, guild, role_info):

        role = guild.get_role(role_info["role_id"])

        embed = discord.Embed(
            color=role_info.get(
                "color",
                discord.Color.from_rgb(139, 92, 246)
            )
        )

        # ======================================
        # ROLE TIDAK DITEMUKAN
        # ======================================

        if not role:

            embed.title = role_info["name"]

            embed.description = (
                "Role tidak ditemukan. "
                "Pastikan role Astralan masih tersedia."
            )

            return embed

        members = sorted(role.members, key=self.sort_key)

        embed.title = f"{role_info['name']} · {len(members)} staff"

        # ======================================
        # TIDAK ADA STAFF
        # ======================================

        if not members:

            embed.description = "Belum ada staff di role ini."

            return embed

        # ======================================
        # DAFTAR STAFF
        # ======================================

        entries = []

        for member in members:

            dot = self.get_status_emoji(
                guild,
                self.is_active(member)
            )

            name = discord.utils.escape_markdown(
                member.display_name
            )

            status = self.get_status_text(member)

            entries.append(
                f"{dot} **{name}** {member.mention}\n"
                f"-# {status}"
            )

        # Batas deskripsi embed = 4096 karakter
        description = ""
        shown = 0

        for entry in entries:

            if len(description) + len(entry) + 40 > 4096:
                break

            description += entry + "\n"
            shown += 1

        hidden = len(entries) - shown

        if hidden > 0:
            description += f"\n… dan {hidden} staff lainnya"

        embed.description = description.strip()

        return embed

    # ==========================================
    # BUILD PANEL EMBED
    # ==========================================

    def build_panel_embed(self, guild, key, role_info):

        if key == "header":
            return self.generate_header_embed(guild)

        return self.generate_role_embed(guild, role_info)

    # ==========================================
    # FIND OLD STAFF MESSAGES
    # ==========================================

    async def find_existing_messages(self, channel):
        """Cari pesan directory milik bot jika state hilang."""

        found = {}

        try:

            async for message in channel.history(limit=200):

                if message.author != self.bot.user:
                    continue

                if not message.embeds:
                    continue

                title = message.embeds[0].title

                if not title:
                    continue

                # Embed ringkasan
                if (
                    title == self.HEADER_TITLE
                    and not self.header_message_id
                    and "header" not in found
                ):
                    found["header"] = message.id
                    continue

                # Embed role
                for role_info in self.STAFF_ROLES:

                    role_id = role_info["role_id"]

                    if self.message_ids.get(role_id):
                        continue

                    if role_id in found:
                        continue

                    name = role_info["name"]

                    if title == name or title.startswith(f"{name} · "):
                        found[role_id] = message.id
                        break

        except discord.HTTPException as e:
            print(f"{LOG} Gagal mencari message lama: {e}")

        return found

    # ==========================================
    # SCHEDULE REFRESH
    # ==========================================

    def schedule_refresh(self, guild):

        if self.refresh_task and not self.refresh_task.done():
            return

        self.refresh_task = asyncio.create_task(
            self._delayed_refresh(guild)
        )

    async def _delayed_refresh(self, guild):

        try:
            await asyncio.sleep(self.REFRESH_DELAY)
            await self.refresh_all_panels(guild)

        except asyncio.CancelledError:
            pass

        except Exception as e:
            print(f"{LOG} Refresh task error: {e}")

    # ==========================================
    # REFRESH ALL PANELS
    # ==========================================

    async def refresh_all_panels(self, guild):

        if self.refresh_lock.locked():
            return

        async with self.refresh_lock:

            channel = self.bot.get_channel(self.CHANNEL_ID)

            if not channel:
                print(f"{LOG} Channel tidak ditemukan.")
                return

            # ==================================
            # SINKRONKAN DATA MEMBER / PRESENCE
            # ==================================
            # Setelah restart, cache presence bisa belum terisi.

            try:
                if not guild.chunked:
                    await guild.chunk(cache=True)

            except Exception as e:
                print(f"{LOG} Gagal sinkronisasi member: {e}")

            # ==================================
            # CARI MESSAGE LAMA (JIKA STATE HILANG)
            # ==================================

            has_missing = (
                not self.header_message_id
                or any(
                    not self.message_ids.get(role["role_id"])
                    for role in self.STAFF_ROLES
                )
            )

            if has_missing:

                found = await self.find_existing_messages(channel)

                for key, message_id in found.items():
                    self.set_panel_id(key, message_id)

                if found:
                    self.save_message_state()

            # ==================================
            # MIGRASI / REBUILD
            # ==================================
            # Embed ringkasan harus berada paling atas. Jika belum ada
            # tetapi panel role lama masih ada, hapus panel lama lalu
            # buat ulang berurutan.

            if (
                not self.header_message_id
                and any(self.message_ids.values())
            ):

                print(f"{LOG} Membangun ulang panel (layout baru).")

                for role_id, message_id in self.message_ids.items():

                    if not message_id:
                        continue

                    try:
                        await channel.get_partial_message(
                            message_id
                        ).delete()

                    except discord.HTTPException:
                        pass

                self.reset_panel_ids()

            # ==================================
            # UPDATE SETIAP PANEL
            # ==================================

            panels = [("header", None)] + [
                (role["role_id"], role)
                for role in self.STAFF_ROLES
            ]

            for key, role_info in panels:

                label = (
                    "Header"
                    if key == "header"
                    else role_info["name"]
                )

                try:

                    embed = self.build_panel_embed(
                        guild,
                        key,
                        role_info
                    )

                    embed_data = embed.to_dict()

                    message_id = self.get_panel_id(key)

                    # ==============================
                    # MESSAGE SUDAH ADA
                    # ==============================

                    if message_id:

                        # Tidak ada perubahan -> lewati
                        if self.embed_cache.get(key) == embed_data:
                            continue

                        try:

                            await channel.get_partial_message(
                                message_id
                            ).edit(embed=embed)

                            self.embed_cache[key] = embed_data

                            continue

                        except discord.NotFound:

                            print(
                                f"{LOG} Message {label} "
                                "sudah tidak ditemukan."
                            )

                            self.set_panel_id(key, None)
                            self.save_message_state()
                            self.embed_cache.pop(key, None)

                        except discord.HTTPException as e:

                            print(f"{LOG} Gagal edit {label}: {e}")

                            continue

                    # ==============================
                    # MESSAGE TIDAK ADA -> BUAT BARU
                    # ==============================

                    new_message = await channel.send(embed=embed)

                    self.set_panel_id(key, new_message.id)
                    self.save_message_state()

                    self.embed_cache[key] = embed_data

                    print(f"{LOG} Panel {label} dibuat.")

                except Exception as e:
                    print(f"{LOG} Error {label}: {e}")

    # ==========================================
    # STAFF MENGIRIM PESAN
    # ==========================================

    @commands.Cog.listener()
    async def on_message(self, message):

        if message.author.bot:
            return

        if not isinstance(message.author, discord.Member):
            return

        member = message.author

        is_staff = any(
            role.id in self.STAFF_ROLE_IDS
            for role in member.roles
        )

        if not is_staff:
            return

        # Jeda 60 detik agar file tidak ditulis di setiap pesan
        self.update_activity(member.id, min_interval=60)

    # ==========================================
    # STAFF ONLINE / OFFLINE
    # ==========================================

    @commands.Cog.listener()
    async def on_presence_update(self, before, after):

        is_staff = any(
            role.id in self.STAFF_ROLE_IDS
            for role in after.roles
        )

        if not is_staff:
            return

        was_active = before.status in self.ACTIVE_STATUSES
        now_active = after.status in self.ACTIVE_STATUSES

        # Sedang aktif -> catat waktu aktif
        if now_active:
            self.update_activity(after.id, min_interval=60)

        # Baru saja offline -> catat sebagai terakhir aktif
        elif was_active:
            self.update_activity(after.id)

        # Refresh setiap ada perubahan status
        if before.status != after.status:
            self.schedule_refresh(after.guild)

    # ==========================================
    # ROLE STAFF BERUBAH
    # ==========================================

    @commands.Cog.listener()
    async def on_member_update(self, before, after):

        if before.roles == after.roles:
            return

        before_roles = {role.id for role in before.roles}
        after_roles = {role.id for role in after.roles}

        changed_roles = before_roles ^ after_roles

        if not (changed_roles & self.STAFF_ROLE_IDS):
            return

        self.schedule_refresh(after.guild)

    # ==========================================
    # AUTO REFRESH
    # ==========================================

    @tasks.loop(minutes=10)
    async def update_directory(self):

        channel = self.bot.get_channel(self.CHANNEL_ID)

        if not channel:
            return

        await self.refresh_all_panels(channel.guild)

    @update_directory.before_loop
    async def before_update_directory(self):

        await self.bot.wait_until_ready()

    # ==========================================
    # SETUP DIRECTORY
    # ==========================================

    @commands.command(name="setupdirectory")
    @commands.has_permissions(administrator=True)
    async def setup_directory(self, ctx):

        # Pindah channel -> panel lama tidak berlaku lagi
        if ctx.channel.id != self.CHANNEL_ID:

            self.CHANNEL_ID = ctx.channel.id

            self.reset_panel_ids()

        self.directory_state["channel_id"] = self.CHANNEL_ID

        self.save_message_state()

        try:
            await ctx.message.delete()
        except Exception:
            pass

        # Paksa semua panel diedit ulang
        self.embed_cache.clear()

        await self.refresh_all_panels(ctx.guild)

        print(f"{LOG} Directory berhasil dibuat / diperbarui.")

    # ==========================================
    # UNLOAD
    # ==========================================

    def cog_unload(self):

        self.update_directory.cancel()

        if self.refresh_task and not self.refresh_task.done():
            self.refresh_task.cancel()


# ==============================================
# SETUP
# ==============================================

async def setup(bot):

    await bot.add_cog(StaffDirectory(bot))