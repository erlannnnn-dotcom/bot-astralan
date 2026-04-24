import discord
from discord.ext import commands

class Rules(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="rules")
    async def rules(self, ctx):

        # 🔥 Kirim gambar dulu (di atas, bukan embed)
        file = discord.File("rules.png", filename="rules.png")
        await ctx.send(file=file)

        # ================= EMBED 1 =================
        embed1 = discord.Embed(
            description="**A. Respect & Attitude**",
            color=discord.Color.blue()
        )
        embed1.add_field(
            name="",
            value=(
                "• Semua member wajib saling menghormati tanpa terkecuali.\n"
                "• Dilarang keras melakukan toxic behavior seperti menghina, merendahkan, atau mempermalukan orang lain.\n"
                "• Segala bentuk pelecehan, intimidasi, maupun bullying tidak akan ditoleransi.\n"
                "• Gunakan bahasa yang sopan, jelas, dan tidak menyinggung pihak lain.\n"
                "• Perbedaan pendapat adalah hal wajar, namun tetap harus disampaikan dengan cara yang baik.\n"
                "• Hindari memancing konflik atau memperkeruh suasana komunitas.\n"
            ),
            inline=False
        )

        embed1.add_field(
            name="B. Chat Rules",
            value=(
                "• Dilarang spam dalam bentuk apapun (text, emoji, sticker, atau GIF).\n"
                "• Hindari penggunaan huruf kapital berlebihan yang dapat dianggap sebagai teriakan.\n"
                "• Dilarang mengirim pesan berulang (flood) yang mengganggu kenyamanan.\n"
                "• Gunakan channel sesuai dengan topik dan fungsinya.\n"
                "• Hindari pembahasan di luar topik (OOT) secara berlebihan.\n"
                "• Jaga kualitas percakapan agar tetap nyaman untuk semua member.\n"
            ),
            inline=False
        )

        await ctx.send(embed=embed1)

        # ================= EMBED 2 =================
        embed2 = discord.Embed(
            color=discord.Color.blue()
        )

        embed2.add_field(
            name="C. Toxic & Hate Speech",
            value=(
                "• Dilarang menggunakan kata-kata kasar, ofensif, atau tidak pantas.\n"
                "• Segala bentuk rasisme, diskriminasi, dan stereotip sangat dilarang.\n"
                "• Tidak diperbolehkan menyerang individu maupun kelompok secara langsung.\n"
                "• Ujaran kebencian dalam bentuk apapun akan langsung ditindak tegas.\n"
                "• Jaga lingkungan tetap aman dan nyaman untuk semua orang.\n"
            ),
            inline=False
        )

        embed2.add_field(
            name="D. Privacy & Safety",
            value=(
                "• Dilarang menyebarkan data pribadi (doxxing) dalam bentuk apapun.\n"
                "• Tidak diperbolehkan membagikan nomor telepon, alamat, email, atau informasi sensitif orang lain.\n"
                "• Jangan memaksa member lain untuk mengungkapkan identitas pribadi.\n"
                "• Hormati privasi setiap individu di dalam komunitas.\n"
                "• Keamanan member adalah prioritas utama.\n"
            ),
            inline=False
        )

        embed2.add_field(
            name="E. Media & Content",
            value=(
                "• Dilarang mengirim konten NSFW atau tidak pantas.\n"
                "• Dilarang konten yang mengandung kekerasan ekstrem.\n"
                "• Dilarang menyebarkan link berbahaya, phishing, atau scam.\n"
                "• Gunakan fitur spoiler untuk konten sensitif.\n"
                "• Pastikan konten yang dibagikan sesuai dengan aturan server.\n"
            ),
            inline=False
        )

        await ctx.send(embed=embed2)

        # ================= EMBED 3 =================
        embed3 = discord.Embed(
            color=discord.Color.blue()
        )

        embed3.add_field(
            name="F. Voice Channel",
            value=(
                "• Hormati pembicaraan orang lain di voice channel.\n"
                "• Dilarang mic spam, noise berlebihan, atau soundboard mengganggu (gunakan voice dengan etika yang baik).\n"
                "• Jangan memotong pembicaraan secara tidak sopan.\n"
            ),
            inline=False
        )

        embed3.add_field(
            name="G. Promotion",
            value=(
                "• Dilarang melakukan promosi tanpa izin staff.\n"
                "• Dilarang menyebarkan link server lain tanpa persetujuan.\n"
                "• Gunakan channel khusus promosi jika tersedia.\n"
                "• Pelanggaran akan langsung ditindak.\n"
            ),
            inline=False
        )

        embed3.add_field(
            name="H. Exploit & Abuse",
            value=(
                "• Dilarang mencoba bypass sistem bot atau moderation.\n"
                "• Dilarang memanfaatkan bug server untuk keuntungan pribadi.\n"
                "• Dilarang menggunakan karakter aneh untuk menghindari filter.\n"
                "• Segala bentuk penyalahgunaan sistem akan dikenakan sanksi.\n"
            ),
            inline=False
        )

        embed3.add_field(
            name="I. Moderation",
            value=(
                "• Hormati semua keputusan admin dan moderator.\n"
                "• Jangan mendebat keputusan staff di channel publik.\n"
                "• Gunakan ticket atau DM jika ingin mengajukan banding.\n"
                "• Staff berhak mengambil tindakan sesuai situasi.\n"
            ),
            inline=False
        )

        embed3.add_field(
            name="J. Punishment",
            value=(
                "• Pelanggaran akan dikenakan sanksi sesuai tingkatnya.\n"
                "• Sanksi dapat berupa warning, mute, kick, atau ban.\n"
                "• Pelanggaran berulang akan mendapatkan hukuman lebih berat.\n"
                "• Tidak ada toleransi untuk pelanggaran berat.\n"
            ),
            inline=False
        )

        embed3.set_footer(text="Astralan Community • Follow the rules")

        await ctx.send(embed=embed3)


async def setup(bot):
    await bot.add_cog(Rules(bot))