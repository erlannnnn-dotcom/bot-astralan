import discord
from discord.ext import commands

class AutoRoles(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        # ID Roles
        self.TAG_ROLE_ID = 1538088297199444039
        self.TAG_REF_ROLE_ID = 1526881805645643917  # Posisi role tag dipasang tepat di atas role ini

        self.BOOSTER_ROLE_ID = 1497460091442565241
        self.BOOSTER_REF_ROLE_ID = 1497460091442565241  # Sesuaikan jika ada role referensi lain

    def has_server_tag(self, member: discord.Member) -> bool:
        """Mengecek apakah member memasang Server Tag (Clan Tag) resmi dari server ini."""
        # Memeriksa fitur Clan / Primary Guild Tag Discord
        if hasattr(member, 'primary_guild') and member.primary_guild:
            if member.primary_guild.id == member.guild.id:
                return True

        # Penanganan fallback atribut alternatif discord.py
        if hasattr(member, 'clan') and member.clan:
            if getattr(member.clan, 'identity_guild_id', None) == member.guild.id or getattr(member.clan, 'guild_id', None) == member.guild.id:
                return True

        return False

    async def adjust_role_positions(self, guild: discord.Guild):
        """Merapikan posisi hirarki role."""
        try:
            tag_role = guild.get_role(self.TAG_ROLE_ID)
            ref_tag_role = guild.get_role(self.TAG_REF_ROLE_ID)
            if tag_role and ref_tag_role and tag_role.id != ref_tag_role.id:
                if tag_role.position <= ref_tag_role.position:
                    await tag_role.edit(position=ref_tag_role.position + 1)

            booster_role = guild.get_role(self.BOOSTER_ROLE_ID)
            ref_booster_role = guild.get_role(self.BOOSTER_REF_ROLE_ID)
            if booster_role and ref_booster_role and booster_role.id != ref_booster_role.id:
                if booster_role.position <= ref_booster_role.position:
                    await booster_role.edit(position=ref_booster_role.position + 1)
        except Exception as e:
            print(f"[AutoRoles Error] Gagal mengatur posisi role: {e}")

    async def sync_all_members(self, guild: discord.Guild):
        """Pemeriksaan ulang seluruh member saat bot aktif/sync."""
        tag_role = guild.get_role(self.TAG_ROLE_ID)
        booster_role = guild.get_role(self.BOOSTER_ROLE_ID)

        for member in guild.members:
            if member.bot:
                continue

            # 1. Sync Server Tag Resmi
            if tag_role:
                if self.has_server_tag(member):
                    if tag_role not in member.roles:
                        await member.add_roles(tag_role, reason="Auto Sync: Menggunakan Server Tag Resmi")
                else:
                    if tag_role in member.roles:
                        await member.remove_roles(tag_role, reason="Auto Sync: Server Tag Lepas/Dihapus")

            # 2. Sync Status Booster
            if booster_role:
                if member.premium_since is not None:
                    if booster_role not in member.roles:
                        await member.add_roles(booster_role, reason="Auto Sync: Server Booster")
                else:
                    if booster_role in member.roles:
                        await member.remove_roles(booster_role, reason="Auto Sync: Boost Habis")

    @commands.Cog.listener()
    async def on_ready(self):
        for guild in self.bot.guilds:
            await self.adjust_role_positions(guild)
            await self.sync_all_members(guild)

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        if self.has_server_tag(member):
            tag_role = member.guild.get_role(self.TAG_ROLE_ID)
            if tag_role and tag_role not in member.roles:
                await member.add_roles(tag_role, reason="Auto Role: Memasang Server Tag Saat Join")

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        guild = after.guild

        # 1. CEK PERUBAHAN SERVER TAG RESMI (CLAN TAG)
        has_tag_before = self.has_server_tag(before)
        has_tag_after = self.has_server_tag(after)

        if has_tag_before != has_tag_after:
            tag_role = guild.get_role(self.TAG_ROLE_ID)
            if tag_role:
                if has_tag_after:
                    if tag_role not in after.roles:
                        await after.add_roles(tag_role, reason="Auto Role: Memasang Server Tag Resmi")
                else:
                    if tag_role in after.roles:
                        await after.remove_roles(tag_role, reason="Auto Role: Melepas Server Tag Resmi")

        # 2. CEK STATUS BOOSTER
        if before.premium_since != after.premium_since:
            booster_role = guild.get_role(self.BOOSTER_ROLE_ID)
            if booster_role:
                if after.premium_since is not None:
                    if booster_role not in after.roles:
                        await after.add_roles(booster_role, reason="Auto Role: Server Booster Baru")
                else:
                    if booster_role in after.roles:
                        await after.remove_roles(booster_role, reason="Auto Role: Boost Berakhir")

async def setup(bot):
    await bot.add_cog(AutoRoles(bot))