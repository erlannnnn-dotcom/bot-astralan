import discord
from discord.ext import commands

WELCOME_CHANNEL_ID = 1494993934315946079  # GANTI dengan ID channel kamu


class Welcomee(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        channel = member.guild.get_channel(WELCOME_CHANNEL_ID)

        if channel is None:
            return

        embed = discord.Embed(
            title=f"Selamat datang di {member.guild.name}",
            description=(
                f"Halo {member.mention}, selamat bergabung di **Astralan**\n\n"
                f"Di sini kamu bisa ngobrol, cari teman, dan ikut berbagai aktivitas seru. Jangan ragu untuk mulai berinteraksi ya!\n\n"
                f"**Baca aturan** di <#1496857934339244163>\n"
                f"**Ambil role** di <#1496857983735435486>\n\n"
                f"Sekarang kamu sudah menjadi bagian dari komunitas ini!"
            ),
            color=discord.Color.from_rgb(88, 101, 242)
        )

        embed.set_thumbnail(url=member.display_avatar.url)

        embed.set_footer(
            text=f"{member.guild.name}  •  Member ke-{member.guild.member_count}"
        )

        await channel.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Welcomee(bot))