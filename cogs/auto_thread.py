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