import discord
from discord.ext import commands
import random

# ==========================================
# ID CHANNEL KHUSUS STATUS / QUOTE
# ==========================================
STATUS_CHANNEL_ID = 1544029661946839070


class UploadView(discord.ui.View):
    def __init__(self, bot, user_status_text, user_mood, author_id):
        super().__init__(timeout=300)
        self.bot = bot
        self.status_text = user_status_text
        self.mood = user_mood
        self.author_id = author_id

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author_id:
            await interaction.response.send_message(
                "❌ Ini bukan status milikmu!", ephemeral=True
            )
            return False
        return True

    async def send_status(
        self,
        interaction: discord.Interaction,
        files=None,
        stickers=None
    ):
        files = files or []
        stickers = stickers or []

        status_channel = self.bot.get_channel(STATUS_CHANNEL_ID)
        if not status_channel:
            return

        colors = [
            discord.Color.blurple(),
            discord.Color.purple(),
            discord.Color.magenta(),
            discord.Color.teal(),
            discord.Color.random()
        ]

        embed = discord.Embed(
            description=f"❝ *{self.status_text}* ❞",
            color=random.choice(colors)
        )

        embed.set_author(
            name=interaction.user.display_name,
            icon_url=interaction.user.display_avatar.url
        )

        if self.mood:
            embed.add_field(
                name="Mood",
                value=self.mood,
                inline=False
            )

        image_file = None
        music_files = []

        for file in files:
            filename = file.filename.lower()
            if filename.endswith(("png", "jpg", "jpeg", "webp", "gif")):
                image_file = file
            elif filename.endswith(("mp3", "wav", "ogg", "m4a")):
                music_files.append(file)

        if image_file:
            embed.set_image(url=f"attachment://{image_file.filename}")

        if stickers:
            sticker = stickers[0]
            try:
                embed.set_thumbnail(url=sticker.url)
            except:
                pass

        embed.set_footer(text=f"Astralan Status • {interaction.user.display_name}")

        send_files = []
        if image_file:
            send_files.append(image_file)

        status_message = await status_channel.send(
            embed=embed,
            files=send_files
        )

        # Auto React
        for react in ["❤️", "✨"]:
            try:
                await status_message.add_reaction(react)
            except:
                pass

        # Auto Thread
        try:
            await status_message.create_thread(
                name=f"💬 Thread by {interaction.user.display_name}"
            )
        except:
            pass

        # Kirim File Lagu
        for music in music_files:
            music_embed = discord.Embed(
                description=f"**Now Playing**\n`{music.filename}`",
                color=discord.Color.dark_theme()
            )
            await status_channel.send(embed=music_embed, file=music)

    @discord.ui.button(
        label="📤 Tambah Media",
        style=discord.ButtonStyle.blurple,
        custom_id="status_upload_media"
    )
    async def upload_media(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        await interaction.response.send_message(
            (
                "Kirimkan foto, lagu, atau stiker ke chat ini sekarang:\n"
                "🖼️ Foto | 🎵 Lagu | 🌸 Stiker\n\n"
                "> Pesan kamu akan otomatis dihapus.\n"
                "⏳ Batas waktu: 60 detik."
            ),
            ephemeral=True
        )

        def check(message):
            return (
                message.author == interaction.user
                and message.channel == interaction.channel
            )

        files = []
        stickers = []

        try:
            msg = await self.bot.wait_for("message", timeout=60, check=check)

            if msg.attachments:
                files = [await att.to_file() for att in msg.attachments]
            if msg.stickers:
                stickers = msg.stickers

            try:
                await msg.delete()
            except:
                pass

        except:
            await interaction.followup.send(
                "❌ Waktu upload habis, status dikirim tanpa media.",
                ephemeral=True
            )
            await self.send_status(interaction)
            # Hapus pesan konfirmasi publik
            try:
                await interaction.message.delete()
            except:
                return

        await self.send_status(interaction, files=files, stickers=stickers)
        await interaction.followup.send(
            "**✨ Status Astralan berhasil dikirim dengan media!**",
            ephemeral=True
        )
        try:
            await interaction.message.delete()
        except:
            pass

    @discord.ui.button(
        label="⏭️ Kirim Langsung (Tanpa Media)",
        style=discord.ButtonStyle.gray,
        custom_id="status_skip_media"
    )
    async def skip_media(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        await interaction.response.defer(ephemeral=True)
        await self.send_status(interaction)
        await interaction.followup.send(
            "**✨ Status Astralan berhasil dikirim!**",
            ephemeral=True
        )
        try:
            await interaction.message.delete()
        except:
            pass


class AutoStatus(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message):
        # Abaikan pesan dari bot sendiri atau pesan dari server lain (DM)
        if message.author.bot or not message.guild:
            return

        # Pastikan pesan dikirim di channel khusus status
        if message.channel.id != STATUS_CHANNEL_ID:
            return

        # Ambil teks status dari pesan member
        status_text = message.content

        # Hapus pesan asli member di channel agar chat tetap bersih
        try:
            await message.delete()
        except:
            pass

        # Kirim pesan konfirmasi publik di channel (bisa diklik tombolnya oleh pengirim)
        await message.channel.send(
            f"**📝 Konfirmasi Status Astralan ({message.author.mention})**\n"
            f"> *\"{status_text}\"*\n\n"
            f"Apakah kamu ingin menambahkan foto, lagu, atau stiker?",
            view=UploadView(self.bot, status_text, user_mood="", author_id=message.author.id)
        )


async def setup(bot):
    await bot.add_cog(AutoStatus(bot))