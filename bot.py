import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
from cogs.role import GameRoleView
from cogs.vibesrole import RoleView
from cogs.genderrole import GenderView
from cogs.ticket import TicketView

load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ================= READY =================
@bot.event
async def on_ready():
    print(f"Bot aktif sebagai {bot.user}")

    bot.add_view(GameRoleView())
    bot.add_view(RoleView())
    bot.add_view(GenderView())
    bot.add_view(TicketView())

    print("Views registered")

# ================= LOAD COGS =================
async def load_extensions():
    for file in os.listdir("./cogs"):
        if file.endswith(".py"):
            await bot.load_extension(f"cogs.{file[:-3]}")
    print("Cogs loaded")

# ================= START =================
async def main():
    async with bot:
        await load_extensions()
        await bot.start(DISCORD_TOKEN)

import asyncio
asyncio.run(main())