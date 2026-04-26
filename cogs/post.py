import discord
from discord.ext import commands

ADMIN_ROLE_IDS = [
    1496838207822889050,
    1496846251914956820,
    1496845677764804738
]

POST_CHANNEL_ID = None

class PostSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="post")
    async def post_system(self, ctx, *, args):

        # 🔒 CEK ADMIN
        if not any(role.id in ADMIN_ROLE_IDS for role in ctx.author.roles):
            await ctx.send("❌ Kamu tidak punya akses untuk command ini!")
            return

        # 🧠 PARSE
        try:
            judul, isi = args.split("|", 1)
        except ValueError:
            await ctx.send("❌ Format salah!\nGunakan: !post Judul | Isi pesan")
            return

        # 🎨 STYLE BARU (KAYAK SS)
        embed = discord.Embed(
            description=(
                f"## {judul.strip()}\n"
                f"{isi.strip()}"
            ),
            color=discord.Color.from_rgb(47, 49, 54)  # bikin garis samping nyatu
        )
        
        # 📸 GAMBAR DARI DISCORD
        file = None
        if ctx.message.attachments:
            attachment = ctx.message.attachments[0]
            file = await attachment.to_file()
            embed.set_image(url=f"attachment://{attachment.filename}")

        # 📤 TARGET CHANNEL
        target_channel = ctx.channel
        if POST_CHANNEL_ID:
            channel = ctx.guild.get_channel(POST_CHANNEL_ID)
            if channel:
                target_channel = channel

        # 🚀 KIRIM
        await target_channel.send(embed=embed, file=file if file else None)

        # 🧹 HAPUS COMMAND
        try:
            await ctx.message.delete()
        except:
            pass


async def setup(bot):
    await bot.add_cog(PostSystem(bot))