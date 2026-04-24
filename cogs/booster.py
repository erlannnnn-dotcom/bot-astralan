import discord
from discord.ext import commands

BOOST_CHANNEL_ID = 1496893907882217552  # ganti

class Booster(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def send_boost_embed(self, member: discord.Member):
        channel = member.guild.get_channel(BOOST_CHANNEL_ID)

        if channel is None:
            return

        embed = discord.Embed(
            title="🚀 A New Stardust Booster Appears!",
            description=(
                f"Terima kasih {member.mention} telah menguatkan energi server ini ✨\n\n"
                "Boost kamu membuka kekuatan baru dan membuat komunitas ini semakin bersinar.\n"
                "Dukunganmu sangat berarti bagi seluruh Stardust!"
            ),
            color=discord.Color.from_rgb(186, 104, 200)
        )

        embed.set_thumbnail(url=member.display_avatar.url)

        embed.add_field(
            name="Level Boost Saat Ini",
            value=f"Level {member.guild.premium_tier}",
            inline=True
        )

        embed.add_field(
            name="Total Boost",
            value=f"{member.guild.premium_subscription_count}",
            inline=True
        )

        embed.set_footer(text="Astral Boost System")

        file = discord.File("booster.png", filename="booster.png")
        embed.set_image(url="attachment://booster.png")

        await channel.send(embed=embed, file=file)

    # 🔥 AUTO DETECT BOOST
    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        if before.premium_since is None and after.premium_since is not None:
            await self.send_boost_embed(after)

    # 🧪 COMMAND TEST
    @commands.command(name="test_boost")
    async def test_boost(self, ctx):
        await self.send_boost_embed(ctx.author)
        await ctx.send("Test boost berhasil dikirim!")


async def setup(bot):
    await bot.add_cog(Booster(bot))